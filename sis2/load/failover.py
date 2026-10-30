import argparse
import asyncio
import random
import subprocess
import time
import uuid
from collections import Counter

import grpc
from client import READ_TIMEOUT, WRITE_TIMEOUT, auth, channel, stubs
from shared.proto import counters_pb2 as pb

RATE = 30
POSTS = 12


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], capture_output=True, check=True)


async def run(target: str, users: int, kill_at: float, settle: float) -> None:
    posts = [random.randint(10**10, 2 * 10**10) for _ in range(POSTS)]
    base = random.randint(10**6, 10**9)
    likes: Counter[int] = Counter()
    sent: Counter[int] = Counter()
    writes: Counter[str] = Counter()
    reads: Counter[str] = Counter()
    errors_at: list[float] = []

    async with channel("localhost:8081") as chan:
        write, read = stubs(chan)

        async def like(user_id: int, post_id: int, started: float) -> None:
            request = pb.LikeRequest(post_id=post_id, idempotency_key=str(uuid.uuid4()))
            sent[post_id] += 1
            try:
                await write.Like(request, metadata=auth(user_id), timeout=WRITE_TIMEOUT)
                likes[post_id] += 1
                writes["OK"] += 1
            except grpc.aio.AioRpcError as exc:
                writes[exc.code().name] += 1
                errors_at.append(time.monotonic() - started)

        async def get(post_id: int, started: float) -> None:
            request = pb.GetCountersRequest(post_id=post_id)
            try:
                await read.GetCounters(request, metadata=auth(base), timeout=READ_TIMEOUT)
                reads["OK"] += 1
            except grpc.aio.AioRpcError as exc:
                reads[exc.code().name] += 1
                errors_at.append(time.monotonic() - started)

        started = time.monotonic()
        killed = False
        tasks = []
        for i in range(users):
            if not killed and time.monotonic() - started >= kill_at:
                await asyncio.to_thread(compose, "kill", target)
                print(f"killed {target} at {time.monotonic() - started:.1f}s")
                killed = True
            tasks.append(asyncio.ensure_future(like(base + i, posts[i % POSTS], started)))
            if i % 3 == 0:
                tasks.append(asyncio.ensure_future(get(random.choice(posts), started)))
            await asyncio.sleep(1 / RATE)
        await asyncio.gather(*tasks)

        await asyncio.sleep(settle)
        result = await read.BatchGetCounters(pb.BatchGetCountersRequest(post_ids=posts), metadata=auth(base), timeout=2)

    await asyncio.to_thread(compose, "start", target)
    counted = {item.post_id: item.likes for item in result.counters}
    wrong = [post_id for post_id in posts if not likes[post_id] <= counted[post_id] <= sent[post_id]]

    print(f"like:  {dict(writes)}")
    print(f"read:  {dict(reads)}")
    if errors_at:
        print(f"errors between {min(errors_at):.1f}s and {max(errors_at):.1f}s")
    print(f"likes counted {sum(counted.values())}, sent {sum(sent.values())}, confirmed {writes['OK']}")
    print(f"lost or duplicated: {'none' if not wrong else wrong}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="compose service to kill, e.g. kafka-2 or redis-0")
    parser.add_argument("--users", type=int, default=300)
    parser.add_argument("--kill-at", type=float, default=3.0)
    parser.add_argument("--settle", type=float, default=8.0)
    args = parser.parse_args()
    asyncio.run(run(args.target, args.users, args.kill_at, args.settle))


if __name__ == "__main__":
    main()
