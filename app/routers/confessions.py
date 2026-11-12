from fastapi import APIRouter, HTTPException, Response, Query
from app.schemas import ConfessionCreate, ConfessionUpdate
from app.store import store
from app.services.core import get_or_404

router = APIRouter(prefix='/confessions',tags=['Ishimде'])

def public(post):
    return {k:v for k,v in post.items() if k!='author_id'}

@router.post('',status_code=201)
def add_confession(body: ConfessionCreate):
    obj = {'id':store.new_id(),**body.model_dump(),'likes':0}
    store.confessions[obj['id']] = obj
    return public(obj)

@router.get('')
def list_confessions():
    return [public(p) for p in store.confessions.values()]

@router.get('/{post_id}')
def get_confession(post_id: int):
    return public(get_or_404(store.confessions,post_id))

@router.patch('/{post_id}')
def edit_confession(post_id: int,body: ConfessionUpdate,actor_id: int = Query(gt=0)):
    obj = get_or_404(store.confessions,post_id)
    if obj['author_id'] != actor_id: raise HTTPException(403,'Only author can edit')
    obj['text'] = body.text
    return public(obj)

@router.post('/{post_id}/likes')
def like(post_id: int,user_id: int = Query(gt=0)):
    obj = get_or_404(store.confessions,post_id)
    key = (post_id,user_id)
    if key in store.likes: raise HTTPException(409,'Already liked')
    store.likes.add(key)
    obj['likes'] += 1
    return public(obj)

@router.delete('/{post_id}/likes',status_code=204)
def unlike(post_id: int,user_id: int = Query(gt=0)):
    obj = get_or_404(store.confessions,post_id)
    key = (post_id,user_id)
    if key not in store.likes: raise HTTPException(404,'Like not found')
    store.likes.remove(key)
    obj['likes'] -= 1
    return Response(status_code=204)

@router.delete('/{post_id}',status_code=204)
def remove_confession(post_id: int,actor_id: int = Query(gt=0)):
    obj = get_or_404(store.confessions,post_id)
    if obj['author_id'] != actor_id: raise HTTPException(403,'Only author can delete')
    del store.confessions[post_id]
    store.likes = {x for x in store.likes if x[0]!=post_id}
    return Response(status_code=204)
