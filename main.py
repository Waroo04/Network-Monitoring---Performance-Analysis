# =============================================================================
# main.py – Entry Point for Network Monitoring & Performance Analysis Tool
# =============================================================================
# Orchestrates all modules, handles CLI arguments, spawns threads, and cleanly
# shuts everything down on Ctrl+C or when the optional --duration expires.
#
# Usage:
#   python main.py                     # Run indefinitely
#   python main.py --duration 60       # Run for 60 seconds then auto-stop
#   python main.py --no-sniff          # Disable packet sniffer (no admin needed)
#   python main.py --report            # Generate graph from existing CSV and exit
#   python main.py --duration 60 --no-sniff  # Combine flags freely

import argparse
import signal
import sys
import time
import threading
from datetime import datetime

# ── Local modules ─────────────────────────────────────────────────────────────
import config
from bandwidth_monitor  import BandwidthMonitor
from ping_monitor       import PingMonitor
from packet_sniffer     import PacketSniffer
from bottleneck_detector import analyse as detect_bottlenecks
import logger
import visualizer
from dashboard          import Dashboard


# =============================================================================
# Globals
# =============================================================================
_stop_event = threading.Event()     # Signals all loop threads to stop
_dashboard  = None                  # Reference so signal handler can stop it


# =============================================================================
# Signal handler (Ctrl+C / SIGTERM)
# =============================================================================
def _handle_exit(signum, frame):
    print("\n\n[Main] Shutdown signal received. Stopping all threads…")
    _stop_event.set()


# =============================================================================
# Logging loop – runs in its own thread
# =============================================================================
def _logging_loop(bw_monitor: BandwidthMonitor, ping_monitor: PingMonitor):
    """
    Every PING_INTERVAL seconds, collect the latest bandwidth + ping readings,
    run anomaly detection, push alerts to the dashboard, and write to CSV.
    """
    while not _stop_event.is_set():
        bw      = bw_monitor.latest
        pings   = ping_monitor.latest_results

        if bw.get("timestamp") and pings:
            alerts = detect_bottlenecks(bw, pings)

            if alerts:
                # Print alerts to console (visible even without the dashboard)
                for alert in alerts:
                    print(f"  [ALERT] {alert}")

            # Push to dashboard (no-op if dashboard is None)
            if _dashboard:
                _dashboard.bw_data   = bw
                _dashboard.ping_data = pings
                _dashboard.alerts    = (_dashboard.alerts + alerts)[-20:]  # keep last 20

            # Log each ping target as its own CSV row
            for ping_result in pings:
                logger.log_metrics(bw, ping_result, alerts)

        # Sleep in small ticks so we react to _stop_event promptly
        for _ in range(config.PING_INTERVAL * 10):
            if _stop_event.is_set():
                break
            time.sleep(0.1)


# =============================================================================
# CLI argument parser
# =============================================================================
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Network Monitoring & Performance Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --duration 120
  python main.py --no-sniff --duration 30
  python main.py --report
        """
    )
    parser.add_argument(
        "--duration", type=int, default=config.DEFAULT_DURATION, metavar="SECONDS",
        help="How long to run (0 = run until Ctrl+C).",
    )
    parser.add_argument(
        "--no-sniff", action="store_true",
        help="Disable packet capture (no Administrator/root privileges needed).",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Read existing CSV log and generate a graph, then exit.",
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="Disable the live CLI dashboard (plain text output only).",
    )
    return parser.parse_args()


# =============================================================================
# Main entry point
# =============================================================================
def main():
    global _dashboard

    args = _parse_args()

    # ── Report-only mode ──────────────────────────────────────────────────────
    if args.report:
        print("[Main] Generating performance report from CSV…")
        visualizer.generate_report()
        return

    # ── Banner ────────────────────────────────────────────────────────────────
    print("=" * 60)
    print("   Network Monitoring & Performance Analysis Tool")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.duration:
        print(f"   Duration: {args.duration} seconds")
    else:
        print("   Duration: Indefinite (Ctrl+C to stop)")
    if args.no_sniff:
        print("   Packet sniffer: DISABLED")
    print("=" * 60)

    # ── Register signal handlers ──────────────────────────────────────────────
    signal.signal(signal.SIGINT,  _handle_exit)
    signal.signal(signal.SIGTERM, _handle_exit)

    # ── Initialise monitors ───────────────────────────────────────────────────
    bw_monitor   = BandwidthMonitor()
    ping_monitor = PingMonitor()
    sniffer      = PacketSniffer(
        on_packet=lambda pkt: setattr(_dashboard, "packet_info", pkt) if _dashboard else None
    )

    # ── Initialise dashboard ──────────────────────────────────────────────────
    if not args.no_dashboard:
        _dashboard = Dashboard()
        _dashboard.sniff_enabled = not args.no_sniff

    # ── Start background threads ──────────────────────────────────────────────
    bw_monitor.start()
    ping_monitor.start()

    if not args.no_sniff:
        sniffer.start()
    else:
        print("[Main] Packet sniffer skipped.")

    if _dashboard:
        _dashboard.start()

    # ── Logging loop (separate thread) ────────────────────────────────────────
    log_thread = threading.Thread(
        target=_logging_loop,
        args=(bw_monitor, ping_monitor),
        daemon=True,
        name="LoggingLoop",
    )
    log_thread.start()

    # ── Wait for duration or Ctrl+C ───────────────────────────────────────────
    try:
        if args.duration > 0:
            _stop_event.wait(timeout=args.duration)
            if not _stop_event.is_set():
                print(f"\n[Main] Duration of {args.duration}s elapsed. Stopping…")
                _stop_event.set()
        else:
            _stop_event.wait()   # Block indefinitely
    except KeyboardInterrupt:
        _stop_event.set()

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    print("[Main] Stopping monitors…")
    bw_monitor.stop()
    ping_monitor.stop()
    sniffer.stop()

    if _dashboard:
        _dashboard.stop()

    log_thread.join(timeout=5)

    print(f"[Main] All threads stopped. Log saved to: {config.CSV_LOG_FILE}")
    print("[Main] Run  'python main.py --report'  to generate a performance graph.")
    print("[Main] Done.")


# =============================================================================
if __name__ == "__main__":
    main()
