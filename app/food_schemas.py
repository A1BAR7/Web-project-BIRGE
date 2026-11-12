from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FoodCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=1000)
    price: float = Field(gt=0, allow_inf_nan=False)
    currency: Literal['KZT'] = 'KZT'
    category: str = Field(min_length=1, max_length=80)
    canteen: str = Field(min_length=1, max_length=100)
    image_url: str = '/static/images/food/placeholder.svg'
    available: bool = True

    @field_validator('image_url')
    @classmethod
    def local_image(cls, value):
        # Only shipped local assets: no unsafe schemes, traversal or stale remote URLs.
        from app.services.food import validate_image_url
        return validate_image_url(value)


class FoodUpdate(FoodCreate):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: Literal['KZT'] | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    canteen: str | None = Field(default=None, min_length=1, max_length=100)
    image_url: str | None = None
    available: bool | None = None


class FoodRead(FoodCreate):
    id: int
    created_at: datetime
    image_kind: Literal['placeholder', 'representative', 'authentic'] = 'placeholder'
    image_alt: str
    image_credit: str = ''
    image_source: str = ''
