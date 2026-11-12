from fastapi import APIRouter, HTTPException, Response, Query, UploadFile, File
from typing import Literal
from app.schemas import LostCreate, LostUpdate, LostRead
from app.services import lost_images
from app.store import store
from app.services.core import create, update, get_or_404, owner_only

router = APIRouter(prefix='/lost-items', tags=['Lost & Found'])

@router.post('', status_code=201, response_model=LostRead)
def add_item(body: LostCreate):
    item = create(store.lost, body)
    item['resolved'] = False
    item['images'] = []
    return item

@router.get('', response_model=list[LostRead])
def list_items(status: Literal['lost','found'] | None = None, q: str | None = Query(None,max_length=100), resolved: bool | None = None):
    return [i for i in store.lost.values() if (status is None or i['status']==status) and (resolved is None or i['resolved']==resolved) and (not q or q.casefold() in (i['name']+' '+i['place']+' '+i['desc']).casefold())]

@router.get('/{item_id}', response_model=LostRead)
def get_item(item_id: int):
    return get_or_404(store.lost,item_id)

@router.patch('/{item_id}', response_model=LostRead)
def edit_item(item_id: int, body: LostUpdate, actor_id: int = Query(gt=0)):
    item = get_or_404(store.lost,item_id)
    owner_only(item,actor_id)
    if item['resolved']: raise HTTPException(409,'Resolved items cannot be edited')
    return update(store.lost,item_id,body)

@router.post('/{item_id}/resolve', response_model=LostRead)
def resolve_item(item_id: int, actor_id: int = Query(gt=0)):
    item = get_or_404(store.lost,item_id)
    owner_only(item,actor_id)
    if item['resolved']: raise HTTPException(409,'Item already resolved')
    item['resolved'] = True
    return item

@router.delete('/{item_id}', status_code=204)
async def remove_item(item_id: int, actor_id: int = Query(gt=0)):
    await lost_images.delete_item(item_id, actor_id)
    return Response(status_code=204)

@router.post('/{item_id}/images', status_code=201, response_model=LostRead,
             responses={403: {'description': 'Owner required'}, 404: {'description': 'Announcement missing'},
                        413: {'description': 'Image exceeds 5 MB'}, 422: {'description': 'Invalid images or image count'}})
async def add_images(item_id: int, actor_id: int = Query(gt=0), files: list[UploadFile] = File(...)):
    return await lost_images.upload_images(item_id, actor_id, files)

@router.delete('/{item_id}/images/{image_id}', status_code=204)
async def remove_image(item_id: int, image_id: str, actor_id: int = Query(gt=0)):
    await lost_images.delete_image(item_id, actor_id, image_id)
    return Response(status_code=204)
