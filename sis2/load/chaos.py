import asyncio
import random
import sys
import uuid
from collections import Counter

from client import READ_TIMEOUT, WRITE_TIMEOUT, auth, connect, paced, status
from shared.proto import counters_pb2 as pb

USERS = 100
RATE = 20
MODES = ("none", "naive", "grpc")


async def send(mode: str, method, request, user_id: int) -> str:
    attempts = 4 if mode == "naive" else 1
    result = "UNAVAILABLE"
    for _ in range(attempts):
        request.idempotency_key = str(uuid.uuid4())
        result = await status(method(request, metadata=auth(user_id), timeout=WRITE_TIMEOUT))
        if result != "UNAVAILABLE":
            break
        await asyncio.sleep(0.05)
    return result


async def run(mode: str) -> None:
    post_id = random.randint(10**9, 2 * 10**9)
    first_user = random.randint(10**6, 10**9)
    users = range(first_user, first_user + USERS)

    channel, write, read = connect(retries=mode == "grpc")
    async with channel:
        started = await paced(
            (
                write.ViewStarted(pb.ViewStartedRequest(post_id=post_id), metadata=auth(u), timeout=WRITE_TIMEOUT)
                for u in users
            ),
            RATE,
        )
        await asyncio.sleep(2.1)
        views = await paced(
            (
                send(mode, write.ViewFinished, pb.ViewFinishedRequest(post_id=post_id, view_token=s.view_token), u)
                for u, s in zip(users, started)
            ),
            RATE,
        )
        likes = await paced((send(mode, write.Like, pb.LikeRequest(post_id=post_id), u) for u in users), RATE)

        await asyncio.sleep(2.5)
        counters = await read.GetCounters(
            pb.GetCountersRequest(post_id=post_id), metadata=auth(first_user), timeout=READ_TIMEOUT
        )

    print(f"mode={mode}")
    print(f"  view_finished: {dict(Counter(views))}")
    print(f"  like:          {dict(Counter(likes))}")
    print(f"  counters: views={counters.views} likes={counters.likes} (expected {USERS})")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        sys.exit(f"usage: chaos.py {'|'.join(MODES)}")
    asyncio.run(run(sys.argv[1]))
