from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.security import create_access_token, verify_password

client = TestClient(app)
BODY = {'email': 'Student@SDU.edu.kz', 'username': 'Student_1', 'password': 'S3cret-pass!'}
FOOD = {'name': 'Тест', 'price': 1000, 'category': 'Lunch', 'canteen': 'Injoo'}


def register(**changes):
    return client.post('/auth/register', json={**BODY, **changes})


def login(username='student_1', password=BODY['password']):
    return client.post('/auth/login', data={'username': username, 'password': password})


def bearer(token):
    return {'Authorization': f'Bearer {token}'}


# --- registration -----------------------------------------------------------------

def test_register_returns_public_user_and_hashes_password(sessions):
    response = register()
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == 'student@sdu.edu.kz' and data['username'] == 'student_1'
    assert data['role'] == 'user' and data['is_active'] is True
    assert 'password' not in data and 'hashed_password' not in data
    with sessions() as session:
        stored = session.get(User, data['id']).hashed_password
    assert stored.startswith('$argon2id$') and BODY['password'] not in stored
    assert verify_password(BODY['password'], stored) and not verify_password('wrong-pass', stored)


def test_register_cannot_choose_role():
    assert register(role='admin').json()['role'] == 'user'


def test_register_duplicates_are_case_insensitive():
    assert register().status_code == 201
    assert register(username='other').status_code == 409
    assert register(email='other@sdu.edu.kz', username='STUDENT_1').status_code == 409


@pytest.mark.parametrize('changes', [
    {'email': 'not-an-email'}, {'username': 'ab'}, {'username': 'has space'}, {'username': 'x' * 31},
    {'password': 'short'}, {'password': 'x' * 129}, {'password': 'bad\x00pass1'},
])
def test_register_validation(changes):
    assert register(**changes).status_code == 422


# --- login / tokens ---------------------------------------------------------------

def test_login_by_username_or_email_and_token_contents():
    user_id = register().json()['id']
    for name in ('student_1', 'Student@SDU.edu.kz'):
        response = login(name)
        assert response.status_code == 200
        data = response.json()
        assert data['token_type'] == 'bearer' and data['expires_in'] == 30 * 60
    claims = jwt.decode(data['access_token'], options={'verify_signature': False})
    assert claims['sub'] == str(user_id) and claims['exp'] > claims['iat']
    assert 'password' not in claims and 'role' not in claims


@pytest.mark.parametrize('username, password', [('student_1', 'wrong-password'), ('nobody', BODY['password'])])
def test_login_failures_are_indistinguishable(username, password):
    register()
    response = login(username, password)
    assert response.status_code == 401
    assert response.json() == {'detail': 'Incorrect email/username or password'}
    assert response.headers['www-authenticate'] == 'Bearer'


def test_me_requires_valid_token():
    register()
    token = login().json()['access_token']
    assert client.get('/auth/me', headers=bearer(token)).json()['username'] == 'student_1'
    assert client.get('/auth/me').status_code == 401
    assert client.get('/auth/me', headers=bearer('garbage')).status_code == 401
    assert client.get('/auth/me', headers={'Authorization': 'Basic abc'}).status_code == 401


def test_expired_tampered_and_unknown_user_tokens_rejected(monkeypatch):
    user_id = register().json()['id']
    secret = 'test-secret-key-for-pytest-only-0123456789'
    now = datetime.now(timezone.utc)
    expired = jwt.encode({'sub': str(user_id), 'iat': now - timedelta(hours=2), 'exp': now - timedelta(hours=1)},
                         secret, algorithm='HS256')
    wrong_key = jwt.encode({'sub': str(user_id), 'exp': now + timedelta(hours=1)}, 'x' * 40, algorithm='HS256')
    no_exp = jwt.encode({'sub': str(user_id)}, secret, algorithm='HS256')
    none_alg = jwt.encode({'sub': str(user_id), 'exp': now + timedelta(hours=1)}, None, algorithm='none')
    ghost = create_access_token(9999)[0]
    for token in (expired, wrong_key, no_exp, none_alg, ghost):
        assert client.get('/auth/me', headers=bearer(token)).status_code == 401


def test_missing_secret_key_reports_503(monkeypatch):
    register()
    monkeypatch.setenv('SECRET_KEY', 'short')
    assert login().status_code == 503


def test_inactive_user_is_blocked(sessions):
    user_id = register().json()['id']
    token = login().json()['access_token']
    with sessions() as session:
        session.get(User, user_id).is_active = False
        session.commit()
    assert login().status_code == 403
    assert client.get('/auth/me', headers=bearer(token)).status_code == 403
    assert client.post('/lost-items', headers=bearer(token),
                       json={'name': 'Keys', 'status': 'lost', 'place': 'Hall', 'desc': 'Silver keys'}).status_code == 403


