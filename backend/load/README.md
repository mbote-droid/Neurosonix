# Load testing

Load test for the agentic evaluation API using [k6](https://k6.io).

## What it does

`evaluate_load.js` runs **50 concurrent virtual users** against
`POST /api/evaluate/` for 30 seconds and asserts that every response is a
well-formed five-dimension evaluation. Thresholds:

- `http_req_failed rate < 1%`
- `http_req_duration p(95) < 2000 ms` (offline mode)

## Running it

1. Start the backend:

   ```bash
   cd backend
   ./venv/Scripts/python -m uvicorn main:app --port 8000
   ```

2. Install k6 (see https://k6.io/docs/get-started/installation/), then:

   ```bash
   k6 run backend/load/evaluate_load.js
   # or against a non-default host:
   k6 run --env BASE_URL=http://localhost:8010 backend/load/evaluate_load.js
   ```

## Interpreting results

- **Offline mode** (no `ANTHROPIC_API_KEY`): scoring is deterministic and
  in-process, so the numbers reflect FastAPI/serialization/persistence overhead
  under concurrency — a clean measure of the platform's own throughput.
- **Live LLM mode**: latency is dominated by the model provider and its rate
  limits. Reduce `vus` or relax the duration threshold before comparing.

Record actual k6 output alongside the environment it was run on; this file does
not include measured numbers because they are hardware- and mode-dependent.
