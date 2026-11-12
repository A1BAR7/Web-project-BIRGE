"""Däm validation, filtering and record management; assets are shared/read-only."""
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from app.store import store
from app.services.core import get_or_404

FOOD_IMAGES = Path(__file__).resolve().parents[2] / 'static/images/food'


def validate_image_url(value):
    prefix = '/static/images/food/'
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError('Use an existing local /static/images/food/ asset')
    filename = value[len(prefix):]
    if not filename or '/' in filename or '\\' in filename or filename in {'.', '..'}:
        raise ValueError('Invalid image filename')
    if Path(filename).suffix.lower() not in {'.svg', '.jpg', '.jpeg', '.png', '.webp'} or not (FOOD_IMAGES / filename).is_file():
        raise ValueError('Image asset does not exist')
    return value


def image_metadata(url, name):
    # Source manifest contains licensing/provenance for any downloaded photographs.
    import json
    manifest = FOOD_IMAGES / 'credits.json'
    credits = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    info = credits.get(url.rsplit('/', 1)[-1], {})
    return {'image_kind': info.get('kind', 'placeholder'),
            'image_alt': info.get('alt', f'{name} — photo unavailable / Фото жоқ'),
            'image_credit': info.get('credit', ''), 'image_source': info.get('source', '')}


def list_food(canteen=None, category=None, search=None, min_price=None, max_price=None):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, 'min_price must not exceed max_price')
    return [item for item in store.food.values()
            if (canteen is None or item['canteen'].casefold() == canteen.casefold())
            and (category is None or item['category'].casefold() == category.casefold())
            and (not search or search.casefold() in item['name'].casefold())
            and (min_price is None or item['price'] >= min_price)
            and (max_price is None or item['price'] <= max_price)]


def create_food(body):
    data = body.model_dump()
    item = {'id': next(store.food_ids), **data, 'created_at': datetime.now(timezone.utc),
            **image_metadata(data['image_url'], data['name'])}
    store.food[item['id']] = item
    return item


def update_food(food_id, body):
    item = get_or_404(store.food, food_id)
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(422, 'Fields cannot be null')
    item.update(changes)
    item.update(image_metadata(item['image_url'], item['name']))
    return item
