# =============================================================================
# bandwidth_monitor.py – Real-Time Network Bandwidth Monitor
# =============================================================================
# Uses psutil to measure bytes sent/received over a configurable interval
# and converts them into human-friendly Mbps values.

import time
import threading
import psutil
from datetime import datetime

import config


def get_bandwidth_sample(interval: float = config.BANDWIDTH_INTERVAL) -> dict:
    """
    Measure upload and download speed over a given interval.

    How it works:
      1. Record bytes sent/received at time T1.
      2. Wait 'interval' seconds.
      3. Record bytes sent/received at time T2.
      4. Compute speed = (delta_bytes * 8) / (interval * 1_000_000) → Mbps

    Args:
        interval (float): Sampling window in seconds.

    Returns:
        dict with keys:
            timestamp      – ISO-format string
            upload_mbps    – Upload speed in Megabits per second
            download_mbps  – Download speed in Megabits per second
    """
    # Snapshot 1 – before the interval
    counters_before = psutil.net_io_counters()
    time.sleep(interval)
    # Snapshot 2 – after the interval
    counters_after = psutil.net_io_counters()

    bytes_sent = counters_after.bytes_sent - counters_before.bytes_sent
    bytes_recv = counters_after.bytes_recv - counters_before.bytes_recv

    # Convert bytes → Megabits: multiply by 8 bits, divide by 1,000,000
    upload_mbps   = (bytes_sent * 8) / (interval * 1_000_000)
    download_mbps = (bytes_recv * 8) / (interval * 1_000_000)

    return {
        "timestamp":     datetime.now().isoformat(timespec="seconds"),
        "upload_mbps":   round(upload_mbps,   3),
        "download_mbps": round(download_mbps, 3),
    }


class BandwidthMonitor:
    """
    Continuously samples bandwidth in a background thread.

    Usage:
        monitor = BandwidthMonitor()
        monitor.start()
        ...
        latest = monitor.latest   # always has the most recent reading
        ...
        monitor.stop()
    """

    def __init__(self):
        self.latest: dict = {
            "timestamp": None,
            "upload_mbps": 0.0,
            "download_mbps": 0.0,
        }
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="BandwidthMonitor")

    def start(self):
        """Start the background monitoring thread."""
        self._thread.start()

    def stop(self):
        """Signal the monitoring thread to stop and wait for it to finish."""
        self._stop_event.set()
        self._thread.join(timeout=config.BANDWIDTH_INTERVAL + 1)

    def _run(self):
        """Inner loop – keep measuring until stop() is called."""
        while not self._stop_event.is_set():
            sample = get_bandwidth_sample(config.BANDWIDTH_INTERVAL)
            self.latest = sample
