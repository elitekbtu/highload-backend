import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

from shared.models import Base
from shared.settings import DatabaseSettings

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

SHARD_URLS = DatabaseSettings().database_urls


def run_migrations_offline():
    context.configure(
        url=SHARD_URLS[0],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        connection.execute(text("SELECT pg_advisory_xact_lock(731215001)"))
        context.run_migrations()


async def run_async_migrations():
    urls = SHARD_URLS[:1] if getattr(config.cmd_opts, "autogenerate", False) else SHARD_URLS
    for url in urls:
        connectable = create_async_engine(url, poolclass=pool.NullPool)
        try:
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)
        finally:
            await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
