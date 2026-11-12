from fastapi import HTTPException
from app.store import store

def get_or_404(collection, item_id):
    if item_id not in collection:
        raise HTTPException(404, 'Resource not found')
    return collection[item_id]

def create(collection, data):
    obj = {'id': store.new_id(), **data.model_dump()}
    collection[obj['id']] = obj
    return obj

def update(collection, item_id, data):
    obj = get_or_404(collection, item_id)
    changes = data.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(422, 'Fields cannot be null')
    obj.update(changes)
    return obj

def delete(collection, item_id):
    get_or_404(collection, item_id)
    del collection[item_id]

def owner_only(obj, actor_id):
    if obj['owner_id'] != actor_id:
        raise HTTPException(403, 'Only the owner may perform this operation')
