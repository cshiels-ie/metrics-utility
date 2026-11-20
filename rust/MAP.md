# MAP — Rust Controller Billing CLI port

Goal: Replace the Python `metrics-utility` billing pipeline in the Controller base image with a standalone Rust binary `metrics-utility gather_automation_controller_billing_data` that produces identical billing payloads and ships to console.redhat.com.

Index:
- Decisions: `rust/DECISIONS.md` (ADR-001..011)
- Glossary: `rust/GLOSSARY.md`
- Research: `rust/research/*.md`
- App cases: `rust/app-cases/`
- Handoff: `rust/HANDOFF.md`

## Units (from `rust-anything analyze --whole-app`, waves 0-8)

Wave 0 (leaves, ready):
- `metrics_utility/schemas/` — empty schemas — open
- `mock_awx/*` — test mocks — out-of-scope (keep Python)
- `tools/*` — perf/test tools — out-of-scope

Wave 1:
- `metrics_utility/automation_controller_billing/base/` — billing base helpers — open
- `metrics_utility/candlepin/` — cert handling — open
- `metrics_utility/library/storage/` — S3/directory storage — open
- `metrics_utility/automation_controller_billing/dedup/` — CCSP dedup — out-of-scope v1

Wave 2 (core collectors, highest priority):
- `metrics_utility/library/collectors/others/` — **total_workers_vcpu** (Prometheus) — claimed by feat/rust-controller-billing-cli 2026-11-20 — START HERE
- `metrics_utility/library/collectors/` — util, output adapters — open
- `metrics_utility/library/` — lock, helpers — open
- `metrics_utility/library/collectors/dashboard/` + `service/` + `controller/` — tangled collectors — open (controller blocked on django)
- `metrics_utility/automation_controller_billing/report_saver/` — open

Wave 3:
- `metrics_utility/automation_controller_billing/extract/` — DB extract — open (blocked django)
- `metrics_utility/base/` — base Collector/Collection — open (blocked django)

Wave 4:
- `metrics_utility/automation_controller_billing/package/` — CRC/S3/directory packaging — open
- `metrics_utility/management/` — validation, CLI — open

Wave 5:
- `metrics_utility/automation_controller_billing/` — billing Collector + helpers — open

Wave 6:
- `metrics_utility/automation_controller_billing/dataframe_engine/` — report dataframes — out-of-scope v1
- `tools/perf/` — out-of-scope

Wave 7:
- `metrics_utility/automation_controller_billing/report/` + renderers + `anonymized_rollups` — out-of-scope v1

Wave 8:
- `metrics_utility/management/commands/` — `gather_automation_controller_billing_data.py` CLI — open (port after dependencies)

## Current state
- Branch: `feat/rust-controller-billing-cli` from `origin/devel@84b3900`
- Front door: not yet scaffolded — next step
- Fallback rate: N/A (no app crate yet)
- Wave in progress: wave 2, unit `library/collectors/others/` (total_workers_vcpu)

## What is out of scope in v1
- `build_report`, CCSP v1/v2, renewal_guidance reports
- `anonymized_rollups`, dashboard collection, service collection
- Candlepin standalone manage, perf/benchmark tools

## Open questions
- Q1: How does Controller expose DB URL to the Rust binary? (env var vs config file) — check controller-container
- Q2: Confirm SQL for billing collectors (are they in repo sql/ dir or inline?) — need to locate
- Q3: Mock Prometheus/ingress strategy for app-record — reuse tools/mock-prometheus-server?

## Progress 2026-11-20
- Workspace created, vcpu+config crates done, app front door builds, all tests pass
- Next claim: `metrics_utility/library/storage` or `metrics_utility/candlepin` (wave 1)
