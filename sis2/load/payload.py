import json
import random
import time

import jwt
from shared.proto import counters_pb2 as pb

random.seed(7)


def post() -> dict:
    return {
        "post_id": random.randint(1, 50_000_000),
        "likes": random.randint(0, 2_000),
        "views": random.randint(0, 200_000),
        "liked_by_me": random.random() < 0.3,
    }


def as_json(value) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


one = post()
feed = [post() for _ in range(100)]
ids = [item["post_id"] for item in feed]
claims = {"pid": one["post_id"], "uid": 7, "t": time.time_ns() // 1_000_000, "exp": int(time.time()) + 3600}
view_token = jwt.encode(claims, "0" * 32, algorithm="HS256")

cases = [
    ("GetCounters response", pb.PostCounters(**one), as_json(one)),
    (
        "BatchGetCounters request (100 ids)",
        pb.BatchGetCountersRequest(post_ids=ids),
        f"post_ids={','.join(map(str, ids))}".encode(),
    ),
    (
        "BatchGetCounters response (100)",
        pb.BatchGetCountersReply(counters=[pb.PostCounters(**p) for p in feed]),
        as_json({"counters": feed}),
    ),
    (
        "ViewFinished request",
        pb.ViewFinishedRequest(post_id=one["post_id"], view_token=view_token),
        as_json({"view_token": view_token}),
    ),
]

print("| Message | protobuf, B | JSON, B | JSON / protobuf |")
print("|---|---|---|---|")
for name, message, rest in cases:
    proto = len(message.SerializeToString())
    print(f"| {name} | {proto} | {len(rest)} | {len(rest) / proto:.1f}x |")
