# Research: Prometheus vCPU Collector

Date: 2026-11-20
Sources: total_workers_vcpu.py, prometheus HTTP API docs, reqwest docs, mock-prometheus-server/main.go

## PromQL

- Instant: `max_over_time(sum(machine_cpu_cores)[59m59s999ms:5m] @ <base_timestamp>)`
  - Note: extra `)` in Python string: `"... @ {base_timestamp})"` — verify if intentional or bug. Keep for parity.
- Range: `sum(machine_cpu_cores)` with `start`, `end`, `step=5m`

## API

- `GET /api/v1/query?query=<promql>&time=<ts>` -> `{"status":"success","data":{"result":[{"value":[ts,"24"]}]}}`
- `GET /api/v1/query_range?query=<q>&start=<ts>&end=<ts>&step=5m` -> `{"status":"success","data":{"result":[{"values":[[ts,"16"],...]}]}}`
- Auth: `Authorization: Bearer <token>` from `/var/run/secrets/kubernetes.io/serviceaccount/token`
- TLS: CA at `/var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt` or `METRICS_UTILITY_PROMETHEUS_CA_CERT_PATH`

## Traps

- `get_current_value` returns None on empty result (cluster just started) -> Python raises MetricsException, not empty value.
- `int(total_vcpu_val)` truncates — 24.9 becomes 24.
- Timeline values are `float(cpu_val)` from Prometheus string values.
- Mock server in `tools/mock-prometheus-server` can be used for integration tests.
