"""Reusable authentication/authorization dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.database import DatabaseSession
from app.models import User
from app.security import AuthConfigError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DatabaseSession):
    try:
        user_id = decode_access_token(token)
    except AuthConfigError as error:
        raise HTTPException(503, str(error)) from None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, 'Invalid or expired token', headers={'WWW-Authenticate': 'Bearer'})
    return user


def get_current_active_user(user: Annotated[User, Depends(get_current_user)]):
    if not user.is_active:
        raise HTTPException(403, 'Inactive user')
    return user


def get_current_admin_user(user: Annotated[User, Depends(get_current_active_user)]):
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator privileges required')
    return user


CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
