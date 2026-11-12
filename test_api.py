from fastapi.testclient import TestClient
from app.main import app
from app.store import store
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset():
    store.__init__()

def test_lost_workflow():
    r=client.post('/lost-items',json={'name':'Black headphones','status':'lost','place':'Library','desc':'Lost near desk','owner_id':1})
    assert r.status_code==201
    i=r.json()['id']
    assert client.get('/lost-items',params={'status':'lost'}).json()[0]['id']==i
    assert client.patch(f'/lost-items/{i}',params={'actor_id':2},json={'name':'Other'}).status_code==403
    assert client.post(f'/lost-items/{i}/resolve',params={'actor_id':1}).status_code==200
    assert client.post(f'/lost-items/{i}/resolve',params={'actor_id':1}).status_code==409
    assert client.delete(f'/lost-items/{i}',params={'actor_id':1}).status_code==204
    assert client.get(f'/lost-items/{i}').status_code==404

def test_skills_workflow():
    r=client.post('/skills',json={'name':'Java basics','person':'Ali','kind':'teach','detail':'Learn Java OOP','exchange':'English','owner_id':1})
    assert r.status_code==201
    sid=r.json()['id']
    assert client.post(f'/skills/{sid}/requests',json={'applicant_id':1,'message':'Hello'}).status_code==409
    a=client.post(f'/skills/{sid}/requests',json={'applicant_id':2,'message':'Please teach me'})
    assert a.status_code==201
    assert client.post(f'/skills/{sid}/requests',json={'applicant_id':2,'message':'Please teach me'}).status_code==409
    rid=a.json()['id']
    assert client.patch(f'/skills/{sid}/requests/{rid}',params={'decision':'accepted','actor_id':1}).json()['status']=='accepted'
    assert client.patch(f'/skills/{sid}/requests/{rid}',params={'decision':'rejected','actor_id':1}).status_code==409
    assert client.delete(f'/skills/{sid}',params={'actor_id':1}).status_code==204
    assert rid not in store.requests

def test_confessions_workflow():
    r=client.post('/confessions',json={'text':'Great campus day','author_id':1})
    assert r.status_code==201 and 'author_id' not in r.json()
    pid=r.json()['id']
    assert client.post(f'/confessions/{pid}/likes',params={'user_id':2}).json()['likes']==1
    assert client.post(f'/confessions/{pid}/likes',params={'user_id':2}).status_code==409
    assert client.delete(f'/confessions/{pid}/likes',params={'user_id':2}).status_code==204
    assert client.delete(f'/confessions/{pid}',params={'actor_id':2}).status_code==403
    assert client.delete(f'/confessions/{pid}',params={'actor_id':1}).status_code==204

def test_validation():
    assert client.post('/lost-items',json={'name':'x','status':'bad','place':'x','desc':'x','owner_id':-1}).status_code==422
    assert client.post('/confessions',json={'text':'x'*281,'author_id':1}).status_code==422
    assert client.get('/skills/999').status_code==404
