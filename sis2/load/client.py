import json
import os

import grpc
import jwt
from shared.proto.counters_pb2_grpc import CounterReadServiceStub, CounterWriteServiceStub

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-jwt")

WRITE_TIMEOUT = 1.0
READ_TIMEOUT = 0.3

RETRY_POLICY = {
    "maxAttempts": 4,
    "initialBackoff": "0.05s",
    "maxBackoff": "0.5s",
    "backoffMultiplier": 2,
    "retryableStatusCodes": ["UNAVAILABLE"],
}

SERVICE_CONFIG = {
    "methodConfig": [
        {
            "name": [{"service": "counters.v1.CounterWriteService"}, {"service": "counters.v1.CounterReadService"}],
            "retryPolicy": RETRY_POLICY,
        },
    ],
    "retryThrottling": {"maxTokens": 100, "tokenRatio": 0.1},
}


def token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id)}, JWT_SECRET, algorithm="HS256")


def auth(user_id: int) -> tuple[tuple[str, str], ...]:
    return (("authorization", f"Bearer {token(user_id)}"),)


def channel(target: str, retries: bool = True) -> grpc.aio.Channel:
    options: list[tuple[str, str | int]] = [("grpc.enable_retries", int(retries))]
    if retries:
        options.append(("grpc.service_config", json.dumps(SERVICE_CONFIG)))
    return grpc.aio.insecure_channel(target, options=options)


def stubs(chan: grpc.aio.Channel) -> tuple[CounterWriteServiceStub, CounterReadServiceStub]:
    return CounterWriteServiceStub(chan), CounterReadServiceStub(chan)
