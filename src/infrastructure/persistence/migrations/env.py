import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from app.core.database import Base
from app.models import order, product  # noqa: F401 - register models on Base.metadata

load_dotenv()


config = context.config
target_metadata = Base.metadata


def get_database_url() -> str:
    sync_db_url = os.getenv("SYNC_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not sync_db_url:
        raise RuntimeError("SYNC_DATABASE_URL environment variable is not set")
    return sync_db_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
