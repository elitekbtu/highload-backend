from typing import Annotated

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


UserIdDep = Annotated[int, Depends(get_user_id)]
PostId = Annotated[int, Path(gt=0, le=2**63 - 1)]
