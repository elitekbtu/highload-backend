import exec from "k6/execution";
import http from "k6/http";
import { check } from "k6";

import { BATCH, SCENARIO, bearer, randomPost, randomPosts } from "./common.js";

export { options } from "./common.js";

const WRITE = __ENV.WRITE_HTTP || "http://write_service:8000";
const READ = __ENV.READ_HTTP || "http://read_service:8000";

const calls = {
  single: () => http.get(`${READ}/api/v1/posts/${randomPost()}/counters`, params()),
  batch: () => http.get(`${READ}/api/v1/counters?post_ids=${randomPosts(BATCH).join(",")}`, params()),
  like: () => http.put(`${WRITE}/api/v1/posts/${randomPost()}/like`, null, params()),
};

function params() {
  return { headers: { Authorization: bearer(exec.vu.idInTest) }, timeout: "2s" };
}

export default function () {
  const response = calls[SCENARIO]();
  check(response, { ok: (r) => r.status === 200 || r.status === 202 });
}
