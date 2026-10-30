import grpc
from shared.events import CounterEvent, EventType
from shared.proto import counters_pb2 as pb
from shared.rpc import event_id_from_key, within_deadline
from starlette.datastructures import State

from app.rpc.deps import check_post_id, get_user_id
from app.services.publisher import EventBusUnavailable


class LikesRpc:
    state: State

    async def Like(self, request: pb.LikeRequest, context: grpc.aio.ServicerContext) -> pb.WriteReply:
        return await self.publish_like(EventType.LIKE, request, context)

    async def Unlike(self, request: pb.LikeRequest, context: grpc.aio.ServicerContext) -> pb.WriteReply:
        return await self.publish_like(EventType.UNLIKE, request, context)

    async def publish_like(
        self, kind: EventType, request: pb.LikeRequest, context: grpc.aio.ServicerContext
    ) -> pb.WriteReply:
        user_id = await get_user_id(context)
        await check_post_id(request.post_id, context)
        event_id = await event_id_from_key(context, request.idempotency_key)
        event = CounterEvent(event_id=event_id, type=kind, post_id=request.post_id, user_id=user_id)
        async with within_deadline(context):
            try:
                await self.state.publisher.publish(event)
            except EventBusUnavailable as exc:
                await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
        return pb.WriteReply()
