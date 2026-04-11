from multiprocessing import context
from dotenv import load_dotenv
import os
from app.core.database import Base
from sqlalchemy import create_engine, pool

load_dotenv()

def run_migrations_online() -> None:
    sync_db_url = os.getenv("SYNC_DATABASE_URL")
    if not sync_db_url:
        raise RuntimeError("SYNC_DATABASE_URL environment variable is not set")

    connectable = create_engine(sync_db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata = Base.metadata
        )

        with context.begin_transaction():
            context.run_migrations()