import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from app.database import get_session
from app.main import app


@pytest.fixture
def database_engine(tmp_path):
    url = os.getenv('TEST_DATABASE_URL')
    if url:
        # Keep the test tables separate even when several test runs overlap.
        schema = f'birge_test_{uuid4().hex}'
        admin_engine = create_engine(url)
        try:
            with admin_engine.begin() as connection:
                connection.execute(CreateSchema(schema))
            engine = create_engine(url, connect_args={'options': f'-c search_path={schema}'})
            try:
                yield engine
            finally:
                engine.dispose()
                with admin_engine.begin() as connection:
                    connection.execute(DropSchema(schema, cascade=True))
        finally:
            admin_engine.dispose()
    else:
        engine = create_engine(f'sqlite:///{(tmp_path / "birge.db").as_posix()}')

        @event.listens_for(engine, 'connect')
        def enable_foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

        try:
            yield engine
        finally:
            engine.dispose()


@pytest.fixture(autouse=True)
def sessions(database_engine):
    config = Config(str(Path(__file__).with_name('alembic.ini')))
    with database_engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
    factory = sessionmaker(database_engine, expire_on_commit=False)

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_session)
