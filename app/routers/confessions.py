from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from app.database import DatabaseSession
from app.models import Confession, ConfessionLike
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas import ConfessionCreate, ConfessionRead, ConfessionUpdate
from app.services.core import create, get_or_404

router = APIRouter(prefix='/confessions', tags=['Ishimде'], dependencies=[Depends(get_current_active_user)])


def public(post, likes):
    return ConfessionRead(id=post.id, text=post.text, likes=likes)


def like_count(db, post_id):
    return db.scalar(select(func.count()).select_from(ConfessionLike).where(ConfessionLike.post_id == post_id))


@router.post('', status_code=201, response_model=ConfessionRead)
def add_confession(body: ConfessionCreate, db: DatabaseSession, user: CurrentUser):
    return public(create(db, Confession, body, author_id=user.id), 0)


@router.get('', response_model=list[ConfessionRead])
def list_confessions(db: DatabaseSession):
    counts = (
        select(ConfessionLike.post_id, func.count().label('likes'))
        .group_by(ConfessionLike.post_id)
        .subquery()
    )
    posts = select(Confession, func.coalesce(counts.c.likes, 0)).outerjoin(
        counts, counts.c.post_id == Confession.id,
    ).order_by(Confession.id)
    return [public(post, likes) for post, likes in db.execute(posts)]


@router.get('/{post_id}', response_model=ConfessionRead)
def get_confession(post_id: int, db: DatabaseSession):
    post = get_or_404(db, Confession, post_id)
    return public(post, like_count(db, post_id))


@router.patch('/{post_id}', response_model=ConfessionRead)
def edit_confession(post_id: int, body: ConfessionUpdate, db: DatabaseSession, user: CurrentUser):
    post = get_or_404(db, Confession, post_id, lock=True)
    if post.author_id != user.id:
        raise HTTPException(403, 'Only author can edit')
    post.text = body.text
    result = public(post, like_count(db, post_id))
    db.commit()
    return result


@router.post('/{post_id}/likes', response_model=ConfessionRead)
def like(post_id: int, db: DatabaseSession, user: CurrentUser):
    post = get_or_404(db, Confession, post_id, lock=True)
    if db.get(ConfessionLike, (post_id, user.id)) is not None:
        raise HTTPException(409, 'Already liked')
    db.add(ConfessionLike(post_id=post_id, user_id=user.id))
    result = public(post, like_count(db, post_id))
    db.commit()
    return result


@router.delete('/{post_id}/likes', status_code=204)
def unlike(post_id: int, db: DatabaseSession, user: CurrentUser):
    get_or_404(db, Confession, post_id, lock=True)
    reaction = db.get(ConfessionLike, (post_id, user.id))
    if reaction is None:
        raise HTTPException(404, 'Like not found')
    db.delete(reaction)
    db.commit()
    return Response(status_code=204)


@router.delete('/{post_id}', status_code=204)
def remove_confession(post_id: int, db: DatabaseSession, user: CurrentUser):
    post = get_or_404(db, Confession, post_id, lock=True)
    if post.author_id != user.id and user.role != 'admin':
        raise HTTPException(403, 'Only author or admin can delete')
    db.delete(post)
    db.commit()
    return Response(status_code=204)
