import time
from typing import Annotated

import jwt
from fastapi import Depends, Request


class InvalidViewToken(Exception):
    pass


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


class ViewTokens:
    def __init__(self, secret: str, ttl_seconds: int, min_seconds: float):
        self.secret = secret
        self.ttl_seconds = ttl_seconds
        self.min_ms = int(min_seconds * 1000)

    def issue(self, post_id: int, user_id: int) -> str:
        claims = {"pid": post_id, "uid": user_id, "t": _now_ms(), "exp": int(time.time()) + self.ttl_seconds}
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def verify(self, token: str, post_id: int, user_id: int) -> None:
        try:
            claims = jwt.decode(
                token, self.secret, algorithms=["HS256"], options={"require": ["pid", "uid", "t", "exp"]}
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidViewToken("invalid view token") from exc
        if claims["pid"] != post_id or claims["uid"] != user_id:
            raise InvalidViewToken("view token does not match post or user")
        if _now_ms() - claims["t"] < self.min_ms:
            raise InvalidViewToken("view is too short")


async def get_view_tokens(request: Request) -> ViewTokens:
    return request.app.state.view_tokens


ViewTokensDep = Annotated[ViewTokens, Depends(get_view_tokens)]
