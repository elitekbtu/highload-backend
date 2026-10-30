import grpc
from shared.proto import counters_pb2 as pb
from shared.rpc import event_id_from_key, within_deadline
from starlette.datastructures import State

from app.rpc.deps import check_post_id, get_user_id
from app.services.publisher import EventBusUnavailable
from app.services.view_token import InvalidViewToken
from app.services.views import count_view


class ViewsRpc:
    state: State

    async def ViewStarted(
        self, request: pb.ViewStartedRequest, context: grpc.aio.ServicerContext
    ) -> pb.ViewStartedReply:
        user_id = await get_user_id(context)
        await check_post_id(request.post_id, context)
        return pb.ViewStartedReply(view_token=self.state.view_tokens.issue(request.post_id, user_id))

    async def ViewFinished(self, request: pb.ViewFinishedRequest, context: grpc.aio.ServicerContext) -> pb.WriteReply:
        user_id = await get_user_id(context)
        await check_post_id(request.post_id, context)
        event_id = await event_id_from_key(context, request.idempotency_key)
        try:
            self.state.view_tokens.verify(request.view_token, request.post_id, user_id)
        except InvalidViewToken as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        async with within_deadline(context):
            try:
                counted = await count_view(request.post_id, user_id, event_id, self.state.dedup, self.state.publisher)
            except EventBusUnavailable as exc:
                await context.abort(grpc.StatusCode.UNAVAILABLE, str(exc))
        return pb.WriteReply(already_counted=not counted)
