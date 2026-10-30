import exec from "k6/execution";
import grpc from "k6/net/grpc";
import { check } from "k6";

import { BATCH, SCENARIO, bearer, randomPost, randomPosts } from "./common.js";

export { options } from "./common.js";

const WRITE = __ENV.WRITE_GRPC || "write_service:50051";
const READ = __ENV.READ_GRPC || "read_service:50051";

const client = new grpc.Client();
client.load(["/proto"], "counters.proto");

const calls = {
  single: [READ, "counters.v1.CounterReadService/GetCounters", () => ({ post_id: randomPost() })],
  batch: [READ, "counters.v1.CounterReadService/BatchGetCounters", () => ({ post_ids: randomPosts(BATCH) })],
  like: [WRITE, "counters.v1.CounterWriteService/Like", () => ({ post_id: randomPost() })],
};

export default function () {
  const [target, method, request] = calls[SCENARIO];
  if (exec.vu.iterationInScenario === 0) {
    client.connect(target, { plaintext: true });
  }
  const response = client.invoke(method, request(), {
    metadata: { authorization: bearer(exec.vu.idInTest) },
    timeout: "2s",
  });
  check(response, { ok: (r) => r && r.status === grpc.StatusOK });
}
