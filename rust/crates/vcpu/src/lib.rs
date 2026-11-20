//! Port of `metrics_utility/library/collectors/others/total_workers_vcpu.py`
//!
//! Pure functions are direct translations; Prometheus I/O is isolated in
//! `PrometheusClient` so it can be tested against the mock server in
//! `tools/mock-prometheus-server`.

use chrono::{DateTime, TimeZone, Utc};
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum VcpuError {
    #[error("HTTP error {status}: {body}")]
    Http { status: u16, body: String },
    #[error("Prometheus API error: {0}")]
    Api(String),
    #[error("transport error: {0}")]
    Transport(String),
    #[error("missing cluster_name")]
    MissingClusterName,
    #[error("no data available yet, the cluster is probably running for less than an hour")]
    NoData,
}

// ---------------------------------------------------------------------------
// Pure helpers — must match Python exactly
// ---------------------------------------------------------------------------

/// Return the start and end timestamps of the hour preceding `current_timestamp`.
///
/// Python: `current_hour_start = (ts // 3600) * 3600`
///         `prev_start = current_hour_start - 3600`
///         `prev_end   = current_hour_start - 0.001`
pub fn get_hour_boundaries(current_timestamp: f64) -> (f64, f64) {
    let current_hour_start = (current_timestamp / 3600.0).floor() * 3600.0;
    let previous_hour_start = current_hour_start - 3600.0;
    let previous_hour_end = current_hour_start - 0.001;
    (previous_hour_start, previous_hour_end)
}

/// Format a Unix timestamp as ISO-8601 UTC with millisecond precision, e.g.
/// `2024-01-15T14:00:00.000Z`.
///
/// Python: `datetime.fromtimestamp(ts, UTC).isoformat(timespec="milliseconds").replace("+00:00","Z")`
pub fn timestamp_format(ts: f64) -> String {
    // chrono's timestamp_millis handles fractional seconds; we construct via
    // timestamp_opt and format with 3 fractional digits.
    let secs = ts.trunc() as i64;
    let millis = ((ts.fract() * 1000.0).round() as i32).rem_euclid(1000);
    // Handle negative fract edge: trunc+round already correct for positive ts (our domain).
    let dt: DateTime<Utc> = Utc.timestamp_opt(secs, millis as u32 * 1_000_000).unwrap();
    dt.format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string()
}

/// Build the PromQL query for the previous hour's max worker vCPUs.
pub fn promql_query(base_timestamp: f64) -> String {
    // Python formats base_timestamp with default `str(float)` — which for integer-valued
    // floats like 1700000000.0 renders as "1700000000.0". We replicate that.
    // Rust's default Display for f64 may differ (e.g. "1.7e9"), so we format explicitly.
    format!(
        "max_over_time(sum(machine_cpu_cores)[59m59s999ms:5m] @ {})",
        format_float_py(base_timestamp)
    )
}

fn format_float_py(v: f64) -> String {
    // Python's repr for float: if v is integer-valued, it still shows ".0"
    // e.g. 1000.0 -> "1000.0", 1000.5 -> "1000.5", 1e20 -> "1e+20"
    // For our domain (unix timestamps ~1e9, always .0), simple ".1" or default is fine.
    // Use ryu-like formatting: if it contains '.' or 'e', keep as is, else add ".0".
    let s = format!("{v:?}"); // Debug gives shortest round-trip, similar to Python repr for our range
    // Debug for 1000.0 gives "1000.0" already — good.
    // For 1e9 like 1700000000.0, Debug gives "1700000000.0" — matches.
    if s.contains('.') || s.contains('e') || s.contains('E') {
        s
    } else {
        format!("{s}.0")
    }
}

// ---------------------------------------------------------------------------
// Data structures (mirrors Python's `info` dict)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VcpuInfo {
    pub cluster_name: String,
    pub collection_timestamp: String,
    pub start_timestamp: String,
    pub end_timestamp: String,
    pub usage_based_billing_enabled: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub total_workers_vcpu: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub promql_query: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timeline: Option<Vec<TimelinePoint>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TimelinePoint {
    pub timestamp: String,
    pub cpu_sum: f64,
}

// ---------------------------------------------------------------------------
// Prometheus client — mirrors Python's PrometheusClient
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct PrometheusClient {
    base_url: String,
    token: Option<String>,
    ca_cert_path: Option<String>,
    timeout_secs: u64,
}

