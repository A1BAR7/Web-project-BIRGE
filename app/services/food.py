"""Däm validation, filtering and record management; assets are shared/read-only."""
from pathlib import Path
from fastapi import HTTPException
from app.models import FoodItem
from app.services.core import apply_update, create, get_or_404, list_records

FOOD_IMAGES = Path(__file__).resolve().parents[2] / 'static/images/food'


def validate_image_url(value):
    prefix = '/static/images/food/'
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError('Use an existing local /static/images/food/ asset')
    filename = value[len(prefix):]
    if not filename or '/' in filename or '\\' in filename or filename in {'.', '..'}:
        raise ValueError('Invalid image filename')
    if Path(filename).suffix.lower() not in {'.svg', '.jpg', '.jpeg', '.png', '.webp'} or not (FOOD_IMAGES / filename).is_file():
        raise ValueError('Image asset does not exist')
    return value


def image_metadata(url, name):
    # Source manifest contains licensing/provenance for any downloaded photographs.
    import json
    manifest = FOOD_IMAGES / 'credits.json'
    credits = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    info = credits.get(url.rsplit('/', 1)[-1], {})
    return {'image_kind': info.get('kind', 'placeholder'),
            'image_alt': info.get('alt', f'{name} — photo unavailable / Фото жоқ'),
            'image_credit': info.get('credit', ''), 'image_source': info.get('source', '')}


#123456
def list_food(db, canteen, category, search, min_price, max_price):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, 'min_price must not exceed max_price')
    filters = []
    if min_price is not None:
        filters.append(FoodItem.price >= min_price)
    if max_price is not None:
        filters.append(FoodItem.price <= max_price)
    return [item for item in list_records(db, FoodItem, *filters)
            if (canteen is None or item.canteen.casefold() == canteen.casefold())
            and (category is None or item.category.casefold() == category.casefold())
            and (not search or search.casefold() in item.name.casefold())]


def create_food(db, body):
    return create(db, FoodItem, body, **image_metadata(body.image_url, body.name))


def update_food(db, food_id, body):
    item = get_or_404(db, FoodItem, food_id, lock=True)
    apply_update(item, body)
    for field, value in image_metadata(item.image_url, item.name).items():
        setattr(item, field, value)
    db.commit()
    return item
