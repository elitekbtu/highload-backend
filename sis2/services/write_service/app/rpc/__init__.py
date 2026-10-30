import grpc
from shared.proto.counters_pb2_grpc import CounterWriteServiceServicer, add_CounterWriteServiceServicer_to_server
from starlette.datastructures import State

from app.rpc.likes import LikesRpc
from app.rpc.views import ViewsRpc


class CounterWriteService(LikesRpc, ViewsRpc, CounterWriteServiceServicer):
    def __init__(self, state: State):
        self.state = state


def create_server(state: State, port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    add_CounterWriteServiceServicer_to_server(CounterWriteService(state), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
