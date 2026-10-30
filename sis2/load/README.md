# load

Scripts for measurements and checks. Run them from `sis2/` when the stack is up. Before the Python scripts, load the secrets:

```bash
set -a; source .env; set +a
```

| What | Question | Run |
|---|---|---|
| [payload.py](payload.py) | How much smaller is protobuf than JSON? No stack needed | `uv run python load/payload.py` |
| [bench/](bench) | Latency and traffic of REST and gRPC at the same RPS | `./load/bench/run.sh` |
| [chaos.py](chaos.py) | Are retries safe when a Kafka ack is lost? | `uv run python load/chaos.py none\|naive\|grpc` |
| [failover.py](failover.py) | Does the system live when a node dies under load? | `uv run python load/failover.py kafka-2` |

[client.py](client.py) is the shared gRPC client for the scripts: JWT in metadata, deadlines, `retryPolicy` and `retryThrottling`.

## bench

- `k6/common.js`: load with a fixed RPS, JWT signing, random posts 1..10000.
- `k6/rest.js`, `k6/grpc.js`: the cases `single` (one post), `batch` (100 posts), `like`. k6 calls the services directly inside the Docker network, not through the gateway.
- `run.sh`: 3 cases × 2 protocols, 30 s each.
- `summarize.py`: puts the k6 results into one table.

## chaos

It works with fake lost acks:

```bash
CHAOS_ACK_LOSS_RATE=0.1 docker compose up -d --wait write_service
uv run python load/chaos.py naive    # views > 100: a retry with a new key counts twice
uv run python load/chaos.py grpc     # exactly 100/100
docker compose up -d --wait write_service
```

## failover

It kills a node at second 3 of a stream of likes. Then it checks: counted is not less than confirmed and not more than sent. For Redis, kill the current master. To find it: `docker compose exec sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name counters`.

## results

| Folder | From |
|---|---|
| `payload.md` | `payload.py` |
| `bench/` | `bench/run.sh`: k6 JSON results and `summary.md` |
| `chaos/` | `chaos.py` with 10% and 30% lost acks |
| `failover/` | `failover.py` for Kafka and Redis |
