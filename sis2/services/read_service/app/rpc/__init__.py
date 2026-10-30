import grpc
from shared.proto.counters_pb2_grpc import CounterReadServiceServicer, add_CounterReadServiceServicer_to_server

from app.container import Container
from app.rpc.counters import CountersRpc


class CounterReadService(CountersRpc, CounterReadServiceServicer):
    def __init__(self, container: Container):
        self.container = container


def create_server(container: Container) -> grpc.aio.Server:
    server = grpc.aio.server()
    add_CounterReadServiceServicer_to_server(CounterReadService(container), server)
    server.add_insecure_port(f"[::]:{container.settings.grpc_port}")
    return server
