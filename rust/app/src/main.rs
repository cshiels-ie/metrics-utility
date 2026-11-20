//! metrics-utility Rust front door — billing CLI for Controller base image.
//!
//! v1: scaffolds the clap interface matching `gather_automation_controller_billing_data`
//! and falls back to the Python implementation for everything not yet ported.
//! Each completed crate is wired in by replacing its fallback branch.

use clap::{Parser, Subcommand};
use tracing_subscriber::EnvFilter;

/// metrics-utility — Rust billing pipeline for Automation Controller
#[derive(Debug, Parser)]
#[command(name = "metrics-utility", version, about)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Fallback: if no subcommand matched, proxy raw args to Python
    #[arg(trailing_var_arg = true, allow_hyphen_values = true, hide = true)]
    _fallback: Vec<String>,
}

#[derive(Debug, Subcommand)]
enum Commands {
    /// Gather Automation Controller billing data (port in progress)
    GatherAutomationControllerBillingData(GatherArgs),
}

#[derive(Debug, Parser)]
struct GatherArgs {
    /// Start date for collection, inclusive (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
    #[arg(long)]
    since: Option<String>,

    /// End date for collection, exclusive
    #[arg(long)]
    until: Option<String>,

    /// Gather and ship to console.redhat.com
    #[arg(long)]
    ship: bool,

    /// Gather without shipping (dry-run)
    #[arg(long = "dry-run")]
    dry_run: bool,

    /// Verbose debug logging
    #[arg(long, short)]
    verbose: bool,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cli = Cli::parse();

    match cli.command {
        Some(Commands::GatherAutomationControllerBillingData(args)) => {
            run_gather(args).await
        }
        None => {
            // No known subcommand — fall back to Python metrics-utility
            // This preserves every other command (build_report, etc.) until ported.
            fallback_to_python()
        }
    }
}

async fn run_gather(args: GatherArgs) -> anyhow::Result<()> {
    if args.ship && args.dry_run {
        eprintln!("Arguments --ship and --dry-run cannot be processed at the same time, set only one of these.");
        std::process::exit(1);
    }

    // Verbose enables debug logging
    if args.verbose {
        eprintln!("[metrics-utility-rs] verbose mode enabled");
    }

    // Check if billing vCPU collector is enabled and run it as a proof of port
    // Full DB gathering still falls back to Python until wave 3+ is complete.
    let optional = std::env::var("METRICS_UTILITY_OPTIONAL_COLLECTORS").unwrap_or_default();
    let metering_enabled = matches!(
        std::env::var("METRICS_UTILITY_USAGE_BASED_METERING_ENABLED")
            .unwrap_or_default()
            .to_lowercase()
            .as_str(),
        "1" | "true"
    );

    // If vCPU collection was ported and requested, demonstrate it
    if optional.contains("total_workers_vcpu") || metering_enabled {
        let cluster_name = std::env::var("METRICS_UTILITY_CLUSTER_NAME").unwrap_or_default();
        let prom_url = std::env::var("METRICS_UTILITY_PROMETHEUS_URL").ok();
        let ca_path = std::env::var("METRICS_UTILITY_PROMETHEUS_CA_CERT_PATH").ok();
        let token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token";
        let token = std::fs::read_to_string(token_path).ok().map(|s| s.trim().to_string());

        // Only attempt Prometheus I/O if metering is enabled and we have the basics
        if metering_enabled && !cluster_name.is_empty() {
            tracing::info!("gathering total_workers_vcpu via Rust collector");
            match vcpu::gather(
                &cluster_name,
                metering_enabled,
                prom_url.as_deref(),
                ca_path.as_deref(),
                token.as_deref(),
                None,
            )
            .await
            {
                Ok(Some(info)) => {
                    println!("{}", serde_json::to_string_pretty(&info)?);
                }
                Ok(None) => {
                    eprintln!("No data available yet, the cluster is probably running for less than an hour");
                    std::process::exit(1);
                }
                Err(e) => {
                    eprintln!("vcpu gather failed: {e}");
                    // Fall through to Python fallback for full pipeline
                }
            }
            // Fall through to full gather via Python until DB collectors are ported
        }
    }

    // Full pipeline not yet ported — delegate to Python
    fallback_to_python()
}

fn fallback_to_python() -> anyhow::Result<()> {
    // Re-exec the Python metrics-utility with the same args
    // Look for the Python entry point: prefer venv, then system
    let candidates = [
        "/var/lib/awx/venv/awx/bin/python",
        "/usr/bin/python3",
        "python3",
    ];

    let args: Vec<String> = std::env::args().collect();
    // args[0] is our binary; forward the rest to Python's manage
    let py_args = &args[1..];

    for python in candidates {
        // Try `python -m metrics_utility` style via manage
        let status = std::process::Command::new(python)
            .arg("-c")
            .arg("from metrics_utility import manage; manage()")
            .args(py_args)
            .status();

        match status {
            Ok(s) => std::process::exit(s.code().unwrap_or(1)),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(e) => {
                eprintln!("fallback to Python failed: {e}");
                std::process::exit(1);
            }
        }
    }

    anyhow::bail!("no Python interpreter found for fallback")
}