impl PrometheusClient {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into().trim_end_matches('/').to_string(),
            token: None,
            ca_cert_path: None,
            timeout_secs: 30,
        }
    }

    pub fn with_token(mut self, token: impl Into<String>) -> Self {
        self.token = Some(token.into());
        self
    }

    pub fn with_ca_cert(mut self, path: impl Into<String>) -> Self {
        self.ca_cert_path = Some(path.into());
        self
    }

    pub fn with_timeout(mut self, secs: u64) -> Self {
        self.timeout_secs = secs;
        self
    }

    fn build_client(&self) -> Result<reqwest::Client, VcpuError> {
        let mut builder = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(self.timeout_secs))
            .user_agent("metrics-utility-rs/0.1.0");

        if let Some(ca_path) = &self.ca_cert_path {
            let pem = std::fs::read(ca_path).map_err(|e| VcpuError::Transport(e.to_string()))?;
            let cert = reqwest::Certificate::from_pem(&pem)
                .map_err(|e| VcpuError::Transport(e.to_string()))?;
            builder = builder.add_root_certificate(cert);
        }

        builder
            .build()
            .map_err(|e| VcpuError::Transport(e.to_string()))
    }

    /// Execute instant PromQL query (`/api/v1/query`).
    pub async fn query(
        &self,
        query: &str,
        time_param: Option<f64>,
    ) -> Result<Vec<serde_json::Value>, VcpuError> {
        let client = self.build_client()?;
        let url = format!("{}/api/v1/query", self.base_url);
        let mut req = client.get(&url).query(&[("query", query)]);
        if let Some(t) = time_param {
            req = req.query(&[("time", format_float_py(t))]);
        }
        if let Some(tok) = &self.token {
            req = req.bearer_auth(tok);
        }
        let resp = req.send().await.map_err(|e| VcpuError::Transport(e.to_string()))?;
        let status = resp.status().as_u16();
        let text = resp.text().await.map_err(|e| VcpuError::Transport(e.to_string()))?;
        if status != 200 {
            return Err(VcpuError::Http { status, body: text });
        }
        let data: serde_json::Value =
            serde_json::from_str(&text).map_err(|e| VcpuError::Transport(e.to_string()))?;
        if data.get("status").and_then(|v| v.as_str()) != Some("success") {
            return Err(VcpuError::Api(
                data.get("error")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown error")
                    .to_string(),
            ));
        }
        let result = data
            .get("data")
            .and_then(|d| d.get("result"))
            .cloned()
            .unwrap_or(serde_json::Value::Array(vec![]));
        match result {
            serde_json::Value::Array(arr) => Ok(arr),
            _ => Ok(vec![]),
        }
    }

    /// Execute range query (`/api/v1/query_range`).
    pub async fn query_range(
        &self,
        query: &str,
        start_time: f64,
        end_time: f64,
        step: &str,
    ) -> Result<serde_json::Value, VcpuError> {
        let client = self.build_client()?;
        let url = format!("{}/api/v1/query_range", self.base_url);
        let mut req = client.get(&url).query(&[
            ("query", query.to_string()),
            ("start", format_float_py(start_time)),
            ("end", format_float_py(end_time)),
            ("step", step.to_string()),
        ]);
        if let Some(tok) = &self.token {
            req = req.bearer_auth(tok);
        }
        let resp = req.send().await.map_err(|e| VcpuError::Transport(e.to_string()))?;
        let status = resp.status().as_u16();
        let text = resp.text().await.map_err(|e| VcpuError::Transport(e.to_string()))?;
        if status != 200 {
            return Err(VcpuError::Http { status, body: text });
        }
        let data: serde_json::Value =
            serde_json::from_str(&text).map_err(|e| VcpuError::Transport(e.to_string()))?;
        if data.get("status").and_then(|v| v.as_str()) != Some("success") {
            return Err(VcpuError::Api(
                data.get("error")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Unknown error")
                    .to_string(),
            ));
        }
        Ok(data)
    }

    /// Get current value from instant query (first result's value[1] as f64).
    pub async fn get_current_value(&self, query: &str) -> Result<Option<f64>, VcpuError> {
        let result = self.query(query, None).await?;
        if result.is_empty() {
            return Ok(None);
        }
        let val = result[0]
            .get("value")
            .and_then(|v| v.as_array())
            .and_then(|a| a.get(1))
            .and_then(|v| v.as_str())
            .unwrap_or("");
        Ok(val.parse::<f64>().ok())
    }
}

// ---------------------------------------------------------------------------
// High-level gather — mirrors total_workers_vcpu()
// ---------------------------------------------------------------------------

pub async fn gather(
    cluster_name: &str,
    metering_enabled: bool,
    prometheus_url: Option<&str>,
    ca_cert_path: Option<&str>,
    token: Option<&str>,
    now_timestamp: Option<f64>,
) -> Result<Option<VcpuInfo>, VcpuError> {
    if cluster_name.is_empty() {
        return Err(VcpuError::MissingClusterName);
    }

    let now_ts = now_timestamp.unwrap_or_else(|| {
        Utc::now().timestamp_millis() as f64 / 1000.0
    });
    let (prev_start, prev_end) = get_hour_boundaries(now_ts);

    let mut info = VcpuInfo {
        cluster_name: cluster_name.to_string(),
        collection_timestamp: timestamp_format(now_ts),
        start_timestamp: timestamp_format(prev_start),
        end_timestamp: timestamp_format(prev_end),
        usage_based_billing_enabled: metering_enabled,
        total_workers_vcpu: None,
        promql_query: None,
        timeline: None,
    };

    if !metering_enabled {
        info.total_workers_vcpu = Some(1);
        return Ok(Some(info));
    }

    let url = prometheus_url.unwrap_or("https://prometheus-k8s.openshift-monitoring.svc.cluster.local:9091");
    let mut client = PrometheusClient::new(url);
    if let Some(t) = token {
        client = client.with_token(t);
    }
    if let Some(ca) = ca_cert_path {
        client = client.with_ca_cert(ca);
    }

    let query = promql_query(prev_start);
    let total = client.get_current_value(&query).await?;
    let timeline = get_cpu_timeline(&client, prev_start, prev_end).await?;

    info.promql_query = Some(query);
    info.timeline = Some(timeline);

    match total {
        None => Ok(None),
        Some(v) => {
            info.total_workers_vcpu = Some(v as i64);
            Ok(Some(info))
        }
    }
}

