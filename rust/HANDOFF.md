# Handoff — feat/rust-controller-billing-cli

Date: 2026-11-20
Branch: `feat/rust-controller-billing-cli` from `origin/devel@84b3900`
Fallback rate: 100% (front door proxies to Python; only pure helpers ported)
Next: wire DB collectors + package, then lift.

## What is done

- Workspace `rust/Cargo.toml` with `app` binary + `crates/vcpu` + `crates/config`
- `vcpu` crate: pure functions `get_hour_boundaries`, `timestamp_format`, `promql_query` + `PrometheusClient` (reqwest+rTLS) + `gather()` — all tests pass, parity verified against Python
- `config` crate: `get_max_gather_period_days`, `bool_from_env`, `get_optional_collectors`, `ShipTarget`, `GatherWindow::calculate` (mirrors Collector._calculate_collection_interval)
- `app` binary: clap front door for `gather-automation-controller-billing-data` with `--since/--until/--ship/--dry-run/--verbose`, vCPU fast-path when metering enabled, else fallback to Python
- Research docs: `rust/research/{prometheus,django-decoupling,crc-shipping}.md`
- Decisions: `rust/DECISIONS.md` (ADR-001..011), Glossary, MAP

## How to verify

```sh
cargo test --manifest-path rust/Cargo.toml
cargo build --manifest-path rust/Cargo.toml
./rust/target/debug/metrics-utility --help
./rust/target/debug/metrics-utility gather-automation-controller-billing-data --help
```

For integration: set `METRICS_UTILITY_OPTIONAL_COLLECTORS=total_workers_vcpu` + `METRICS_UTILITY_USAGE_BASED_METERING_ENABLED=true` + mock Prometheus, then run gather — vCPU path executes in Rust, rest proxies.

## What is next (wave order)

1. **Wave 1**: `storage` + `candlepin` crates (S3/directory, cert handling)
2. **Wave 2**: `library/*` collectors that are not DB-bound (finish vCPU wiring, extract shared helpers)
3. **Wave 3**: `base/` — Collection/Collector trait + slicing + advisory lock (needs sqlx + Controller DB)
4. **Wave 4**: `package/` — tarball + CRC shipping (reqwest multipart, mTLS)
5. **Wave 5-8**: billing Collector + management command (final CLI wiring)

Each unit: `bridge`/`record`/`diff`/`bench`/`gate` per rust-anything SKILL.md, then `app wire` + `app replay`.

## Open questions (see MAP.md)

- Controller DB URL exposure for Rust binary (env vs config file) — check `automation-controller-container` runtime
- SQL location for billing collectors (inline vs `sql/` dir) — appears to be via `library/collectors/controller/*` with `DataframeOutput.sql`
- Mock strategy for `app record` — need Controller DB fixture + mock Prometheus + mock ingress

## Files to read next session

- `rust/MAP.md`, `rust/DECISIONS.md`, `rust/HANDOFF.md`
- `rust/research/*.md` before porting those units
- `metrics_utility/automation_controller_billing/collector.py` + `base/collector.py` for orchestrator
