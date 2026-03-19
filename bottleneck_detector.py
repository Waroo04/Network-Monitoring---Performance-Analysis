# =============================================================================
# bottleneck_detector.py – Network Bottleneck & Anomaly Detection
# =============================================================================
# Compares current measurements against thresholds defined in config.py.
# Returns human-readable alert strings so other modules can log or display them.

from typing import Optional
import config


def check_bandwidth(upload_mbps: float, download_mbps: float) -> list[str]:
    """
    Check upload/download speeds against configured minimums.

    Args:
        upload_mbps   (float): Current upload speed in Mbps.
        download_mbps (float): Current download speed in Mbps.

    Returns:
        A list of alert strings (empty list = no issues detected).
    """
    alerts = []

    if download_mbps < config.MIN_DOWNLOAD_MBPS:
        alerts.append(
            f"⚠️  LOW BANDWIDTH (Download): {download_mbps:.2f} Mbps "
            f"(threshold: {config.MIN_DOWNLOAD_MBPS} Mbps)"
        )

    if upload_mbps < config.MIN_UPLOAD_MBPS:
        alerts.append(
            f"⚠️  LOW BANDWIDTH (Upload): {upload_mbps:.2f} Mbps "
            f"(threshold: {config.MIN_UPLOAD_MBPS} Mbps)"
        )

    return alerts


def check_latency(latency_ms: Optional[float], host: str) -> list[str]:
    """
    Check ping latency against the configured maximum.

    Args:
        latency_ms (float | None): Average round-trip time in ms. None = unreachable.
        host       (str):          The hostname/IP that was pinged.

    Returns:
        A list of alert strings.
    """
    alerts = []

    if latency_ms is None:
        alerts.append(f"🔴 HOST UNREACHABLE: {host} did not respond to ping.")
    elif latency_ms > config.MAX_LATENCY_MS:
        alerts.append(
            f"⚠️  HIGH LATENCY to {host}: {latency_ms:.1f} ms "
            f"(threshold: {config.MAX_LATENCY_MS} ms)"
        )

    return alerts


def check_packet_loss(packet_loss_pct: float, host: str) -> list[str]:
    """
    Check packet loss percentage against the configured maximum.

    Args:
        packet_loss_pct (float): Percentage of lost packets (0-100).
        host            (str):   The host that was pinged.

    Returns:
        A list of alert strings.
    """
    alerts = []

    if packet_loss_pct > config.MAX_PACKET_LOSS_PCT:
        alerts.append(
            f"⚠️  PACKET LOSS to {host}: {packet_loss_pct:.0f}% "
            f"(threshold: {config.MAX_PACKET_LOSS_PCT}%)"
        )

    return alerts


def analyse(bw_sample: dict, ping_results: list) -> list[str]:
    """
    Run all checks and return a combined list of alerts.

    Args:
        bw_sample    (dict): Output from BandwidthMonitor.latest.
        ping_results (list): Output from PingMonitor.latest_results.

    Returns:
        Combined list of alert strings across all checks.
    """
    all_alerts = []

    # Bandwidth checks
    all_alerts += check_bandwidth(
        bw_sample.get("upload_mbps", 0),
        bw_sample.get("download_mbps", 0),
    )

    # Per-host latency & packet loss checks
    for result in ping_results:
        all_alerts += check_latency(result.get("latency_ms"), result.get("host", "?"))
        all_alerts += check_packet_loss(result.get("packet_loss_pct", 0), result.get("host", "?"))

    return all_alerts
