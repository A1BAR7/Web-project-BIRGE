from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

MAX_IDENTIFIER = 2**63 - 1

ActorId = Annotated[int, Field(gt=0, le=MAX_IDENTIFIER)]


def reject_null_byte(value):
    if '\x00' in value:
        raise ValueError('Text cannot contain a null byte')
    return value


StoredText = Annotated[str, AfterValidator(reject_null_byte)]

class LostCreate(BaseModel):
    name: StoredText = Field(min_length=3, max_length=100)
    status: Literal['lost','found']
    place: StoredText = Field(min_length=2,max_length=120)
    desc: StoredText = Field(min_length=5,max_length=500)
    owner_id: ActorId

class LostUpdate(BaseModel):
    name: StoredText | None = Field(default=None,min_length=3,max_length=100)
    place: StoredText | None = Field(default=None,min_length=2,max_length=120)
    desc: StoredText | None = Field(default=None,min_length=5,max_length=500)

class LostImage(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    url: str

class LostRead(LostCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resolved: bool = False
    images: list[LostImage] = Field(default_factory=list)

class SkillCreate(BaseModel):
    name: StoredText = Field(min_length=3,max_length=100)
    person: StoredText = Field(min_length=2,max_length=60)
    kind: Literal['teach','learn']
    detail: StoredText = Field(min_length=5,max_length=500)
    exchange: StoredText = Field(min_length=2,max_length=120)
    owner_id: ActorId

class SkillRead(SkillCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    active: bool

class SkillUpdate(BaseModel):
    name: StoredText | None = Field(default=None,min_length=3,max_length=100)
    detail: StoredText | None = Field(default=None,min_length=5,max_length=500)
    exchange: StoredText | None = Field(default=None,min_length=2,max_length=120)

class RequestCreate(BaseModel):
    applicant_id: ActorId
    message: StoredText = Field(min_length=3,max_length=300)

class RequestRead(RequestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    skill_id: int
    status: Literal['pending', 'accepted', 'rejected']

class ConfessionCreate(BaseModel):
    text: StoredText = Field(min_length=3,max_length=280)
    author_id: ActorId

class ConfessionUpdate(BaseModel):
    text: StoredText = Field(min_length=3,max_length=280)

class ConfessionRead(ConfessionUpdate):
    id: int
    likes: int = Field(ge=0)
