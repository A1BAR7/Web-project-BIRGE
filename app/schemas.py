from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class LostCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    status: Literal['lost','found']
    place: str = Field(min_length=2,max_length=120)
    desc: str = Field(min_length=5,max_length=500)
    owner_id: int = Field(gt=0)

class LostUpdate(BaseModel):
    name: str | None = Field(default=None,min_length=3,max_length=100)
    place: str | None = Field(default=None,min_length=2,max_length=120)
    desc: str | None = Field(default=None,min_length=5,max_length=500)

class LostImage(BaseModel):
    id: str
    url: str

class LostRead(LostCreate):
    id: int
    resolved: bool = False
    images: list[LostImage] = Field(default_factory=list)

class SkillCreate(BaseModel):
    name: str = Field(min_length=3,max_length=100)
    person: str = Field(min_length=2,max_length=60)
    kind: Literal['teach','learn']
    detail: str = Field(min_length=5,max_length=500)
    exchange: str = Field(min_length=2,max_length=120)
    owner_id: int = Field(gt=0)

class SkillUpdate(BaseModel):
    name: str | None = Field(default=None,min_length=3,max_length=100)
    detail: str | None = Field(default=None,min_length=5,max_length=500)
    exchange: str | None = Field(default=None,min_length=2,max_length=120)

class RequestCreate(BaseModel):
    applicant_id: int = Field(gt=0)
    message: str = Field(min_length=3,max_length=300)

class ConfessionCreate(BaseModel):
    text: str = Field(min_length=3,max_length=280)
    author_id: int = Field(gt=0)

class ConfessionUpdate(BaseModel):
    text: str = Field(min_length=3,max_length=280)
