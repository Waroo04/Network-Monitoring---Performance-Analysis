# =============================================================================
# visualizer.py – Performance Graph Generator (Matplotlib)
# =============================================================================
# Reads network_log.csv and produces a 2-subplot PNG:
#   • Top panel   – Upload & Download speed over time (Mbps)
#   • Bottom panel – Ping latency over time (ms) with threshold line

import csv
import os
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import config
import logger


def _safe_float(value, default=None):
    """Safely convert a string to float; return default if conversion fails."""
    try:
        return float(value) if value not in (None, "", "None") else default
    except (ValueError, TypeError):
        return default


def generate_report(save_path: str = config.REPORT_IMAGE_FILE, show: bool = True):
    """
    Read the CSV log and produce a performance graph.

    Args:
        save_path (str): Where to save the PNG image.
        show      (bool): If True, open the image in a window after saving.
    """
    records = logger.get_all_records()

    if not records:
        print("[Visualizer] No data in CSV yet. Run the monitor first.")
        return

    # ── Parse CSV data ────────────────────────────────────────────────────────
    timestamps  = []
    uploads     = []
    downloads   = []
    latencies   = []
    lat_times   = []   # Subset of timestamps that have latency readings

    for row in records:
        try:
            ts = datetime.fromisoformat(row["timestamp"])
        except (ValueError, KeyError):
            continue

        timestamps.append(ts)
        uploads.append(_safe_float(row.get("upload_mbps"), 0.0))
        downloads.append(_safe_float(row.get("download_mbps"), 0.0))

        lat = _safe_float(row.get("latency_ms"))
        if lat is not None:
            latencies.append(lat)
            lat_times.append(ts)

    if not timestamps:
        print("[Visualizer] No valid data rows found.")
        return

    # ── Build the figure ──────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=False)
    fig.suptitle("Network Performance Report", fontsize=16, fontweight="bold", y=0.98)
    fig.patch.set_facecolor("#1e1e2e")

    for ax in (ax1, ax2):
        ax.set_facecolor("#2a2a3e")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555577")

    # ── Panel 1: Bandwidth ────────────────────────────────────────────────────
    ax1.plot(timestamps, downloads, label="Download (Mbps)", color="#00d4ff", linewidth=1.5)
    ax1.plot(timestamps, uploads,   label="Upload (Mbps)",   color="#ff7b54", linewidth=1.5, linestyle="--")
    ax1.axhline(config.MIN_DOWNLOAD_MBPS, color="#ff4c4c", linestyle=":", linewidth=1,
                label=f"Min Download Threshold ({config.MIN_DOWNLOAD_MBPS} Mbps)")
    ax1.set_title("Bandwidth Over Time")
    ax1.set_ylabel("Speed (Mbps)")
    ax1.legend(facecolor="#2a2a3e", labelcolor="white", framealpha=0.7)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.autofmt_xdate(ax=ax1)

    # ── Panel 2: Latency ──────────────────────────────────────────────────────
    if latencies:
        ax2.plot(lat_times, latencies, label="Avg Latency (ms)", color="#a8ff78", linewidth=1.5, marker="o", markersize=3)
        ax2.axhline(config.MAX_LATENCY_MS, color="#ff4c4c", linestyle=":", linewidth=1,
                    label=f"Max Latency Threshold ({config.MAX_LATENCY_MS} ms)")
        ax2.legend(facecolor="#2a2a3e", labelcolor="white", framealpha=0.7)
    else:
        ax2.text(0.5, 0.5, "No latency data available", transform=ax2.transAxes,
                 ha="center", va="center", color="gray", fontsize=12)

    ax2.set_title("Ping Latency Over Time")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_xlabel("Time")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    fig.autofmt_xdate(ax=ax2)

    # ── Save & Show ───────────────────────────────────────────────────────────
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    print(f"[Visualizer] Report saved to: {os.path.abspath(save_path)}")

    if show:
        plt.show()

    plt.close(fig)


if __name__ == "__main__":
    # Allow running this module standalone: python visualizer.py
    generate_report()
