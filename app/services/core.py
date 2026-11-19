from fastapi import HTTPException
from sqlalchemy import select

from app.schemas import MAX_IDENTIFIER


def get_or_404(db, model, item_id, *, lock=False):
    # Oversized path IDs cannot match a signed BIGINT primary key.
    item = db.get(model, item_id, with_for_update=lock) if 0 < item_id <= MAX_IDENTIFIER else None
    if item is None:
        raise HTTPException(404, 'Resource not found')
    return item


def list_records(db, model, *filters):
    return list(db.scalars(select(model).where(*filters).order_by(model.id)))


def create(db, model, body, **fields):
    item = model(**body.model_dump(), **fields)
    db.add(item)
    db.commit()
    return item


def apply_update(item, body):
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(422, 'Fields cannot be null')
    for key, value in changes.items():
        setattr(item, key, value)


def owner_only(item, actor_id):
    if item.owner_id != actor_id:
        raise HTTPException(403, 'Only the owner may perform this operation')
