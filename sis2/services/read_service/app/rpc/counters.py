from collections.abc import Iterable

import grpc
from shared.proto import counters_pb2 as pb
from shared.rpc import user_id_from_context, within_deadline

from app.container import Container
from app.services.counters import InvalidPostIds, normalize_post_ids


class CountersRpc:
    container: Container

    async def GetCounters(self, request: pb.GetCountersRequest, context: grpc.aio.ServicerContext) -> pb.PostCounters:
        [counters] = await self.get_many([request.post_id], context)
        return counters

    async def BatchGetCounters(
        self, request: pb.BatchGetCountersRequest, context: grpc.aio.ServicerContext
    ) -> pb.BatchGetCountersReply:
        return pb.BatchGetCountersReply(counters=await self.get_many(request.post_ids, context))

    async def get_many(self, raw_ids: Iterable[int], context: grpc.aio.ServicerContext) -> list[pb.PostCounters]:
        user_id = await user_id_from_context(context, self.container.settings.jwt_secret)
        try:
            post_ids = normalize_post_ids(raw_ids, self.container.settings.max_batch_posts)
        except InvalidPostIds as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        async with within_deadline(context):
            counters = await self.container.counters.get_many(post_ids, user_id)
        return [pb.PostCounters(**item.model_dump()) for item in counters]
