from collections.abc import Iterable

import grpc
from shared.proto import counters_pb2 as pb
from shared.rpc import within_deadline
from starlette.datastructures import State

from app.config import get_settings
from app.rpc.deps import get_user_id
from app.services.counters import InvalidPostIds, PostCounters, normalize_post_ids


class CountersRpc:
    state: State

    async def GetCounters(self, request: pb.GetCountersRequest, context: grpc.aio.ServicerContext) -> pb.PostCounters:
        [counters] = await self.get_many([request.post_id], context)
        return counters

    async def BatchGetCounters(
        self, request: pb.BatchGetCountersRequest, context: grpc.aio.ServicerContext
    ) -> pb.BatchGetCountersReply:
        return pb.BatchGetCountersReply(counters=await self.get_many(request.post_ids, context))

    async def get_many(self, raw_ids: Iterable[int], context: grpc.aio.ServicerContext) -> list[pb.PostCounters]:
        user_id = await get_user_id(context)
        try:
            post_ids = normalize_post_ids(raw_ids, get_settings().max_batch_posts)
        except InvalidPostIds as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        async with within_deadline(context):
            counters = await self.state.counters.get_many(post_ids, user_id)
        return [to_message(item) for item in counters]


def to_message(counters: PostCounters) -> pb.PostCounters:
    return pb.PostCounters(
        post_id=counters.post_id, likes=counters.likes, views=counters.views, liked_by_me=counters.liked_by_me
    )
