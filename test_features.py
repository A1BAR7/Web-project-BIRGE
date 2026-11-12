from io import BytesIO
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.menu import MENU
from app.store import store
from app.services import lost_images

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    store.__init__()
    monkeypatch.setattr(lost_images, 'UPLOAD_DIR', tmp_path)
    yield tmp_path


def announcement(owner=101):
    response = client.post('/lost-items', json={
        'name': 'Қара құлаққап', 'status': 'lost', 'place': 'Library',
        'desc': 'Әдемі ғимарат жанында', 'owner_id': owner})
    assert response.status_code == 201
    return response.json()['id']


def image(fmt='PNG', filename=None, mime=None):
    data = BytesIO()
    Image.new('RGB', (20, 16), '#98ad65').save(data, fmt)
    ext = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}[fmt]
    return ('files', (filename or f'photo.{ext}', data.getvalue(), mime or Image.MIME[fmt]))


def upload(item_id, files, actor=101):
    return client.post(f'/lost-items/{item_id}/images', params={'actor_id': actor}, files=files)


@pytest.mark.parametrize('fmt', ['PNG', 'JPEG', 'WEBP'])
def test_valid_image_content_and_generated_names(fmt, isolated_store):
    item_id = announcement()
    response = upload(item_id, [image(fmt, '../../unsafe.' + ('jpg' if fmt == 'JPEG' else fmt.lower()))])
    assert response.status_code == 201, response.text
    stored = response.json()['images'][0]
    assert len(stored['id']) == 32 and 'unsafe' not in stored['url'] and '..' not in stored['url']
    assert lost_images.image_path(stored).is_file()
    assert len(list(isolated_store.iterdir())) == 1


def test_upload_batch_and_total_limit(isolated_store):
    item_id = announcement()
    assert len(upload(item_id, [image(), image()]).json()['images']) == 2
    assert upload(item_id, [image()] * 4).status_code == 422
    assert len(list(isolated_store.iterdir())) == 2
    assert len(upload(item_id, [image()] * 3).json()['images']) == 5
    assert upload(item_id, [image()]).status_code == 422
    assert upload(announcement(), [image()] * 6).status_code == 422


@pytest.mark.parametrize('bad_file', [
    ('file.gif', b'GIF89a', 'image/gif'),
    ('fake.png', b'not an image', 'image/png'),
    ('script.svg', b'<svg onload="alert(1)"/>', 'image/svg+xml'),
    ('empty.jpg', b'', 'image/jpeg'),
])
def test_invalid_formats_atomic_batch(bad_file, isolated_store):
    item_id = announcement()
    assert upload(item_id, [image(), ('files', bad_file)]).status_code == 422
    assert client.get(f'/lost-items/{item_id}').json()['images'] == []
    assert not list(isolated_store.iterdir())


def test_mismatched_types_and_oversize(isolated_store):
    item_id = announcement()
    assert upload(item_id, [image('PNG', 'photo.jpg')]).status_code == 422
    assert upload(item_id, [image('PNG', mime='image/jpeg')]).status_code == 422
    large = ('files', ('big.png', b'x' * (5 * 1024 * 1024 + 1), 'image/png'))
    assert upload(item_id, [large]).status_code == 413
    assert not list(isolated_store.iterdir())


def test_owner_and_missing_announcement(isolated_store):
    item_id = announcement()
    assert upload(item_id, [image()], 202).status_code == 403
    assert upload(999, [image()]).status_code == 404
    assert client.post(f'/lost-items/{item_id}/images', files=[image()]).status_code == 422
    assert not list(isolated_store.iterdir())


def test_image_delete_and_announcement_cleanup(isolated_store):
    item_id = announcement()
    images = upload(item_id, [image(), image()]).json()['images']
    endpoint = f"/lost-items/{item_id}/images/{images[0]['id']}"
    assert client.delete(endpoint, params={'actor_id': 202}).status_code == 403
    assert client.delete(endpoint, params={'actor_id': 101}).status_code == 204
    assert not lost_images.image_path(images[0]).exists()
    assert len(client.get(f'/lost-items/{item_id}').json()['images']) == 1
    assert client.delete(endpoint, params={'actor_id': 101}).status_code == 404
    assert client.delete(f'/lost-items/{item_id}', params={'actor_id': 202}).status_code == 403
    assert client.delete(f'/lost-items/{item_id}', params={'actor_id': 101}).status_code == 204
    assert not list(isolated_store.iterdir())


def test_image_cannot_be_deleted_from_another_announcement():
    first, second = announcement(), announcement()
    stored = upload(first, [image()]).json()['images'][0]
    assert client.delete(f"/lost-items/{second}/images/{stored['id']}", params={'actor_id': 101}).status_code == 404
    assert lost_images.image_path(stored).exists()


def test_failed_disk_write_removes_partial_batch(monkeypatch, isolated_store):
    item_id = announcement()
    original = Path.open
    writes = 0

    def failing_open(path, mode='r', *args, **kwargs):
        nonlocal writes
        if path.parent == isolated_store and mode == 'xb':
            writes += 1
            if writes == 2:
                raise OSError('Simulated full disk')
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', failing_open)
    assert upload(item_id, [image(), image()]).status_code == 500
    assert not list(isolated_store.iterdir())
    assert client.get(f'/lost-items/{item_id}').json()['images'] == []


def test_legacy_announcement_without_images():
    item_id = announcement()
    del store.lost[item_id]['images']
    assert client.get(f'/lost-items/{item_id}').json()['images'] == []


