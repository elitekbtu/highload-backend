LIKES_FIELD = "likes"
VIEWS_FIELD = "views"
OFFSET_FIELD = "offset"
VIEW_DEDUP_TTL_SECONDS = 3600


def counter_key(post_id: int) -> str:
    return f"counter:{{{post_id}}}"


def view_dedup_key(post_id: int, user_id: int) -> str:
    return f"view:{{{post_id}}}:{user_id}"
