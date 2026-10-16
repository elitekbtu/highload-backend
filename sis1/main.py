from contextlib import asynccontextmanager

from fastapi import FastAPI


from database.session import engine
from models import Base
from routes.like import router as like_router
from routes.view import router as view_router


@asynccontextmanager
async def lifespan(aap: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(lifespan=lifespan)

app.include_router(like_router)
app.include_router(view_router)