def test_failed_deletion_returns_error_and_keeps_retryable_record(monkeypatch):
    item_id = announcement()
    images = upload(item_id, [image(), image()]).json()['images']
    original = Path.unlink
    blocked = lost_images.image_path(images[1])

    def failing_unlink(path, *args, **kwargs):
        if path == blocked:
            raise PermissionError('Simulated locked file')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', failing_unlink)
    assert client.delete(f'/lost-items/{item_id}', params={'actor_id': 101}).status_code == 500
    remaining = client.get(f'/lost-items/{item_id}').json()['images']
    assert remaining == [images[1]] and blocked.is_file()
    assert client.delete(f"/lost-items/{item_id}/images/{images[1]['id']}", params={'actor_id': 101}).status_code == 500
    monkeypatch.setattr(Path, 'unlink', original)
    assert client.delete(f'/lost-items/{item_id}', params={'actor_id': 101}).status_code == 204
    assert not blocked.exists()


def test_all_ten_seed_records_and_assets():
    response = client.get('/food')
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 10
    assert [(x['name'], x['price'], x['description'], x['canteen'], x['category']) for x in items] == [row[:5] for row in MENU]
    for item in items:
        assert item['currency'] == 'KZT' and item['available'] is True and item['created_at']
        assert item['image_alt'] and item['image_kind'] == 'authentic'
        asset = client.get(item['image_url'])
        assert asset.status_code == 200
        if item['image_kind'] == 'placeholder':
            assert 'Photo unavailable' in asset.text
        else:
            assert item['image_credit'] and item['image_source']
            Image.open(BytesIO(asset.content)).verify()


@pytest.mark.parametrize(('params', 'count'), [
    ({'canteen': 'Injoo'}, 2), ({'category': 'Combo'}, 3),
    ({'search': 'пицца'}, 2), ({'search': 'ЛАҒМАН'}, 2),
    ({'min_price': 1600, 'max_price': 2000}, 2),
    ({'canteen': 'SDU-Red canteen', 'category': 'Pizza', 'search': 'Маргарита', 'min_price': 2000, 'max_price': 2500}, 1),
    ({'search': 'not-on-menu'}, 0), ({'min_price': 2450, 'max_price': 2450}, 2),
])
def test_food_filters(params, count):
    result = client.get('/food', params=params)
    assert result.status_code == 200
    assert len(result.json()) == count


def food_payload(**changes):
    return {'name': 'Жаңа тағам', 'price': 1200, 'category': 'Lunch', 'canteen': 'Injoo', **changes}


def test_food_crud_availability_and_shared_images():
    result = client.post('/food', json=food_payload())
    assert result.status_code == 201
    item = result.json()
    item_id = item['id']
    assert client.get(f'/food/{item_id}').json()['name'] == 'Жаңа тағам'
    response = client.patch(f'/food/{item_id}', json={'price': 1500, 'available': False})
    assert response.status_code == 200 and response.json()['available'] is False
    assert response.json()['price'] == 1500
    assert client.patch(f'/food/{item_id}', json={}).status_code == 200
    assert client.delete(f'/food/{item_id}').status_code == 204
    assert client.get(f'/food/{item_id}').status_code == 404
    assert client.get(item['image_url']).status_code == 200


@pytest.mark.parametrize('changes', [
    {'price': 0}, {'price': -1}, {'price': 'bad'}, {'name': ''}, {'name': '   '},
    {'canteen': ''}, {'category': ' '}, {'currency': 'USD'}, {'unknown': 1},
    {'image_url': 'javascript:alert(1)'}, {'image_url': '/static/images/food/../other.svg'},
    {'image_url': '/static/images/food/missing.webp'},
])
def test_food_validation(changes):
    assert client.post('/food', json=food_payload(**changes)).status_code == 422


def test_food_invalid_ranges_null_and_missing():
    assert client.post('/food', json={}).status_code == 422
    for params in ({'min_price': -1}, {'min_price': 'bad'}, {'min_price': 200, 'max_price': 100}, {'max_price': 'nan'}):
        assert client.get('/food', params=params).status_code == 422
    for changes in ({'name': None}, {'price': None}, {'available': None}, {'price': -1}):
        assert client.patch('/food/10001', json=changes).status_code == 422
    for method in ('get', 'delete', 'patch'):
        options = {'json': {'price': 1000}} if method == 'patch' else {}
        assert getattr(client, method)('/food/999999', **options).status_code == 404


def test_swagger_and_frontend_integration_contract():
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    for path in ('/food', '/food/{food_id}', '/lost-items/{item_id}/images', '/skills', '/confessions'):
        assert path in schema['paths']
    upload_operation = schema['paths']['/lost-items/{item_id}/images']['post']
    assert 'multipart/form-data' in upload_operation['requestBody']['content']
    assert 'FoodRead' in schema['components']['schemas']
    assert client.get('/app/').status_code == 200
    script = client.get('/app/script.js').text
    assert "api('/food?'" in script and 'sendImages' in script and 'image-gallery' in script
    assert client.get('/static/fonts/NotoSans-Variable.ttf').status_code == 200
    assert client.get('/static/images/food/ATTRIBUTION.md').status_code == 200


def test_uploaded_image_served_by_fastapi(tmp_path, monkeypatch):
    # The mount retains its real directory; patch only this test to use a temporary mount.
    from fastapi.staticfiles import StaticFiles
    mount = next(route for route in app.routes if getattr(route, 'path', '') == '/uploads/lost_items')
    monkeypatch.setattr(mount, 'app', StaticFiles(directory=tmp_path))
    item_id = announcement()
    stored = upload(item_id, [image()]).json()['images'][0]
    response = client.get(stored['url'])
    assert response.status_code == 200 and response.headers['content-type'] == 'image/png'
    Image.open(BytesIO(response.content)).verify()
    assert client.get('/uploads/lost_items/%2e%2e/%2e%2e/app/main.py').status_code == 404
