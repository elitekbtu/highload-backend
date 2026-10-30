import argparse
import asyncio
import random
import uuid
from collections import Counter

import grpc
from client import READ_TIMEOUT, WRITE_TIMEOUT, auth, channel, stubs
from shared.proto import counters_pb2 as pb

RATE = 20


async def paced(calls):
    tasks = []
    for call in calls:
        tasks.append(asyncio.ensure_future(call()))
        await asyncio.sleep(1 / RATE)
    return await asyncio.gather(*tasks)


async def outcome(call) -> str:
    try:
        await call()
        return "OK"
    except grpc.aio.AioRpcError as exc:
        return exc.code().name


async def naive(make_call, attempts: int = 4) -> str:
    result = "UNAVAILABLE"
    for _ in range(attempts):
        result = await outcome(lambda: make_call(str(uuid.uuid4())))
        if result != "UNAVAILABLE":
            return result
        await asyncio.sleep(0.05)
    return result


async def run(mode: str, users: int, target: str) -> None:
    post_id = random.randint(10**9, 2 * 10**9)
    base = random.randint(10**6, 10**9)
    async with channel(target, retries=mode == "grpc") as chan:
        write, read = stubs(chan)

        async def get() -> pb.PostCounters:
            return await read.GetCounters(
                pb.GetCountersRequest(post_id=post_id), metadata=auth(1), timeout=READ_TIMEOUT
            )

        await get()

        def like_call(user_id: int):
            def call(key: str):
                request = pb.LikeRequest(post_id=post_id, idempotency_key=key)
                return write.Like(request, metadata=auth(user_id), timeout=WRITE_TIMEOUT)

            return call

        tokens = await paced(
            lambda user_id=user_id: write.ViewStarted(
                pb.ViewStartedRequest(post_id=post_id), metadata=auth(user_id), timeout=WRITE_TIMEOUT
            )
            for user_id in range(base, base + users)
        )
        await asyncio.sleep(2.1)

        def view_call(user_id: int, token: str):
            def call(key: str):
                request = pb.ViewFinishedRequest(post_id=post_id, view_token=token, idempotency_key=key)
                return write.ViewFinished(request, metadata=auth(user_id), timeout=WRITE_TIMEOUT)

            return call

        def attempt(make_call):
            if mode == "naive":
                return lambda: naive(make_call)
            key = str(uuid.uuid4())
            return lambda: outcome(lambda: make_call(key))

        views = await paced(attempt(view_call(base + i, t.view_token)) for i, t in enumerate(tokens))
        likes = await paced(attempt(like_call(user_id)) for user_id in range(base, base + users))

        await asyncio.sleep(2.5)
        counters = await get()

    print(f"mode={mode} users={users} post={post_id}")
    print(f"  view_finished: {dict(Counter(views))}")
    print(f"  like:          {dict(Counter(likes))}")
    print(f"  counters: views={counters.views} likes={counters.likes} (expected {users})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["none", "naive", "grpc"])
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--target", default="localhost:8081")
    args = parser.parse_args()
    asyncio.run(run(args.mode, args.users, args.target))


if __name__ == "__main__":
    main()
