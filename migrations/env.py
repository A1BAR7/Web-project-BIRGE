from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.database import Base, database_url
import app.models  # register the tables on Base.metadata

config = context.config
target_metadata = Base.metadata


def migrate(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied_connection = config.attributes.get('connection')
    if supplied_connection is not None:
        migrate(supplied_connection)
    else:
        engine = create_engine(database_url(), poolclass=NullPool, hide_parameters=True)
        try:
            with engine.connect() as connection:
                migrate(connection)
        finally:
            engine.dispose()