def test_deleted_user_token_is_rejected(sessions):
    user_id = register().json()['id']
    token = login().json()['access_token']
    with sessions() as session:
        session.delete(session.get(User, user_id))
        session.commit()
    assert client.get('/auth/me', headers=bearer(token)).status_code == 401


# --- authorization ----------------------------------------------------------------

def test_public_modules_are_readable_without_login():
    assert client.get('/food').status_code == 200
    assert client.get('/food/10001').status_code == 200
    assert client.get('/lost-items').status_code == 200
    assert client.get('/app/').status_code == 200


@pytest.mark.parametrize('method, path', [
    ('post', '/lost-items'), ('patch', '/lost-items/1'), ('post', '/lost-items/1/resolve'),
    ('delete', '/lost-items/1'), ('post', '/lost-items/1/images'), ('delete', '/lost-items/1/images/x'),
    ('get', '/skills'), ('post', '/skills'), ('get', '/skills/1'), ('post', '/skills/1/requests'),
    ('get', '/skills/1/requests'), ('get', '/confessions'), ('post', '/confessions'),
    ('get', '/confessions/1'), ('post', '/confessions/1/likes'), ('delete', '/confessions/1'),
    ('post', '/food'), ('patch', '/food/10001'), ('delete', '/food/10001'),
    ('get', '/users'), ('patch', '/users/1'), ('get', '/auth/me'),
])
def test_protected_endpoints_require_token(method, path):
    assert getattr(client, method)(path).status_code == 401


def test_food_writes_are_admin_only(alice, admin):
    user, root = alice[0], admin[0]
    assert client.post('/food', json=FOOD, headers=user).status_code == 403
    assert client.patch('/food/10001', json={'price': 1}, headers=user).status_code == 403
    assert client.delete('/food/10001', headers=user).status_code == 403
    assert client.get('/food/10001').json()['price'] == 4820
    created = client.post('/food', json=FOOD, headers=root)
    assert created.status_code == 201
    assert client.patch(f"/food/{created.json()['id']}", json={'price': 1500}, headers=root).json()['price'] == 1500
    assert client.delete(f"/food/{created.json()['id']}", headers=root).status_code == 204


def test_admin_moderation_rights(alice, admin):
    (a, _), (root, _) = alice, admin
    lost = client.post('/lost-items', json={'name': 'Keys', 'status': 'lost', 'place': 'Hall', 'desc': 'Silver keys'}, headers=a).json()
    # admins moderate (delete) but do not edit other people's content
    assert client.patch(f"/lost-items/{lost['id']}", json={'name': 'Hacked'}, headers=root).status_code == 403
    assert client.delete(f"/lost-items/{lost['id']}", headers=root).status_code == 204
    post = client.post('/confessions', json={'text': 'Anonymous post'}, headers=a).json()
    assert client.patch(f"/confessions/{post['id']}", json={'text': 'Edited by admin'}, headers=root).status_code == 403
    assert client.delete(f"/confessions/{post['id']}", headers=root).status_code == 204
    skill = client.post('/skills', headers=a, json={'name': 'Java basics', 'person': 'Ali', 'kind': 'teach',
                                                    'detail': 'Learn Java', 'exchange': 'English'}).json()
    assert client.delete(f"/skills/{skill['id']}", headers=root).status_code == 204


def test_user_management_is_admin_only(alice, admin):
    (a, alice_id), (root, root_id) = alice, admin
    assert client.get('/users', headers=a).status_code == 403
    assert client.patch(f'/users/{alice_id}', json={'role': 'admin'}, headers=a).status_code == 403
    assert [u['username'] for u in client.get('/users', headers=root).json()] == ['alice', 'root']
    assert client.patch(f'/users/{alice_id}', json={'is_active': False}, headers=root).json()['is_active'] is False
    assert client.get('/auth/me', headers=a).status_code == 403
    assert client.patch(f'/users/{root_id}', json={'role': 'user'}, headers=root).status_code == 409
    assert client.patch(f'/users/{root_id}', json={'is_active': False}, headers=root).status_code == 409
    assert client.patch(f'/users/{alice_id}', json={'role': 'owner'}, headers=root).status_code == 422
    assert client.patch('/users/999', json={'role': 'user'}, headers=root).status_code == 404


def test_role_is_read_from_database_not_token(sessions, alice, admin):
    (a, alice_id), _ = alice, admin
    assert client.post('/food', json=FOOD, headers=a).status_code == 403
    with sessions() as session:
        session.get(User, alice_id).role = 'admin'
        session.commit()
    assert client.post('/food', json=FOOD, headers=a).status_code == 201  # same token, new role


def test_openapi_declares_bearer_security():
    schema = client.get('/openapi.json').json()
    assert 'OAuth2PasswordBearer' in schema['components']['securitySchemes']
    assert 'security' in schema['paths']['/skills']['get']
    assert 'security' not in schema['paths']['/lost-items']['get']
    assert 'security' not in schema['paths']['/food']['get']
