from datetime import datetime
from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

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
    owner_id: ActorId
    resolved: bool = False
    images: list[LostImage] = Field(default_factory=list)

class SkillCreate(BaseModel):
    name: StoredText = Field(min_length=3,max_length=100)
    person: StoredText = Field(min_length=2,max_length=60)
    kind: Literal['teach','learn']
    detail: StoredText = Field(min_length=5,max_length=500)
    exchange: StoredText = Field(min_length=2,max_length=120)

class SkillRead(SkillCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: ActorId
    active: bool

class SkillUpdate(BaseModel):
    name: StoredText | None = Field(default=None,min_length=3,max_length=100)
    detail: StoredText | None = Field(default=None,min_length=5,max_length=500)
    exchange: StoredText | None = Field(default=None,min_length=2,max_length=120)

class RequestCreate(BaseModel):
    message: StoredText = Field(min_length=3,max_length=300)

class RequestRead(RequestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    applicant_id: ActorId
    skill_id: int
    status: Literal['pending', 'accepted', 'rejected']

class ConfessionCreate(BaseModel):
    text: StoredText = Field(min_length=3,max_length=280)

class ConfessionUpdate(BaseModel):
    text: StoredText = Field(min_length=3,max_length=280)

class ConfessionRead(ConfessionUpdate):
    id: int
    likes: int = Field(ge=0)


class UserRegister(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr = Field(max_length=254)
    username: StoredText = Field(min_length=3, max_length=30, pattern=r'^[A-Za-z0-9_.-]+$')
    password: StoredText = Field(min_length=8, max_length=128)

    @field_validator('email', 'username')
    @classmethod
    def lowercase(cls, value):
        return value.lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    username: str
    role: Literal['user', 'admin']
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'admin'] | None = None
    is_active: bool | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int
