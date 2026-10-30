import jwt


class Unauthorized(Exception):
    pass


def user_id_from_header(authorization: str | None, secret: str) -> int:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("missing bearer token")
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub"]})
        return int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise Unauthorized("invalid token") from exc
