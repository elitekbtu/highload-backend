import asyncio
import json
import os
from collections.abc import Awaitable, Iterable

import grpc
import jwt
from shared.proto.counters_pb2_grpc import CounterReadServiceStub, CounterWriteServiceStub

GATEWAY = "localhost:8081"
WRITE_TIMEOUT = 1.0
READ_TIMEOUT = 0.3

SERVICE_CONFIG = {
    "methodConfig": [
        {
            "name": [{"service": "counters.v1.CounterWriteService"}, {"service": "counters.v1.CounterReadService"}],
            "retryPolicy": {
                "maxAttempts": 4,
                "initialBackoff": "0.05s",
                "maxBackoff": "0.5s",
                "backoffMultiplier": 2,
                "retryableStatusCodes": ["UNAVAILABLE"],
            },
        },
    ],
    "retryThrottling": {"maxTokens": 100, "tokenRatio": 0.1},
}


def auth(user_id: int) -> tuple[tuple[str, str]]:
    token = jwt.encode({"sub": str(user_id)}, os.environ["JWT_SECRET"], algorithm="HS256")
    return (("authorization", f"Bearer {token}"),)


def connect(retries: bool = True) -> tuple[grpc.aio.Channel, CounterWriteServiceStub, CounterReadServiceStub]:
    options: list[tuple[str, str | int]] = [("grpc.enable_retries", int(retries))]
    if retries:
        options.append(("grpc.service_config", json.dumps(SERVICE_CONFIG)))
    channel = grpc.aio.insecure_channel(GATEWAY, options=options)
    return channel, CounterWriteServiceStub(channel), CounterReadServiceStub(channel)


async def status(call: Awaitable) -> str:
    try:
        await call
        return "OK"
    except grpc.aio.AioRpcError as exc:
        return exc.code().name


async def paced(calls: Iterable[Awaitable], rate: float) -> list:
    tasks = []
    for call in calls:
        tasks.append(asyncio.ensure_future(call))
        await asyncio.sleep(1 / rate)
    return await asyncio.gather(*tasks)
