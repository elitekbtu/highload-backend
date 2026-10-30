import grpc
from shared.proto.counters_pb2_grpc import CounterReadServiceServicer, add_CounterReadServiceServicer_to_server
from starlette.datastructures import State

from app.rpc.counters import CountersRpc


class CounterReadService(CountersRpc, CounterReadServiceServicer):
    def __init__(self, state: State):
        self.state = state


def create_server(state: State, port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    add_CounterReadServiceServicer_to_server(CounterReadService(state), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
