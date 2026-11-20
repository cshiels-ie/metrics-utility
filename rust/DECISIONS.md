# Decisions — Rust Controller Billing CLI

This port converts the `metrics-utility` billing pipeline (Controller-installed CLI that gathers billing data and ships to console.redhat.com) into a standalone Rust service, focused on the Controller base image use case.

## ADR-001: Scope — Controller billing CLI only (v1)
Status: accepted (2026-11-20)
Context: metrics-utility has many collectors (dashboard, service, CCSP, reports, anonymized rollups). The Controller image only runs `gather_automation_controller_billing_data` with billing collectors + optional `total_workers_vcpu` Prometheus measurement.
Decision: v1 ports only the billing CLI path:
- `gather_automation_controller_billing_data` command (including `--since/--until/--ship/--dry-run/--verbose`, ship targets `crc`/`directory`/`s3`)
- All `automation_controller_billing` collectors (config, job_host_summary, main_host, etc.)
- `total_workers_vcpu` Prometheus collector (optional, metering_enabled)
- Packaging to CRC (ingress upload with SA OAuth + mTLS cert auth), directory, S3
- Advisory locking and last-gathered-entry tracking
Consequences: Report generation (`build_report`), CCSP dedup/report, candlepin standalone, dashboard/service perf tools stay Python in v1. Tagged out-of-scope.

## ADR-002: Shape — CLI binary, not library
Status: accepted (2026-11-20)
Context: The app is entered via `metrics-utility` management command (Django manage.py wrapper). In the Controller image it runs as `/usr/bin/metrics-utility gather_automation_controller_billing_data ...` on a schedule.
Decision: Rust shape is a CLI binary `metrics-utility` with subcommand `gather_automation_controller_billing_data`. Clap-based front door. Single binary replaces Python wrapper.
Consequences: No Python import compatibility needed. DB connection via DATABASE_URL / Controller DB config, not Django ORM.

## ADR-003: Django decoupling — direct Postgres via sqlx
Status: accepted (2026-11-20)
Context: `metrics_utility/base`, `automation_controller_billing/*`, `library/collectors/controller`, `management/commands` are all blocked on `django` (no Rust equivalent). ORM is used for: advisory locks (pg_advisory_lock), last-gathered settings, and collector SQL queries.
Decision: Rework in Rust: use `sqlx` with direct Postgres SQL, preserving the same queries (from collector SQL files) and advisory lock semantics. Controller DB URL from env/Controller config. No Django runtime in Rust path.
Consequences: Must vendor or replicate collector SQL. Django settings (SYSTEM_UUID, etc.) become env/file config. Migration of any Django-specific logic must be verified against actual Controller DB schema.

## ADR-004: Prometheus client — reqwest + bearer + CA
Status: accepted (2026-11-20)
Context: `total_workers_vcpu` queries `https://prometheus-k8s.openshift-monitoring.svc.cluster.local:9091/api/v1/query` and `/query_range` with SA token + service CA.
Decision: Use `reqwest` with rustls, Bearer auth, custom CA bundle. PromQL is fixed strings (`max_over_time(...)`, `sum(machine_cpu_cores)`).
Consequences: Must handle in-cluster SA token file at `/var/run/secrets/kubernetes.io/serviceaccount/token` and service-ca.crt.

## ADR-005: Archive format compatibility
Status: accepted (2026-11-20)
Context: Each gather produces a `.tar.gz` with per-collector CSV/JSON files, `config.json` (with billing_provider_params sans sensitive keys), and manifest. Name: `{SYSTEM_UUID}-{timestamp}.tar.gz`. CRC upload uses specific content-type.
Decision: Byte-for-byte archive structure is not required, but file names, CSV headers/ordering, JSON keys, and upload content-type must match so billing pipeline accepts it. Normalize timestamps to same format.
Consequences: Archive creation can use different tar ordering if content matches; tests compare unpacked content.

## ADR-006: Equivalence bar — unpacked payload equality
Status: accepted (2026-11-20)
Context: Timestamps, SYSTEM_UUID, and DB state make byte-identical comparisons impossible.
Decision: Two runs are equivalent if for same DB snapshot + env + fixed clock: (a) same set of archive members, (b) same CSV/JSON content (row order and values), (c) same upload HTTP request (URL, headers, content-type, archive content), (d) same exit code and log level. Timestamps in output become wildcards in app-cases.
Consequences: Need deterministic test harness with fixture DB and mocked Prometheus/ingress.

## ADR-007: Shipping targets — keep all three
Status: accepted (2026-11-20)
Context: Ship targets are `crc` (production), `directory`, `s3` (testing/debugging). CRC has two auth modes (SA OAuth, mTLS cert).
Decision: Port all three. CRC is primary; others are needed for testing without real ingress.
Consequences: S3 uses `aws-sdk-s3` (or `rust-s3`), directory is local FS.

## ADR-008: Async runtime — tokio
Status: accepted (2026-11-20)
Context: Need async HTTP (reqwest), async DB (sqlx), and potentially concurrent collector gathering.
Decision: `tokio` runtime. Collectors that were sequential can stay sequential initially; parallelize later if beneficial.
Consequences: All IO is async. Sync CSV writing stays sync.

## ADR-009: Checkpoints
Status: accepted (2026-11-20)
Context: Whole-app port is long-running.
Decision: Stop for review after: (1) front door replay passes, (2) each wave completes, (3) lift readiness. MAP.md tracks claims.
Consequences: Each wave merged separately.

## ADR-010: Cutover — side-by-side in Controller image
Status: accepted (2026-11-20)
Context: Controller image installs metrics-utility as Python package and creates `/usr/bin/metrics-utility` shim.
Decision: New image installs Rust binary alongside Python shim initially. E2E test runs both against same DB/inputs and diffs payloads. Only one writer owns advisory lock / checkpoint. Feature-flag or env var selects Rust implementation. Full cutover after parity proven.
Consequences: Need to keep Python fallback until lift.

## ADR-011: Targets — RHEL 9 / UBI, static-ish binary
Status: accepted (2026-11-20)
Context: Controller container is RHEL-based (UBI). Must run as same user, with same mounts/certs.
Decision: Target `x86_64-unknown-linux-gnu` with glibc compatible with UBI 9. MSRV 1.78+. Binary size secondary to correctness. No static musl unless required.
Consequences: Build in container matching controller base.
