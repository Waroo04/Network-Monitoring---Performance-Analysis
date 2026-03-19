# =============================================================================
# ping_monitor.py – Periodic Ping / Latency Monitor
# =============================================================================
# Uses the OS 'ping' command via subprocess. This avoids root/admin
# requirements that raw-socket ICMP libraries often need.
# Works on Windows (ping -n) and Linux/macOS (ping -c).

import subprocess
import platform
import re
import time
import threading
from datetime import datetime
from typing import Optional

import config


def _ping_once(host: str, count: int = 4) -> dict:
    """
    Run a single ping to 'host' with 'count' echo requests.

    Returns:
        dict with keys:
            host            – target hostname/IP
            latency_ms      – average round-trip time in ms (or None if failed)
            packet_loss_pct – percentage of packets lost (0-100)
            timestamp       – ISO-format string
    """
    timestamp = datetime.now().isoformat(timespec="seconds")

    # Build the OS-appropriate command
    if platform.system().lower() == "windows":
        cmd = ["ping", "-n", str(count), host]
    else:
        cmd = ["ping", "-c", str(count), host]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,   # Safety timeout
        )
        output = result.stdout + result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"host": host, "latency_ms": None, "packet_loss_pct": 100, "timestamp": timestamp}

    latency_ms      = _parse_latency(output)
    packet_loss_pct = _parse_packet_loss(output)

    return {
        "host":            host,
        "latency_ms":      latency_ms,
        "packet_loss_pct": packet_loss_pct,
        "timestamp":       timestamp,
    }


def _parse_latency(output: str) -> Optional[float]:
    """
    Extract average latency from ping output.
    Handles both Windows and Linux/macOS formats.
    """
    # Windows: "Average = 25ms"
    match = re.search(r"Average\s*=\s*(\d+(?:\.\d+)?)ms", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Linux/macOS: "rtt min/avg/max/mdev = 10.1/25.3/40.5/5.2 ms"
    match = re.search(r"=\s*[\d.]+/([\d.]+)/", output)
    if match:
        return float(match.group(1))

    return None


def _parse_packet_loss(output: str) -> float:
    """
    Extract packet loss percentage from ping output.
    Handles both Windows ('Lost = N (X% loss)') and Linux/macOS ('X% packet loss').
    """
    # Windows: "(25% loss)"
    match = re.search(r"\((\d+)%\s*loss\)", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Linux/macOS: "25% packet loss"
    match = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", output, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return 0.0


class PingMonitor:
    """
    Periodically pings all configured targets in a background thread.

    Usage:
        pm = PingMonitor()
        pm.start()
        ...
        results = pm.latest_results   # list of dicts, one per target
        ...
        pm.stop()
    """

    def __init__(self):
        self.latest_results: list = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PingMonitor")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=config.PING_INTERVAL + 5)

    def _run(self):
        while not self._stop_event.is_set():
            results = []
            for host in config.PING_TARGETS:
                if self._stop_event.is_set():
                    break
                results.append(_ping_once(host))
            self.latest_results = results
            # Sleep in small ticks so stop() is responsive
            for _ in range(config.PING_INTERVAL * 10):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)
