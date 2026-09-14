import argparse
import time

import httpx

URL = "https://localhost:9443/api/quote/1"
WARMUP, N = 2_000, 20_000


def make_client(*, http2: bool) -> httpx.Client:
    return httpx.Client(
        http2=http2,
        verify=False,
        timeout=httpx.Timeout(0.5, connect=2.0),
    )


def must_match(res: httpx.Response, expected: str) -> None:
    if res.http_version != expected:
        raise RuntimeError(f"expected {expected}, got {res.http_version}")


def percentile(xs: list[int], p: float) -> int:
    return xs[int(len(xs) * p)]


def report(label: str, us: list[int]) -> None:
    us.sort()
    print(
        f"{label} p50={percentile(us, 0.50)} "
        f"p95={percentile(us, 0.95)} "
        f"p99={percentile(us, 0.99)} max={us[-1]} us"
    )


def run_warm(url: str, expected: str, http2: bool) -> None:
    c = make_client(http2=http2)
    for _ in range(WARMUP):
        must_match(c.get(url), expected)
    us = [0] * N
    for i in range(N):
        t0 = time.perf_counter_ns()
        c.get(url)
        us[i] = (time.perf_counter_ns() - t0) // 1_000
    c.close()
    report("warm", us)


def run_cold(url: str, http2: bool) -> None:
    us = [0] * N
    for i in range(N):
        with make_client(http2=http2) as c:
            t0 = time.perf_counter_ns()
            c.get(url)
            us[i] = (time.perf_counter_ns() - t0) // 1_000
    report("cold", us)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cold", action="store_true")
    parser.add_argument("--url", default=URL)
    parser.add_argument(
        "--http1",
        action="store_true",
        help="force HTTP/1.1 (use with --url https://localhost:9444/api/quote/1)",
    )
    args = parser.parse_args()
    http2 = not args.http1
    expected = "HTTP/1.1" if args.http1 else "HTTP/2"
    if args.cold:
        run_cold(args.url, http2)
    else:
        run_warm(args.url, expected, http2)


if __name__ == "__main__":
    main()
