import json
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
DURATION_METRIC = {"rest": "http_req_duration", "grpc": "grpc_req_duration"}


def row(protocol: str, scenario: str) -> str:
    summary = json.loads((RESULTS / f"{protocol}-{scenario}.json").read_text())["metrics"]
    latency = summary[DURATION_METRIC[protocol]]
    iterations = summary["iterations"]["count"]
    checks = summary["checks"]
    errors = checks["fails"] / (checks["passes"] + checks["fails"])
    sent = summary["data_sent"]["count"] / iterations
    received = summary["data_received"]["count"] / iterations
    return (
        f"| {scenario} | {protocol} | {summary['iterations']['rate']:.0f} "
        f"| {latency['med']:.2f} | {latency['p(95)']:.2f} | {latency['p(99)']:.2f} | {latency['max']:.1f} "
        f"| {sent:.0f} | {received:.0f} | {errors:.2%} |"
    )


def main() -> None:
    print(
        "| Scenario | Protocol | RPS | p50, ms | p95, ms | p99, ms | max, ms | sent B/req | received B/req | errors |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for scenario in ("single", "batch", "like"):
        for protocol in ("rest", "grpc"):
            if (RESULTS / f"{protocol}-{scenario}.json").exists():
                print(row(protocol, scenario))


if __name__ == "__main__":
    main()
