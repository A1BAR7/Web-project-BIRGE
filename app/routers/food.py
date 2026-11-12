from fastapi import APIRouter, Query, Response
from app.food_schemas import FoodCreate, FoodRead, FoodUpdate
from app.services import food
from app.services.core import get_or_404
from app.store import store

router = APIRouter(prefix='/food', tags=['Däm'])


@router.get('', response_model=list[FoodRead])
def list_items(canteen: str | None = Query(None, max_length=100),
               category: str | None = Query(None, max_length=80),
               search: str | None = Query(None, max_length=100),
               min_price: float | None = Query(None, ge=0, allow_inf_nan=False),
               max_price: float | None = Query(None, ge=0, allow_inf_nan=False)):
    return food.list_food(canteen, category, search, min_price, max_price)


@router.post('', response_model=FoodRead, status_code=201)
def create_item(body: FoodCreate):
    return food.create_food(body)


@router.get('/{food_id}', response_model=FoodRead)
def get_item(food_id: int):
    return get_or_404(store.food, food_id)


@router.patch('/{food_id}', response_model=FoodRead)
def update_item(food_id: int, body: FoodUpdate):
    return food.update_food(food_id, body)


@router.delete('/{food_id}', status_code=204)
def delete_item(food_id: int):
    get_or_404(store.food, food_id)
    del store.food[food_id]
    # Menu photographs are shared assets, not owned uploads. Keep them for other records.
    return Response(status_code=204)
