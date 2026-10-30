import grpc
from shared.proto import counters_pb2 as pb
from shared.rpc import event_id_from_key

from app.rpc.deps import RpcHandlers, publishing
from app.services.view_token import InvalidViewToken
from app.services.views import count_view


class ViewsRpc(RpcHandlers):
    async def ViewStarted(
        self, request: pb.ViewStartedRequest, context: grpc.aio.ServicerContext
    ) -> pb.ViewStartedReply:
        user_id = await self.authorize(context, request.post_id)
        return pb.ViewStartedReply(view_token=self.container.view_tokens.issue(request.post_id, user_id))

    async def ViewFinished(self, request: pb.ViewFinishedRequest, context: grpc.aio.ServicerContext) -> pb.WriteReply:
        user_id = await self.authorize(context, request.post_id)
        event_id = await event_id_from_key(context, request.idempotency_key)
        try:
            self.container.view_tokens.verify(request.view_token, request.post_id, user_id)
        except InvalidViewToken as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        async with publishing(context):
            counted = await count_view(
                request.post_id, user_id, event_id, self.container.dedup, self.container.publisher
            )
        return pb.WriteReply(already_counted=not counted)
