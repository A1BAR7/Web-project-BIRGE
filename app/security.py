"""Password hashing (Argon2id) and JWT access tokens."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from dotenv import load_dotenv

_hasher = PasswordHasher()
# Verified against when the account does not exist, so login timing doesn't reveal it.
_DUMMY_HASH = _hasher.hash('birge-dummy-password')
MIN_SECRET_LENGTH = 32


class AuthConfigError(RuntimeError):
    pass


def hash_password(password):
    return _hasher.hash(password)


def verify_password(password, hashed=None):
    try:
        return _hasher.verify(hashed or _DUMMY_HASH, password) and hashed is not None
    except (VerificationError, InvalidHashError):
        return False


def settings():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    secret = os.getenv('SECRET_KEY', '')
    if len(secret) < MIN_SECRET_LENGTH:
        raise AuthConfigError(f'Set SECRET_KEY to a random string of at least {MIN_SECRET_LENGTH} characters.')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
    if algorithm not in {'HS256', 'HS384', 'HS512'}:
        raise AuthConfigError('JWT_ALGORITHM must be HS256, HS384 or HS512.')
    try:
        minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    except ValueError:
        raise AuthConfigError('ACCESS_TOKEN_EXPIRE_MINUTES must be an integer.') from None
    if minutes <= 0:
        raise AuthConfigError('ACCESS_TOKEN_EXPIRE_MINUTES must be positive.')
    return secret, algorithm, minutes


def create_access_token(user_id):
    secret, algorithm, minutes = settings()
    now = datetime.now(timezone.utc)
    claims = {'sub': str(user_id), 'iat': now, 'exp': now + timedelta(minutes=minutes)}
    return jwt.encode(claims, secret, algorithm=algorithm), minutes * 60


def decode_access_token(token):
    """Return the user id from a valid token, or None."""
    secret, algorithm, _ = settings()
    try:
        claims = jwt.decode(token, secret, algorithms=[algorithm], options={'require': ['exp', 'sub']})
        return int(claims['sub'])
    except (jwt.PyJWTError, ValueError):
        return None
