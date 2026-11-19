from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas import StoredText


class FoodCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: StoredText = Field(min_length=1, max_length=100)
    description: StoredText = Field(default='', max_length=1000)
    price: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal['KZT'] = 'KZT'
    category: StoredText = Field(min_length=1, max_length=80)
    canteen: StoredText = Field(min_length=1, max_length=100)
    image_url: StoredText = '/static/images/food/placeholder.svg'
    available: bool = True

    @field_validator('image_url')
    @classmethod
    def local_image(cls, value):
        # Only shipped local assets: no unsafe schemes, traversal or stale remote URLs.
        from app.services.food import validate_image_url
        return validate_image_url(value)


class FoodUpdate(FoodCreate):
    name: StoredText | None = Field(default=None, min_length=1, max_length=100)
    description: StoredText | None = Field(default=None, max_length=1000)
    price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: Literal['KZT'] | None = None
    category: StoredText | None = Field(default=None, min_length=1, max_length=80)
    canteen: StoredText | None = Field(default=None, min_length=1, max_length=100)
    image_url: StoredText | None = None
    available: bool | None = None


class FoodRead(FoodCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    image_kind: Literal['placeholder', 'representative', 'authentic'] = 'placeholder'
    image_alt: str
    image_credit: str = ''
    image_source: str = ''

    @field_validator('created_at')
    @classmethod
    def utc_timestamp(cls, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
