from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select

from app.database import DatabaseSession
from app.models import Skill, SkillRequest
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas import RequestCreate, RequestRead, SkillCreate, SkillRead, SkillUpdate
from app.services.core import apply_update, create, get_or_404, list_records, owner_only

router = APIRouter(prefix='/skills', tags=['SkillQos'], dependencies=[Depends(get_current_active_user)])


@router.post('', status_code=201, response_model=SkillRead)
def add_skill(body: SkillCreate, db: DatabaseSession, user: CurrentUser):
    return create(db, Skill, body, owner_id=user.id)


@router.get('', response_model=list[SkillRead])
def list_skills(db: DatabaseSession, kind: Literal['teach', 'learn'] | None = None,
                q: str | None = Query(None, max_length=100)):
    filters = [] if kind is None else [Skill.kind == kind]
    items = list_records(db, Skill, *filters)
    if not q:
        return items
    search = q.casefold()
    return [skill for skill in items if search in f'{skill.name} {skill.detail}'.casefold()]


@router.get('/{skill_id}', response_model=SkillRead)
def get_skill(skill_id: int, db: DatabaseSession):
    return get_or_404(db, Skill, skill_id)


@router.patch('/{skill_id}', response_model=SkillRead)
def edit_skill(skill_id: int, body: SkillUpdate, db: DatabaseSession, user: CurrentUser):
    skill = get_or_404(db, Skill, skill_id, lock=True)
    owner_only(skill, user)
    apply_update(skill, body)
    db.commit()
    return skill


@router.delete('/{skill_id}', status_code=204)
def remove_skill(skill_id: int, db: DatabaseSession, user: CurrentUser):
    skill = get_or_404(db, Skill, skill_id, lock=True)
    owner_only(skill, user, allow_admin=True)
    db.delete(skill)
    db.commit()
    return Response(status_code=204)


@router.post('/{skill_id}/requests', status_code=201, response_model=RequestRead)
def request_skill(skill_id: int, body: RequestCreate, db: DatabaseSession, user: CurrentUser):
    skill = get_or_404(db, Skill, skill_id, lock=True)
    if user.id == skill.owner_id:
        raise HTTPException(409, 'Cannot apply to your own skill')
    pending = select(SkillRequest.id).where(
        SkillRequest.skill_id == skill_id, SkillRequest.applicant_id == user.id,
        SkillRequest.status == 'pending',
    )
    if db.scalar(pending) is not None:
        raise HTTPException(409, 'Pending request already exists')
    return create(db, SkillRequest, body, skill_id=skill_id, applicant_id=user.id)


@router.get('/{skill_id}/requests', response_model=list[RequestRead])
def list_requests(skill_id: int, db: DatabaseSession, user: CurrentUser):
    owner_only(get_or_404(db, Skill, skill_id), user)
    return list_records(db, SkillRequest, SkillRequest.skill_id == skill_id)


@router.patch('/{skill_id}/requests/{request_id}', response_model=RequestRead)
def decide_request(skill_id: int, request_id: int, decision: Literal['accepted', 'rejected'],
                   db: DatabaseSession, user: CurrentUser):
    owner_only(get_or_404(db, Skill, skill_id, lock=True), user)
    request = get_or_404(db, SkillRequest, request_id)
    if request.skill_id != skill_id:
        raise HTTPException(404, 'Request does not belong to skill')
    if request.status != 'pending':
        raise HTTPException(409, 'Request already decided')
    request.status = decision
    db.commit()
    return request
