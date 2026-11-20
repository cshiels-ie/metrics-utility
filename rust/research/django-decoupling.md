# Research: Django Decoupling for Billing CLI

Date: 2026-11-20
Sources: Django docs, sqlx docs.rs, Controller container source, metrics-utility base/Collector

## What Django is used for in the billing path

| Usage | Python API | Rust replacement |
|-------|-----------|-----------------|
| DB connection | `django.db.connection` (psycopg wrapper) | `sqlx::PgPool` via `DATABASE_URL` |
| Advisory lock | `pg_try_advisory_lock(hashtext(key)::bigint)` | Same SQL via sqlx |
| Last-gathered entries | `conf_setting` table `AUTOMATION_ANALYTICS_LAST_ENTRIES` (JSON string containing JSON) | `SELECT value FROM conf_setting WHERE key='...'` + double JSON parse |
| SYSTEM_UUID | `django.conf.settings.SYSTEM_UUID` | Env `SYSTEM_UUID` or query `conf_setting` |
| Time utils | `django.utils.timezone.now()` | `chrono::Utc::now()` |
| Settings | `django.conf.settings` | Env vars / Controller config file |

## Traps

- `conf_setting.value` is JSON-encoded JSON: `json.loads(json.loads(row[0]))` with `_datetime_hook` that parses ISO timestamps. Must replicate double-parse + datetime conversion.
- Advisory lock key is hashed via `hashtext(key)::bigint` then `pos % 2^63` to stay in signed bigint range. Must replicate exactly or lock won't interop with Python.
- `last_gathered_entry` fallback: if no entry, use `horizon = until - 28d`. Must match.
- Controller may expose DB via `/etc/tower/conf.d/postgres.py` or env vars; need to check controller-container runtime.
