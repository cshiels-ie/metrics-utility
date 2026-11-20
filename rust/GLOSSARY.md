# Glossary — Python → Rust names

| Python term | Meaning | Rust name |
|---|---|---|
| `Collector` (base + billing) | Orchestrates gathering, slicing, packaging | `collector::Collector` |
| `Collection` / `CollectionCSV` / `CollectionJSON` | Per-metric gather result | `collection::Collection` |
| `gather_since` / `gather_until` / `last_gather` | Time window for incremental gather | `gather::Window { since, until, last_gather }` |
| `billing_provider_params` | Extra config forwarded to package (S3 creds, billing IDs, certs) | `config::BillingProviderParams` |
| `ship_target` (`crc`/`directory`/`s3`) | Where to upload the tarball | `ship::ShipTarget` |
| `Package` / `PackageCRC` / `PackageS3` / `PackageDirectory` | Creates tarball and ships it | `package::Package` trait |
| `total_workers_vcpu` collector | Prometheus query for worker vCPUs in prev hour | `collectors::vcpu` |
| `DictOutput` / `CollectionOutput` | Adapter collectors use to return data | Collector return types (`Option<Dict>` etc.) |
| `advisory lock` (`gather_automation_controller_billing_lock`) | Postgres pg_advisory_lock to prevent concurrent gathers | `lock::advisory_lock` |
| `last_gathered_entry` | Persisted per-collector watermark in Controller settings | `state::LastGathered` |
| `SYSTEM_UUID` | Controller instance identity, used in tarball name | `config::system_uuid` |
| CRC ingress | `console.redhat.com/api/ingress/v1/upload` | `ship::crc` |
| SSO token URL | `sso.redhat.com/.../token` for SA OAuth | `ship::crc::sso` |
| `METRICS_UTILITY_*` env vars | All configuration | `config::Env` |
