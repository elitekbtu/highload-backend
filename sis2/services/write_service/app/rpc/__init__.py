import grpc
from shared.proto.counters_pb2_grpc import CounterWriteServiceServicer, add_CounterWriteServiceServicer_to_server

from app.container import Container
from app.rpc.likes import LikesRpc
from app.rpc.views import ViewsRpc


class CounterWriteService(LikesRpc, ViewsRpc, CounterWriteServiceServicer):
    def __init__(self, container: Container):
        self.container = container


def create_server(container: Container) -> grpc.aio.Server:
    server = grpc.aio.server()
    add_CounterWriteServiceServicer_to_server(CounterWriteService(container), server)
    server.add_insecure_port(f"[::]:{container.settings.grpc_port}")
    return server
