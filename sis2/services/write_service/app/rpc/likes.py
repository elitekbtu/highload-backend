import grpc
from shared.events import CounterEvent, EventType
from shared.proto import counters_pb2 as pb
from shared.rpc import event_id_from_key

from app.rpc.deps import RpcHandlers, publishing


class LikesRpc(RpcHandlers):
    async def Like(self, request: pb.LikeRequest, context: grpc.aio.ServicerContext) -> pb.WriteReply:
        return await self.publish_like(EventType.LIKE, request, context)

    async def Unlike(self, request: pb.LikeRequest, context: grpc.aio.ServicerContext) -> pb.WriteReply:
        return await self.publish_like(EventType.UNLIKE, request, context)

    async def publish_like(
        self, kind: EventType, request: pb.LikeRequest, context: grpc.aio.ServicerContext
    ) -> pb.WriteReply:
        user_id = await self.authorize(context, request.post_id)
        event_id = await event_id_from_key(context, request.idempotency_key)
        async with publishing(context):
            await self.container.publisher.publish(
                CounterEvent(event_id=event_id, type=kind, post_id=request.post_id, user_id=user_id)
            )
        return pb.WriteReply()
