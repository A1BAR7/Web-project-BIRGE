"""Shared database configuration for FastAPI and Alembic."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    value = os.getenv('DATABASE_URL')
    if not value:
        raise ValueError('Set DATABASE_URL to your PostgreSQL connection URL.')
    try:
        url = make_url(value)
    except (ArgumentError, ValueError):
        raise ValueError('DATABASE_URL is invalid.') from None
    if url.drivername in {'postgres', 'postgresql'}:
        return url.set(drivername='postgresql+psycopg')
    if url.drivername != 'postgresql+psycopg':
        raise ValueError('DATABASE_URL must use PostgreSQL with psycopg.')
    return url

#123456
@lru_cache(maxsize=1)
def session_factory():
    engine = create_engine(
        database_url(), 
        pool_pre_ping=True, 
        hide_parameters=True)
    return sessionmaker(engine, expire_on_commit=False)


def get_session():
    try:
        factory = session_factory()
    except ValueError as error:
        raise HTTPException(503, str(error)) from None
    with factory() as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_session)]
