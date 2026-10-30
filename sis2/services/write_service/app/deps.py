from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, Header, HTTPException, Path, Request
from shared.auth import Unauthorized, user_id_from_header

from app.container import Container


async def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


async def get_user_id(container: ContainerDep, authorization: Annotated[str | None, Header()] = None) -> int:
    try:
        return user_id_from_header(authorization, container.settings.jwt_secret)
    except Unauthorized as exc:
        raise HTTPException(401, str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc


async def get_event_id(idempotency_key: Annotated[UUID | None, Header()] = None) -> UUID:
    return idempotency_key or uuid4()


UserIdDep = Annotated[int, Depends(get_user_id)]
IdempotencyKey = Annotated[UUID, Depends(get_event_id)]
PostId = Annotated[int, Path(gt=0, le=2**63 - 1)]
