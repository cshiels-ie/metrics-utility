# Research: CRC Shipping (console.redhat.com)

Date: 2026-11-20
Sources: package_crc.py, base/package.py, ingress docs

## Upload

- URL: `METRICS_UTILITY_CRC_INGRESS_URL` default `https://console.redhat.com/api/ingress/v1/upload`
- SSO: `METRICS_UTILITY_CRC_SSO_URL` default `https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token`
- Content-Type: `application/vnd.redhat.aap-billing-controller.aap_billing_controller_payload+tgz`
- Auth modes:
  1. Service account: `client_credentials` grant to SSO, Bearer token to ingress
  2. mTLS: client cert from `candlepin_cert_pem`/`candlepin_key_pem` in billing_provider_params, temp files, CA bundle at `/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem`
  - Cert ingress URL is `cert.` subdomain of ingress URL (e.g. `cert.console.redhat.com`)
  - Fallback: mTLS SSLError -> retry with service account if creds present
- Proxy: `METRICS_UTILITY_PROXY_URL` if set
- Tarball name: `{SYSTEM_UUID}-{timestamp:%Y-%m-%d-%H%M%S%z}.tar.gz` with `-{index}-{key}` suffix

## Archive contents (from Package.make_tgz)

- Each collection's CSV/JSON files
- `config.json` (with billing_provider_params sans candlepin cert/key)
- `manifest.json` + `data_collection_status.json`
- Members added via `tarfile` — need to ensure same paths Rust-side

## Traps

- Sensitive keys `candlepin_cert_pem`, `candlepin_key_pem` must NOT be in `config.json` in archive.
- Payload is multipart `file` field with specific content-type.