pub async fn get_cpu_timeline(
    prom: &PrometheusClient,
    prev_start: f64,
    prev_end: f64,
) -> Result<Vec<TimelinePoint>, VcpuError> {
    let data = prom.query_range("sum(machine_cpu_cores)", prev_start, prev_end, "5m").await?;
    let mut result = Vec::new();
    if let Some(series) = data
        .get("data")
        .and_then(|d| d.get("result"))
        .and_then(|r| r.as_array())
    {
        for s in series {
            if let Some(values) = s.get("values").and_then(|v| v.as_array()) {
                for pair in values {
                    if let Some(arr) = pair.as_array() {
                        let ts_str = arr.get(0).and_then(|v| v.as_str()).or_else(|| arr.get(0).and_then(|v| v.as_f64().map(|_| ""))).unwrap_or("");
                        // handle numeric timestamp (mock may send number)
                        let ts_f: f64 = if let Some(n) = arr.get(0).and_then(|v| v.as_f64()) {
                            n
                        } else if let Some(s) = arr.get(0).and_then(|v| v.as_str()) {
                            s.parse().unwrap_or(0.0)
                        } else {
                            continue;
                        };
                        let cpu_f: f64 = if let Some(n) = arr.get(1).and_then(|v| v.as_f64()) {
                            n
                        } else if let Some(s) = arr.get(1).and_then(|v| v.as_str()) {
                            s.parse().unwrap_or(0.0)
                        } else {
                            continue;
                        };
                        let _ = ts_str;
                        result.push(TimelinePoint {
                            timestamp: timestamp_format(ts_f),
                            cpu_sum: cpu_f,
                        });
                    }
                }
            }
        }
    }
    result.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
    Ok(result)
}

// ---------------------------------------------------------------------------
// Tests — port of Python cases + edge cases
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hour_boundaries_on_hour() {
        // 2024-01-15 14:00:00 UTC = 1705327200
        let ts = 1705327200.0;
        let (start, end) = get_hour_boundaries(ts);
        assert_eq!(start, 1705323600.0); // 13:00
        assert_eq!(end, 1705327199.999); // 13:59:59.999
    }

    #[test]
    fn hour_boundaries_mid_hour() {
        // 14:30 -> previous hour is 13:00-13:59:59.999
        let ts = 1705329000.0; // 14:30
        let (start, end) = get_hour_boundaries(ts);
        assert_eq!(start, 1705323600.0);
        assert_eq!(end, 1705327199.999);
    }

    #[test]
    fn hour_boundaries_just_after_hour() {
        let ts = 1705327200.5;
        let (start, end) = get_hour_boundaries(ts);
        assert_eq!(start, 1705323600.0);
        assert_eq!(end, 1705327199.999);
    }

    #[test]
    fn timestamp_format_known() {
        // 1705327200 = 2024-01-15T14:00:00.000Z
        assert_eq!(timestamp_format(1705327200.0), "2024-01-15T14:00:00.000Z");
        assert_eq!(timestamp_format(1705327200.5), "2024-01-15T14:00:00.500Z");
    }

    #[test]
    fn timestamp_format_millis() {
        assert_eq!(timestamp_format(0.0), "1970-01-01T00:00:00.000Z");
        assert_eq!(timestamp_format(0.001), "1970-01-01T00:00:00.001Z");
    }

    #[test]
    fn promql_query_format() {
        let q = promql_query(1705323600.0);
        assert_eq!(q, "max_over_time(sum(machine_cpu_cores)[59m59s999ms:5m] @ 1705323600.0)");
    }

    #[test]
    fn format_float_py_int_valued() {
        assert_eq!(format_float_py(1000.0), "1000.0");
        assert_eq!(format_float_py(0.0), "0.0");
    }

    #[test]
    fn gather_metering_disabled() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let info = rt.block_on(gather("my-cluster", false, None, None, None, Some(1705327200.0))).unwrap().unwrap();
        assert_eq!(info.cluster_name, "my-cluster");
        assert_eq!(info.total_workers_vcpu, Some(1));
        assert!(!info.usage_based_billing_enabled);
        assert_eq!(info.start_timestamp, "2024-01-15T13:00:00.000Z");
        assert_eq!(info.end_timestamp, "2024-01-15T13:59:59.999Z");
    }

    #[test]
    fn gather_missing_cluster_name() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let err = rt.block_on(gather("", true, None, None, None, Some(1705327200.0))).unwrap_err();
        assert!(matches!(err, VcpuError::MissingClusterName));
    }
}
