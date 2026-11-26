from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select

from app.database import DatabaseSession
from app.dependencies import AdminUser, CurrentUser
from app.models import User
from app.schemas import Token, UserAdminUpdate, UserRead, UserRegister
from app.security import AuthConfigError, create_access_token, hash_password, verify_password
from app.services.core import get_or_404

router = APIRouter(tags=['Auth'])


@router.post('/auth/register', status_code=201, response_model=UserRead)
def register(body: UserRegister, db: DatabaseSession):
    taken = db.scalar(select(User.id).where(or_(User.email == body.email, User.username == body.username)))
    if taken is not None:
        raise HTTPException(409, 'Email or username is already registered')
    # New accounts are always regular users; admins are created with scripts/create_admin.py.
    user = User(email=body.email, username=body.username, hashed_password=hash_password(body.password))
    db.add(user)
    db.commit()  # a concurrent duplicate hits the unique constraint and becomes a 409 in main.py
    return user


@router.post('/auth/login', response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DatabaseSession):
    """Log in with email or username; the form field is called `username` (OAuth2 standard)."""
    login_name = form.username.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == login_name, User.username == login_name)))
    if not verify_password(form.password, user.hashed_password if user else None):
        raise HTTPException(401, 'Incorrect email/username or password', headers={'WWW-Authenticate': 'Bearer'})
    if not user.is_active:
        raise HTTPException(403, 'Inactive user')
    try:
        token, expires_in = create_access_token(user.id)
    except AuthConfigError as error:
        raise HTTPException(503, str(error)) from None
    return Token(access_token=token, expires_in=expires_in)


@router.get('/auth/me', response_model=UserRead)
def me(user: CurrentUser):
    return user


@router.get('/users', response_model=list[UserRead])
def list_users(_admin: AdminUser, db: DatabaseSession):
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch('/users/{user_id}', response_model=UserRead)
def update_user(user_id: int, body: UserAdminUpdate, admin: AdminUser, db: DatabaseSession):
    user = get_or_404(db, User, user_id, lock=True)
    if user.id == admin.id and (body.role == 'user' or body.is_active is False):
        raise HTTPException(409, 'Administrators cannot demote or deactivate themselves')
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return user
