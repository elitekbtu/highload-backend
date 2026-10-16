import http from 'k6/http';
import { check } from 'k6';

const rate = Number(__ENV.RATE || 100);
const base = __ENV.BASE_URL || 'http://api:8000';

export const options = {
  scenarios: {
    increments: {
      executor: 'constant-arrival-rate',
      rate,
      timeUnit: '1s',
      duration: __ENV.DURATION || '30s',
      preAllocatedVUs: Math.max(50, Math.ceil(rate * 0.1)),
      maxVUs: Math.max(100, Math.ceil(rate * 0.5)),
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(99)<150'],
    checks: ['rate>0.99'],
    dropped_iterations: ['count==0'],
  },
};

export function setup() {
  const posts = [];
  for (let index = 0; index < 100; index++) {
    const response = http.post(`${base}/post/`, JSON.stringify({content: `load-${index}`}), {
      headers: {'Content-Type': 'application/json'},
    });
    if (response.status !== 201) throw new Error(`Post creation failed: ${response.status}`);
    posts.push(response.json('id'));
  }
  return {posts, run: String(Date.now())};
}

export default function (data) {
  const group = Math.floor(__ITER / 4);
  const post = group % 2 === 0 ? data.posts[0] : data.posts[(__VU * 104729 + group) % data.posts.length];
  const username = `load-${data.run}-${__VU}-${group}`;
  const path = __ITER % 2 ? '/like' : '/view';
  const response = http.post(`${base}${path}`, JSON.stringify({post_id: post, username}), {
    headers: {'Content-Type': 'application/json'},
    tags: {name: path},
  });
  check(response, {'Kafka acknowledged event': (result) => result.status === 202});
}
