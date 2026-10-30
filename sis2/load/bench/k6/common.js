import crypto from "k6/crypto";
import encoding from "k6/encoding";

export const SCENARIO = __ENV.SCENARIO || "single";
export const POSTS = Number(__ENV.POSTS || 10000);
export const BATCH = Number(__ENV.BATCH || 100);

export const options = {
  scenarios: {
    load: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 300),
      timeUnit: "1s",
      duration: __ENV.DURATION || "30s",
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  summaryTrendStats: ["avg", "med", "p(95)", "p(99)", "max"],
};

function b64url(value) {
  return encoding.b64encode(value, "rawurl");
}

export function bearer(userId) {
  const secret = __ENV.JWT_SECRET || "change-me-jwt";
  const body = `${b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }))}.${b64url(JSON.stringify({ sub: String(userId) }))}`;
  return `Bearer ${body}.${crypto.hmac("sha256", secret, body, "base64rawurl")}`;
}

export function randomPost() {
  return 1 + Math.floor(Math.random() * POSTS);
}

export function randomPosts(count) {
  const ids = new Set();
  while (ids.size < count) ids.add(randomPost());
  return [...ids];
}
