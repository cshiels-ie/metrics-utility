//! Env/config — mirrors metrics_utility/base/utils.py + management/validation.py

use chrono::{DateTime, Utc, Duration, TimeZone};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS can not be converted to an integer")]
    BadMaxGather,
    #[error("METRICS_UTILITY_SHIP_TARGET must be one of 'crc', 'directory', 's3' (got '{0}')")]
    BadShipTarget(String),
    #[error("date parse error: {0}")]
    DateParse(String),
}

pub fn get_max_gather_period_days() -> Result<i64, ConfigError> {
    let raw = std::env::var("METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS").unwrap_or_else(|_| "28".to_string());
    raw.parse().map_err(|_| ConfigError::BadMaxGather)
}

pub fn bool_from_env(name: &str, default: Option<bool>) -> Option<bool> {
    match std::env::var(name) {
        Ok(v) => Some(matches!(v.to_lowercase().as_str(), "1" | "true")),
        Err(_) => default,
    }
}

pub fn get_optional_collectors() -> Vec<String> {
    let raw = std::env::var("METRICS_UTILITY_OPTIONAL_COLLECTORS").unwrap_or_else(|_| "main_jobevent".to_string());
    raw.split(',')
        .map(|s| s.trim().trim_matches(|c| c == ',' || c == ' ' || c == '\t').to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ShipTarget { Crc, Directory, S3 }

impl ShipTarget {
    pub fn from_env() -> Result<Self, ConfigError> {
        let raw = std::env::var("METRICS_UTILITY_SHIP_TARGET").unwrap_or_default();
        match raw.as_str() {
            "crc" => Ok(Self::Crc),
            "directory" => Ok(Self::Directory),
            "s3" => Ok(Self::S3),
            other => Err(ConfigError::BadShipTarget(other.to_string())),
        }
    }
    pub fn as_str(&self) -> &'static str {
        match self { Self::Crc => "crc", Self::Directory => "directory", Self::S3 => "s3" }
    }
}

// Window calculation — mirrors Collector._calculate_collection_interval
#[derive(Debug, Clone)]
pub struct GatherWindow {
    pub since: Option<DateTime<Utc>>,
    pub until: DateTime<Utc>,
    pub horizon: DateTime<Utc>,
}

impl GatherWindow {
    pub fn calculate(since: Option<DateTime<Utc>>, until: Option<DateTime<Utc>>, now: DateTime<Utc>, max_days: i64) -> Result<Self, ConfigError> {
        let mut since = since;
        let mut until = until;
        let max_dur = Duration::days(max_days);

        if let Some(u) = until { if u > now { until = Some(now); } }
        if let Some(s) = since { if s > now { since = Some(now); } }

        if since.is_some() {
            if let (Some(s), Some(u)) = (since, until) {
                if u > s + max_dur { until = Some(s + max_dur); }
            }
            if until.is_none() {
                let s = since.unwrap();
                until = Some(std::cmp::min(s + max_dur, now));
            }
        } else if until.is_none() {
            until = Some(now);
        }

        let until = until.unwrap();
        let horizon = until - max_dur;

        if let Some(s) = since {
            if s > until { return Err(ConfigError::DateParse("Start is later than end".into())); }
            if s < horizon {
                since = Some(horizon);
            }
        }

        Ok(Self { since, until, horizon })
    }
}

pub fn parse_date_param(s: Option<&str>, now: DateTime<Utc>) -> Result<Option<DateTime<Utc>>, ConfigError> {
    let Some(raw) = s else { return Ok(None); };
    if raw.is_empty() { return Ok(None); }

    // Absolute date YYYY-MM-DD -> start of day UTC
    if let Ok(d) = chrono::NaiveDate::parse_from_str(raw, "%Y-%m-%d") {
        return Ok(Some(d.and_hms_opt(0,0,0).unwrap().and_utc()));
    }
    // ISO datetime
    if let Ok(dt) = raw.parse::<DateTime<Utc>>() {
        return Ok(Some(dt));
    }
    // Relative: 5d, 2m, 2mo (m = minutes, mo = months)
    let lower = raw.to_lowercase();
    if lower.ends_with("days") || lower.ends_with("day") {
        let _num: i64 = lower.trim_end_matches(|c: char| !c.is_ascii_digit()).parse().map_err(|_| ConfigError::DateParse(format!("invalid date: {raw}")))?;
        return Ok(Some(Utc.from_local_datetime(&now.naive_local().date().and_hms_opt(0,0,0).unwrap()).unwrap()));
    }
    if lower.ends_with('d') && !lower.ends_with("mo") {
        let num: i64 = lower.trim_end_matches('d').parse().map_err(|_| ConfigError::DateParse(format!("invalid date: {raw}")))?;
        let start_of_day = Utc.from_local_datetime(&now.naive_local().date().and_hms_opt(0,0,0).unwrap()).unwrap();
        return Ok(Some(start_of_day - Duration::days(num)));
    }
    if lower.ends_with('m') && !lower.ends_with("mo") {
        let num: i64 = lower.trim_end_matches('m').parse().map_err(|_| ConfigError::DateParse(format!("invalid date: {raw}")))?;
        return Ok(Some(now - Duration::minutes(num)));
    }
    Err(ConfigError::DateParse(format!("invalid date format: {raw}. {}", "An absolute date (--since=2023-12-20) (start of day, UTC), a number of minutes ago (--since=2m), a number of days ago (--since=5d), or months ago (--since=2mo)")))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bool_from_env_cases() {
        std::env::set_var("TEST_BOOL_T", "true");
        assert_eq!(bool_from_env("TEST_BOOL_T", None), Some(true));
        std::env::set_var("TEST_BOOL_T", "1");
        assert_eq!(bool_from_env("TEST_BOOL_T", None), Some(true));
        std::env::set_var("TEST_BOOL_T", "false");
        assert_eq!(bool_from_env("TEST_BOOL_T", None), Some(false));
        std::env::remove_var("TEST_BOOL_T2");
        assert_eq!(bool_from_env("TEST_BOOL_T2", Some(false)), Some(false));
    }
    #[test]
    fn gather_window_clamps_to_max_days() {
        let now = Utc.with_ymd_and_hms(2024,1,15,14,0,0).unwrap();
        let since = Utc.with_ymd_and_hms(2023,12,1,0,0,0).unwrap();
        let w = GatherWindow::calculate(Some(since), None, now, 28).unwrap();
        assert_eq!(w.until, Utc.with_ymd_and_hms(2023,12,29,0,0,0).unwrap());
    }
}
