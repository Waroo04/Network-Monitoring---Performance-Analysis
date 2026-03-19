# =============================================================================
# config.py – Central Configuration for Network Monitoring Tool
# =============================================================================
# All tunable settings live here. Edit this file to customise thresholds,
# targets, intervals, and file paths without touching the core modules.

# ── Ping Targets ──────────────────────────────────────────────────────────────
# A list of hosts that will be pinged to measure latency & packet loss.
PING_TARGETS = [
    "8.8.8.8",        # Google DNS
    "1.1.1.1",        # Cloudflare DNS
    "google.com",     # General internet reachability
]

# ── Sampling Intervals (seconds) ──────────────────────────────────────────────
BANDWIDTH_INTERVAL   = 1   # How often bandwidth is measured (seconds)
PING_INTERVAL        = 5   # How often ping tests run (seconds)
DASHBOARD_REFRESH    = 1   # How often the CLI dashboard refreshes (seconds)

# ── Packet Sniffer ────────────────────────────────────────────────────────────
SNIFF_PACKET_COUNT   = 10  # Number of packets to capture per sniff burst
SNIFF_TIMEOUT        = 5   # Max seconds to wait for packets per burst

# ── Bottleneck / Alert Thresholds ─────────────────────────────────────────────
MIN_DOWNLOAD_MBPS    = 1.0   # Below this  → LOW BANDWIDTH alert (Mbps)
MIN_UPLOAD_MBPS      = 0.5   # Below this  → LOW UPLOAD alert    (Mbps)
MAX_LATENCY_MS       = 150   # Above this  → HIGH LATENCY alert  (ms)
MAX_PACKET_LOSS_PCT  = 10    # Above this  → PACKET LOSS alert   (%)

# ── File Paths ────────────────────────────────────────────────────────────────
CSV_LOG_FILE         = "network_log.csv"       # CSV output file
REPORT_IMAGE_FILE    = "network_report.png"    # Graph output image

# ── Misc ──────────────────────────────────────────────────────────────────────
DEFAULT_DURATION     = 0    # 0 = run indefinitely until Ctrl+C
