# =============================================================================
# logger.py – Thread-Safe CSV Logger
# =============================================================================
# Appends one row per monitoring cycle to network_log.csv.
# A threading.Lock ensures no data corruption when multiple threads write.

import csv
import os
import threading
from datetime import datetime
from typing import Optional

import config

# Column headers for the CSV file – order matters for readability
CSV_HEADERS = [
    "timestamp",
    "upload_mbps",
    "download_mbps",
    "ping_host",
    "latency_ms",
    "packet_loss_pct",
    "alerts",
]

_lock = threading.Lock()   # Shared lock; module-level so all callers share it


def _ensure_file():
    """Create the CSV file with headers if it does not already exist."""
    if not os.path.exists(config.CSV_LOG_FILE):
        with open(config.CSV_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


def log_metrics(
    bw_sample: dict,
    ping_result: dict,
    alerts: Optional[list] = None,
):
    """
    Append one row to the CSV log file.

    Args:
        bw_sample   (dict): {'timestamp', 'upload_mbps', 'download_mbps'}
        ping_result (dict): {'host', 'latency_ms', 'packet_loss_pct', 'timestamp'}
        alerts      (list): List of alert strings (may be empty or None).
    """
    alert_str = " | ".join(alerts) if alerts else ""
    row = {
        "timestamp":       bw_sample.get("timestamp", datetime.now().isoformat(timespec="seconds")),
        "upload_mbps":     bw_sample.get("upload_mbps", 0),
        "download_mbps":   bw_sample.get("download_mbps", 0),
        "ping_host":       ping_result.get("host", ""),
        "latency_ms":      ping_result.get("latency_ms", ""),
        "packet_loss_pct": ping_result.get("packet_loss_pct", ""),
        "alerts":          alert_str,
    }

    with _lock:
        _ensure_file()
        with open(config.CSV_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow(row)


def get_all_records() -> list[dict]:
    """
    Read and return all rows from the CSV as a list of dicts.
    Useful for the visualiser module.

    Returns:
        List of row dicts, or empty list if file doesn't exist yet.
    """
    if not os.path.exists(config.CSV_LOG_FILE):
        return []

    with _lock:
        with open(config.CSV_LOG_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
