# =============================================================================
# server.py – Flask Web Server & REST API for Network Monitor
# =============================================================================
# Runs the monitoring threads in the background and exposes JSON endpoints
# that the browser dashboard polls every 2 seconds.
#
# Endpoints:
#   GET /                  → Serve the web dashboard (index.html)
#   GET /api/status        → Current bandwidth, ping, alerts, packets
#   GET /api/history       → Full CSV data for historical graphs
#   GET /api/packets       → Last N captured packets
#
# Run:
#   python server.py
#   python server.py --no-sniff
#   python server.py --port 8080

import argparse
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template, request

import config
from bandwidth_monitor    import BandwidthMonitor
from ping_monitor         import PingMonitor
from packet_sniffer       import PacketSniffer
from bottleneck_detector  import analyse as detect_bottlenecks
import logger

# =============================================================================
# Flask App
# =============================================================================
app = Flask(__name__)

# =============================================================================
# Shared State  (written by monitor threads, read by API handlers)
# =============================================================================
_state = {
    "bw":      {"timestamp": None, "upload_mbps": 0.0, "download_mbps": 0.0},
    "pings":   [],
    "alerts":  [],          # rolling list of the last 50 alerts
    "packets": [],          # rolling list of the last 50 packets
    "started": datetime.now().isoformat(timespec="seconds"),
}
_state_lock = threading.Lock()


# =============================================================================
# Background Monitors
# =============================================================================
bw_monitor   = BandwidthMonitor()
ping_monitor = PingMonitor()
sniffer      = PacketSniffer()     # enabled/disabled by --no-sniff below


def _on_packet(pkt_info: dict):
    """Callback from PacketSniffer – push to shared state."""
    with _state_lock:
        _state["packets"].append(pkt_info)
        if len(_state["packets"]) > 50:
            _state["packets"].pop(0)


def _logging_loop():
    """
    Runs in its own thread.
    Every PING_INTERVAL seconds: collect latest readings → detect anomalies →
    update shared state → write to CSV.
    """
    import time
    while True:
        bw    = bw_monitor.latest
        pings = ping_monitor.latest_results

        if bw.get("timestamp") and pings:
            alerts = detect_bottlenecks(bw, pings)

            with _state_lock:
                _state["bw"]    = bw
                _state["pings"] = pings
                # Keep only the last 50 alerts in memory
                _state["alerts"] = (_state["alerts"] + [
                    {"time": datetime.now().strftime("%H:%M:%S"), "message": a}
                    for a in alerts
                ])[-50:]

            for ping_result in pings:
                logger.log_metrics(bw, ping_result, alerts)

        # Sleep in small ticks so the thread stays responsive
        for _ in range(config.PING_INTERVAL * 10):
            time.sleep(0.1)


# =============================================================================
# API Routes
# =============================================================================

@app.route("/")
def index():
    """Serve the main dashboard HTML."""
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """
    Return the current live snapshot.

    Response JSON shape:
    {
        "bandwidth":  { upload_mbps, download_mbps, timestamp },
        "pings":      [ { host, latency_ms, packet_loss_pct, timestamp }, ... ],
        "alerts":     [ { time, message }, ... ],
        "packets":    [ { src, dst, protocol, length, timestamp }, ... ],
        "uptime":     "HH:MM:SS"
    }
    """
    with _state_lock:
        started   = datetime.fromisoformat(_state["started"])
        elapsed   = datetime.now() - started
        h, rem    = divmod(int(elapsed.total_seconds()), 3600)
        m, s      = divmod(rem, 60)

        return jsonify({
            "bandwidth": _state["bw"],
            "pings":     _state["pings"],
            "alerts":    _state["alerts"][-10:],   # last 10 for UI
            "packets":   _state["packets"][-10:],  # last 10 for UI
            "uptime":    f"{h:02d}:{m:02d}:{s:02d}",
        })


@app.route("/api/history")
def api_history():
    """
    Return all CSV rows.  Optional query param: ?limit=N

    Response JSON:
    {
        "rows": [ { timestamp, upload_mbps, download_mbps,
                    ping_host, latency_ms, packet_loss_pct, alerts }, ... ]
    }
    """
    limit = request.args.get("limit", default=None, type=int)
    rows  = logger.get_all_records()

    # Convert numeric-looking strings back to numbers for easier JS charting
    for row in rows:
        for key in ("upload_mbps", "download_mbps", "latency_ms", "packet_loss_pct"):
            try:
                row[key] = float(row[key]) if row[key] not in (None, "") else None
            except (ValueError, TypeError):
                row[key] = None

    if limit:
        rows = rows[-limit:]

    return jsonify({"rows": rows})


@app.route("/api/packets")
def api_packets():
    """Return the last 50 captured packets."""
    with _state_lock:
        return jsonify({"packets": list(_state["packets"])})


# =============================================================================
# Entry Point
# =============================================================================
def _parse_args():
    parser = argparse.ArgumentParser(description="Network Monitor Web Server")
    parser.add_argument("--port",     type=int, default=5000)
    parser.add_argument("--no-sniff", action="store_true",
                        help="Disable Scapy packet capture (no admin needed)")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    # Update the sniffer callback now that we have the shared state ready
    sniffer._on_packet = _on_packet

    # Start background threads
    bw_monitor.start()
    ping_monitor.start()

    if not args.no_sniff:
        sniffer.start()
    else:
        print("[Server] Packet sniffer disabled (--no-sniff).")

    log_thread = threading.Thread(target=_logging_loop, daemon=True, name="LoggingLoop")
    log_thread.start()

    print(f"\n{'='*55}")
    print(f"  Network Monitor Web Dashboard")
    print(f"  Open your browser at:  http://localhost:{args.port}")
    print(f"  Press Ctrl+C to stop.")
    print(f"{'='*55}\n")

    # use_reloader=False is critical – reloader would double-start our threads
    app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)
