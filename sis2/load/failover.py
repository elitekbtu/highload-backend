import asyncio
import random
import subprocess
import sys
import uuid
from collections import Counter

from client import READ_TIMEOUT, WRITE_TIMEOUT, auth, connect, paced, status
from shared.proto import counters_pb2 as pb

USERS = 300
POSTS = 12
RATE = 40
KILL_AT = 3.0
SETTLE = 8.0


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], capture_output=True, check=True)


async def run(target: str) -> None:
    posts = [random.randint(10**10, 2 * 10**10) for _ in range(POSTS)]
    first_user = random.randint(10**6, 10**9)
    sent, confirmed, results = Counter(), Counter(), Counter()

    channel, write, read = connect()
    async with channel:

        async def like(user_id: int, post_id: int) -> None:
            sent[post_id] += 1
            request = pb.LikeRequest(post_id=post_id, idempotency_key=str(uuid.uuid4()))
            result = await status(write.Like(request, metadata=auth(user_id), timeout=WRITE_TIMEOUT))
            results[f"like {result}"] += 1
            if result == "OK":
                confirmed[post_id] += 1

        async def get(post_id: int) -> None:
            request = pb.GetCountersRequest(post_id=post_id)
            result = await status(read.GetCounters(request, metadata=auth(first_user), timeout=READ_TIMEOUT))
            results[f"read {result}"] += 1

        def calls():
            for i in range(USERS):
                yield like(first_user + i, posts[i % POSTS])
                if i % 3 == 0:
                    yield get(random.choice(posts))

        async def kill() -> None:
            await asyncio.sleep(KILL_AT)
            await asyncio.to_thread(compose, "kill", target)
            print(f"killed {target} at {KILL_AT:.0f}s")

        await asyncio.gather(kill(), paced(calls(), RATE))
        await asyncio.sleep(SETTLE)
        reply = await read.BatchGetCounters(
            pb.BatchGetCountersRequest(post_ids=posts), metadata=auth(first_user), timeout=2
        )

    await asyncio.to_thread(compose, "start", target)
    counted = {item.post_id: item.likes for item in reply.counters}
    correct = all(confirmed[p] <= counted[p] <= sent[p] for p in posts)

    print(f"calls: {dict(sorted(results.items()))}")
    print(f"likes counted {sum(counted.values())}, sent {sum(sent.values())}, confirmed {sum(confirmed.values())}")
    print(f"lost or duplicated: {'none' if correct else 'YES'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: failover.py <compose service>, e.g. kafka-2 or redis-0")
    asyncio.run(run(sys.argv[1]))
