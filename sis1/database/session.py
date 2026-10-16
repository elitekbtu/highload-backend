from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

settings = get_settings()


engine = create_engine(
    url=settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
    echo=False,
)


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, _):
    
    previous_autocommit = connection.autocommit
    connection.autocommit = True

    cursor = connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
        connection.autocommit = previous_autocommit


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    with SessionLocal() as session:
        yield session


SessionDB = Annotated[Session, Depends(get_db)]
