from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models import ConfessionLike, SkillRequest

client = TestClient(app)

LOST = {'name': 'Black headphones', 'status': 'lost', 'place': 'Library', 'desc': 'Lost near desk'}
SKILL = {'name': 'Java basics', 'person': 'Ali', 'kind': 'teach', 'detail': 'Learn Java OOP', 'exchange': 'English'}


def test_lost_workflow(alice, bob):
    (a, alice_id), (b, _) = alice, bob
    r = client.post('/lost-items', json=LOST, headers=a)
    assert r.status_code == 201 and r.json()['owner_id'] == alice_id
    i = r.json()['id']
    assert client.get('/lost-items', params={'status': 'lost'}).json()[0]['id'] == i
    assert client.patch(f'/lost-items/{i}', headers=b, json={'name': 'Other'}).status_code == 403
    assert client.post(f'/lost-items/{i}/resolve', headers=b).status_code == 403
    assert client.post(f'/lost-items/{i}/resolve', headers=a).status_code == 200
    assert client.post(f'/lost-items/{i}/resolve', headers=a).status_code == 409
    assert client.delete(f'/lost-items/{i}', headers=b).status_code == 403
    assert client.delete(f'/lost-items/{i}', headers=a).status_code == 204
    assert client.get(f'/lost-items/{i}').status_code == 404


def test_lost_owner_cannot_be_spoofed(alice, bob):
    (a, alice_id), (_, bob_id) = alice, bob
    item = client.post('/lost-items', json={**LOST, 'owner_id': bob_id}, headers=a).json()
    assert item['owner_id'] == alice_id


def test_skills_workflow(sessions, alice, bob):
    (a, _), (b, bob_id) = alice, bob
    r = client.post('/skills', json=SKILL, headers=a)
    assert r.status_code == 201
    sid = r.json()['id']
    assert client.post(f'/skills/{sid}/requests', json={'message': 'Hello'}, headers=a).status_code == 409
    req = client.post(f'/skills/{sid}/requests', json={'message': 'Please teach me'}, headers=b)
    assert req.status_code == 201 and req.json()['applicant_id'] == bob_id
    assert client.post(f'/skills/{sid}/requests', json={'message': 'Please teach me'}, headers=b).status_code == 409
    rid = req.json()['id']
    assert client.get(f'/skills/{sid}/requests', headers=b).status_code == 403
    assert client.patch(f'/skills/{sid}/requests/{rid}', params={'decision': 'accepted'}, headers=b).status_code == 403
    assert client.patch(f'/skills/{sid}/requests/{rid}', params={'decision': 'accepted'}, headers=a).json()['status'] == 'accepted'
    assert client.patch(f'/skills/{sid}/requests/{rid}', params={'decision': 'rejected'}, headers=a).status_code == 409
    assert client.delete(f'/skills/{sid}', headers=b).status_code == 403
    assert client.delete(f'/skills/{sid}', headers=a).status_code == 204
    with sessions() as session:
        assert session.get(SkillRequest, rid) is None


def test_confessions_workflow(alice, bob):
    (a, _), (b, _) = alice, bob
    r = client.post('/confessions', json={'text': 'Great campus day'}, headers=a)
    assert r.status_code == 201 and 'author_id' not in r.json()
    pid = r.json()['id']
    assert client.post(f'/confessions/{pid}/likes', headers=b).json()['likes'] == 1
    assert client.post(f'/confessions/{pid}/likes', headers=b).status_code == 409
    assert client.delete(f'/confessions/{pid}/likes', headers=b).status_code == 204
    assert client.patch(f'/confessions/{pid}', json={'text': 'Edited text'}, headers=b).status_code == 403
    assert client.delete(f'/confessions/{pid}', headers=b).status_code == 403
    assert client.delete(f'/confessions/{pid}', headers=a).status_code == 204


def test_validation(alice):
    a = alice[0]
    assert client.post('/lost-items', json={'name': 'x', 'status': 'bad', 'place': 'x', 'desc': 'x'}, headers=a).status_code == 422
    assert client.post('/confessions', json={'text': 'x' * 281}, headers=a).status_code == 422
    assert client.get('/skills/999', headers=a).status_code == 404
    assert client.post('/confessions', json={'text': 'Null\x00byte'}, headers=a).status_code == 422


def test_skill_requests_are_scoped_to_skill_and_can_be_reapplied(alice, bob):
    (a, _), (b, _) = alice, bob
    first = client.post('/skills', json=SKILL, headers=a).json()['id']
    second = client.post('/skills', json=SKILL, headers=a).json()['id']
    application = {'message': 'Please teach me'}
    assert client.post('/skills/999/requests', json=application, headers=b).status_code == 404
    request_id = client.post(f'/skills/{first}/requests', json=application, headers=b).json()['id']
    decision = {'decision': 'rejected'}
    assert client.patch(f'/skills/{second}/requests/{request_id}', params=decision, headers=a).status_code == 404
    assert client.patch(f'/skills/{first}/requests/{request_id}', params=decision, headers=a).status_code == 200
    assert client.post(f'/skills/{first}/requests', json=application, headers=b).status_code == 201


def test_like_persists_across_connections_and_cascades(database_engine, sessions, alice, bob):
    (a, _), (b, bob_id) = alice, bob
    post = client.post('/confessions', json={'text': 'Great campus day'}, headers=a).json()
    post_id = post['id']
    urls = f'/confessions/{post_id}'
    assert client.post(f'{urls}/likes', headers=b).status_code == 200
    database_engine.dispose()
    assert client.get(urls, headers=a).json() == {**post, 'likes': 1}

    with sessions() as session:
        session.add(ConfessionLike(post_id=post_id, user_id=bob_id))
        with pytest.raises(IntegrityError):
            session.commit()

    assert client.delete(urls, headers=a).status_code == 204
    with sessions() as session:
        assert session.get(ConfessionLike, (post_id, bob_id)) is None
        session.add(ConfessionLike(post_id=post_id, user_id=3))
        with pytest.raises(IntegrityError):
            session.commit()
