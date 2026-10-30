from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class LikeRequest(_message.Message):
    __slots__ = ("post_id", "idempotency_key")
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    post_id: int
    idempotency_key: str
    def __init__(self, post_id: _Optional[int] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class ViewStartedRequest(_message.Message):
    __slots__ = ("post_id",)
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    post_id: int
    def __init__(self, post_id: _Optional[int] = ...) -> None: ...

class ViewStartedReply(_message.Message):
    __slots__ = ("view_token",)
    VIEW_TOKEN_FIELD_NUMBER: _ClassVar[int]
    view_token: str
    def __init__(self, view_token: _Optional[str] = ...) -> None: ...

class ViewFinishedRequest(_message.Message):
    __slots__ = ("post_id", "view_token", "idempotency_key")
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    VIEW_TOKEN_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    post_id: int
    view_token: str
    idempotency_key: str
    def __init__(self, post_id: _Optional[int] = ..., view_token: _Optional[str] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class WriteReply(_message.Message):
    __slots__ = ("already_counted",)
    ALREADY_COUNTED_FIELD_NUMBER: _ClassVar[int]
    already_counted: bool
    def __init__(self, already_counted: _Optional[bool] = ...) -> None: ...

class GetCountersRequest(_message.Message):
    __slots__ = ("post_id",)
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    post_id: int
    def __init__(self, post_id: _Optional[int] = ...) -> None: ...

class BatchGetCountersRequest(_message.Message):
    __slots__ = ("post_ids",)
    POST_IDS_FIELD_NUMBER: _ClassVar[int]
    post_ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, post_ids: _Optional[_Iterable[int]] = ...) -> None: ...

class PostCounters(_message.Message):
    __slots__ = ("post_id", "likes", "views", "liked_by_me")
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    LIKES_FIELD_NUMBER: _ClassVar[int]
    VIEWS_FIELD_NUMBER: _ClassVar[int]
    LIKED_BY_ME_FIELD_NUMBER: _ClassVar[int]
    post_id: int
    likes: int
    views: int
    liked_by_me: bool
    def __init__(self, post_id: _Optional[int] = ..., likes: _Optional[int] = ..., views: _Optional[int] = ..., liked_by_me: _Optional[bool] = ...) -> None: ...

class BatchGetCountersReply(_message.Message):
    __slots__ = ("counters",)
    COUNTERS_FIELD_NUMBER: _ClassVar[int]
    counters: _containers.RepeatedCompositeFieldContainer[PostCounters]
    def __init__(self, counters: _Optional[_Iterable[_Union[PostCounters, _Mapping]]] = ...) -> None: ...
