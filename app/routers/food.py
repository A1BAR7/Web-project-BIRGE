from fastapi import APIRouter, Query, Response
from app.database import DatabaseSession
from app.food_schemas import FoodCreate, FoodRead, FoodUpdate
from app.models import FoodItem
from app.services import food
from app.services.core import get_or_404

router = APIRouter(prefix='/food', tags=['Däm'])


@router.get('', response_model=list[FoodRead])
def list_items(db: DatabaseSession, canteen: str | None = Query(None, max_length=100),
               category: str | None = Query(None, max_length=80),
               search: str | None = Query(None, max_length=100),
               min_price: float | None = Query(None, ge=0, allow_inf_nan=False),
               max_price: float | None = Query(None, ge=0, allow_inf_nan=False)):
    return food.list_food(db, canteen, category, search, min_price, max_price)


@router.post('', response_model=FoodRead, status_code=201)
def create_item(body: FoodCreate, db: DatabaseSession):
    return food.create_food(db, body)


@router.get('/{food_id}', response_model=FoodRead)
def get_item(food_id: int, db: DatabaseSession):
    return get_or_404(db, FoodItem, food_id)


@router.patch('/{food_id}', response_model=FoodRead)
def update_item(food_id: int, body: FoodUpdate, db: DatabaseSession):
    return food.update_food(db, food_id, body)


@router.delete('/{food_id}', status_code=204)
def delete_item(food_id: int, db: DatabaseSession):
    db.delete(get_or_404(db, FoodItem, food_id, lock=True))
    db.commit()
    # Menu photographs are shared assets, not owned uploads. Keep them for other records.
    return Response(status_code=204)
