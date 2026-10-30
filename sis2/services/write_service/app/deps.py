from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path
from shared.auth import Unauthorized, user_id_from_header

from app.config import get_settings


async def get_user_id(authorization: Annotated[str | None, Header()] = None) -> int:
    try:
        return user_id_from_header(authorization, get_settings().jwt_secret)
    except Unauthorized as exc:
        raise HTTPException(401, str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc


UserIdDep = Annotated[int, Depends(get_user_id)]
PostId = Annotated[int, Path(gt=0, le=2**63 - 1)]
