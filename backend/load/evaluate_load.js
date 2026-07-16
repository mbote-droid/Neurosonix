// k6 load test for the agentic evaluation endpoint.
//
// Drives 50 concurrent virtual users against POST /api/evaluate/ and checks
// that every response is a well-formed five-dimension evaluation.
//
// Run (requires the backend running and k6 installed — https://k6.io):
//   k6 run backend/load/evaluate_load.js
//   k6 run --env BASE_URL=http://localhost:8010 backend/load/evaluate_load.js
//
// Notes:
// - In offline mode (no ANTHROPIC_API_KEY) scoring is deterministic and fast,
//   which isolates framework/serialization overhead from LLM latency.
// - With a live LLM, latency reflects the provider; lower the VUs or raise the
//   duration-based thresholds accordingly.

import http from 'k6/http'
import { check } from 'k6'

const BASE = __ENV.BASE_URL || 'http://localhost:8000'

export const options = {
  scenarios: {
    fifty_concurrent_evaluations: {
      executor: 'constant-vus',
      vus: 50,
      duration: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'], // <1% errors
    http_req_duration: ['p(95)<2000'], // 95th percentile under 2s (offline)
  },
}

const payload = JSON.stringify({
  scenario_id: 'fin_card_dispute',
  transcript: 'I want to dispute a charge I do not recognize on my account.',
})

const params = { headers: { 'Content-Type': 'application/json' } }

export default function () {
  const res = http.post(`${BASE}/api/evaluate/`, payload, params)
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has five agent scores': (r) => {
      try {
        return JSON.parse(r.body).agent_scores.length === 5
      } catch (_e) {
        return false
      }
    },
  })
}
