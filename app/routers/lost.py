from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from app.database import DatabaseSession
from app.models import LostItem
from app.schemas import MAX_IDENTIFIER, LostCreate, LostRead, LostUpdate
from app.services import lost_images
from app.services.core import apply_update, create, get_or_404, list_records, owner_only

router = APIRouter(prefix='/lost-items', tags=['Lost & Found'])


@router.post('', status_code=201, response_model=LostRead)
def add_item(body: LostCreate, db: DatabaseSession):
    return create(db, LostItem, body)


@router.get('', response_model=list[LostRead])
def list_items(db: DatabaseSession, status: Literal['lost', 'found'] | None = None,
               q: str | None = Query(None, max_length=100), resolved: bool | None = None):
    filters = []
    if status is not None:
        filters.append(LostItem.status == status)
    if resolved is not None:
        filters.append(LostItem.resolved == resolved)
    items = list_records(db, LostItem, *filters)
    if not q:
        return items
    search = q.casefold()
    return [item for item in items if search in f'{item.name} {item.place} {item.desc}'.casefold()]


@router.get('/{item_id}', response_model=LostRead)
def get_item(item_id: int, db: DatabaseSession):
    return get_or_404(db, LostItem, item_id)


@router.patch('/{item_id}', response_model=LostRead)
def edit_item(item_id: int, body: LostUpdate, db: DatabaseSession, actor_id: int = Query(gt=0, le=MAX_IDENTIFIER)):
    item = get_or_404(db, LostItem, item_id, lock=True)
    owner_only(item, actor_id)
    if item.resolved:
        raise HTTPException(409, 'Resolved items cannot be edited')
    apply_update(item, body)
    db.commit()
    return item


@router.post('/{item_id}/resolve', response_model=LostRead)
def resolve_item(item_id: int, db: DatabaseSession, actor_id: int = Query(gt=0, le=MAX_IDENTIFIER)):
    item = get_or_404(db, LostItem, item_id, lock=True)
    owner_only(item, actor_id)
    if item.resolved:
        raise HTTPException(409, 'Item already resolved')
    item.resolved = True
    db.commit()
    return item


@router.delete('/{item_id}', status_code=204)
def remove_item(item_id: int, db: DatabaseSession, actor_id: int = Query(gt=0, le=MAX_IDENTIFIER)):
    lost_images.delete_item(db, item_id, actor_id)
    return Response(status_code=204)


@router.post('/{item_id}/images', status_code=201, response_model=LostRead,
             responses={403: {'description': 'Owner required'}, 404: {'description': 'Announcement missing'},
                        413: {'description': 'Image exceeds 5 MB'}, 422: {'description': 'Invalid images or image count'}})
def add_images(item_id: int, db: DatabaseSession, actor_id: int = Query(gt=0, le=MAX_IDENTIFIER),
               files: list[UploadFile] = File(...)):
    return lost_images.upload_images(db, item_id, actor_id, files)


@router.delete('/{item_id}/images/{image_id}', status_code=204)
def remove_image(item_id: int, image_id: str, db: DatabaseSession, actor_id: int = Query(gt=0, le=MAX_IDENTIFIER)):
    lost_images.delete_image(db, item_id, actor_id, image_id)
    return Response(status_code=204)
