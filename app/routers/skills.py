from fastapi import APIRouter, HTTPException, Response, Query
from typing import Literal
from app.schemas import SkillCreate, SkillUpdate, RequestCreate
from app.store import store
from app.services.core import create, update, delete, get_or_404, owner_only

router = APIRouter(prefix='/skills', tags=['SkillQos'])

@router.post('',status_code=201)
def add_skill(body: SkillCreate):
    obj = create(store.skills,body)
    obj['active'] = True
    return obj

@router.get('')
def list_skills(kind: Literal['teach','learn'] | None = None, q: str | None = Query(None,max_length=100)):
    return [s for s in store.skills.values() if (kind is None or s['kind']==kind) and (not q or q.casefold() in (s['name']+' '+s['detail']).casefold())]

@router.get('/{skill_id}')
def get_skill(skill_id: int):
    return get_or_404(store.skills,skill_id)

@router.patch('/{skill_id}')
def edit_skill(skill_id: int,body: SkillUpdate,actor_id: int = Query(gt=0)):
    owner_only(get_or_404(store.skills,skill_id),actor_id)
    return update(store.skills,skill_id,body)

@router.delete('/{skill_id}',status_code=204)
def remove_skill(skill_id: int,actor_id: int = Query(gt=0)):
    owner_only(get_or_404(store.skills,skill_id),actor_id)
    delete(store.skills,skill_id)
    for rid in [rid for rid,r in store.requests.items() if r['skill_id']==skill_id]:
        del store.requests[rid]
    return Response(status_code=204)

@router.post('/{skill_id}/requests',status_code=201)
def request_skill(skill_id: int,body: RequestCreate):
    skill = get_or_404(store.skills,skill_id)
    if body.applicant_id == skill['owner_id']:
        raise HTTPException(409,'Cannot apply to your own skill')
    if any(r['skill_id']==skill_id and r['applicant_id']==body.applicant_id and r['status']=='pending' for r in store.requests.values()):
        raise HTTPException(409,'Pending request already exists')
    obj = {'id':store.new_id(),'skill_id':skill_id,**body.model_dump(),'status':'pending'}
    store.requests[obj['id']] = obj
    return obj

@router.get('/{skill_id}/requests')
def list_requests(skill_id: int,actor_id: int = Query(gt=0)):
    owner_only(get_or_404(store.skills,skill_id),actor_id)
    return [r for r in store.requests.values() if r['skill_id']==skill_id]

@router.patch('/{skill_id}/requests/{request_id}')
def decide_request(skill_id: int,request_id: int,decision: Literal['accepted','rejected'],actor_id: int = Query(gt=0)):
    owner_only(get_or_404(store.skills,skill_id),actor_id)
    obj = get_or_404(store.requests,request_id)
    if obj['skill_id'] != skill_id: raise HTTPException(404,'Request does not belong to skill')
    if obj['status'] != 'pending': raise HTTPException(409,'Request already decided')
    obj['status'] = decision
    return obj
