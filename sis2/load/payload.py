import gzip
import json
import random
import time

import jwt
from shared.proto import counters_pb2 as pb

random.seed(7)
POSTS = 50_000_000


def counters(count: int) -> list[dict]:
    return [
        {
            "post_id": random.randint(1, POSTS),
            "likes": random.randint(0, 2_000),
            "views": random.randint(0, 200_000),
            "liked_by_me": random.random() < 0.3,
        }
        for _ in range(count)
    ]


def as_json(value) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


def cases():
    one = counters(1)[0]
    many = counters(100)
    ids = [item["post_id"] for item in many]
    yield "GetCounters response", pb.PostCounters(**one).SerializeToString(), as_json(one)
    yield (
        "BatchGetCounters request (100 ids; REST — query string)",
        pb.BatchGetCountersRequest(post_ids=ids).SerializeToString(),
        ("post_ids=" + ",".join(map(str, ids))).encode(),
    )
    yield (
        "BatchGetCounters response (100)",
        pb.BatchGetCountersReply(counters=[pb.PostCounters(**item) for item in many]).SerializeToString(),
        as_json({"counters": many}),
    )
    claims = {"pid": one["post_id"], "uid": 7, "t": time.time_ns() // 1_000_000, "exp": int(time.time()) + 3600}
    view = {"view_token": jwt.encode(claims, "0" * 32, algorithm="HS256")}
    yield (
        "ViewFinished request",
        pb.ViewFinishedRequest(post_id=one["post_id"], **view).SerializeToString(),
        as_json(view),
    )


def main() -> None:
    print("| Message | protobuf, B | JSON, B | JSON / protobuf | protobuf gzip, B | JSON gzip, B |")
    print("|---|---|---|---|---|---|")
    for name, proto, rest in cases():
        print(
            f"| {name} | {len(proto)} | {len(rest)} | {len(rest) / len(proto):.1f}x"
            f" | {len(gzip.compress(proto))} | {len(gzip.compress(rest))} |"
        )


if __name__ == "__main__":
    main()
