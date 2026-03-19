# =============================================================================
# dashboard.py – Live CLI Dashboard (powered by the `rich` library)
# =============================================================================
# Displays current network metrics in a nicely formatted, auto-refreshing
# terminal table. Designed to run in a background thread.

import threading
import time
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.columns import Columns
from rich.text import Text
from rich import box

import config


class Dashboard:
    """
    A live CLI dashboard that refreshes every DASHBOARD_REFRESH seconds.

    Shared state is updated externally by main.py via simple attribute writes.
    No locking is needed because Python's GIL protects simple attribute assignments.

    Usage:
        dash = Dashboard()
        dash.start()
        dash.bw_data     = {"upload_mbps": 5.2, "download_mbps": 30.1, ...}
        dash.ping_data   = [{"host": "8.8.8.8", "latency_ms": 25, ...}, ...]
        dash.alerts      = ["⚠️ HIGH LATENCY ..."]
        dash.packet_info = {"src": "192.168.1.1", "dst": "8.8.8.8", ...}
        ...
        dash.stop()
    """

    def __init__(self):
        self.bw_data:     dict = {}
        self.ping_data:   list = []
        self.alerts:      list = []
        self.packet_info: Optional[dict] = None
        self.sniff_enabled: bool = True
        self.start_time   = datetime.now()

        self._stop_event = threading.Event()
        self._console    = Console()
        self._thread     = threading.Thread(target=self._run, daemon=True, name="Dashboard")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=3)

    # ── Layout builders ───────────────────────────────────────────────────────

    def _build_header(self) -> Panel:
        elapsed = datetime.now() - self.start_time
        h, rem  = divmod(int(elapsed.total_seconds()), 3600)
        m, s    = divmod(rem, 60)
        title   = Text(f" 🌐  Network Monitor   elapsed: {h:02d}:{m:02d}:{s:02d} ", style="bold cyan")
        return Panel(title, box=box.DOUBLE_EDGE, style="bold blue")

    def _build_bandwidth_table(self) -> Panel:
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold magenta")
        table.add_column("Metric",  style="dim", width=20)
        table.add_column("Value",   justify="right")

        up   = self.bw_data.get("upload_mbps",   0.0)
        down = self.bw_data.get("download_mbps", 0.0)
        ts   = self.bw_data.get("timestamp", "—")

        # Colour download speed: red if below threshold, green otherwise
        down_style = "bold red" if down < config.MIN_DOWNLOAD_MBPS else "bold green"
        up_style   = "bold red" if up   < config.MIN_UPLOAD_MBPS   else "bold yellow"

        table.add_row("⬇  Download Speed", Text(f"{down:.2f} Mbps", style=down_style))
        table.add_row("⬆  Upload Speed",   Text(f"{up:.2f} Mbps",   style=up_style))
        table.add_row("🕐 Last Sample",    ts)

        return Panel(table, title="[bold]Bandwidth[/bold]", border_style="blue")

    def _build_ping_table(self) -> Panel:
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold magenta")
        table.add_column("Host",         style="dim", width=16)
        table.add_column("Latency (ms)", justify="right")
        table.add_column("Packet Loss",  justify="right")

        for r in self.ping_data:
            lat  = r.get("latency_ms")
            loss = r.get("packet_loss_pct", 0)
            host = r.get("host", "?")

            lat_str  = f"{lat:.1f}" if lat is not None else "Timeout"
            loss_str = f"{loss:.0f}%"

            lat_style  = "bold red" if (lat is None or lat > config.MAX_LATENCY_MS) else "bold green"
            loss_style = "bold red" if loss > config.MAX_PACKET_LOSS_PCT else "green"

            table.add_row(host, Text(lat_str, style=lat_style), Text(loss_str, style=loss_style))

        if not self.ping_data:
            table.add_row("—", "—", "—")

        return Panel(table, title="[bold]Ping Results[/bold]", border_style="cyan")

    def _build_alerts_panel(self) -> Panel:
        if self.alerts:
            content = "\n".join(self.alerts[-5:])   # Show last 5 alerts
            style   = "bold red"
        else:
            content = "✅  No anomalies detected."
            style   = "green"
        return Panel(Text(content, style=style), title="[bold]Alerts[/bold]", border_style="red")

    def _build_packet_panel(self) -> Panel:
        if not self.sniff_enabled:
            content = Text("Packet sniffer disabled (--no-sniff).", style="dim")
        elif self.packet_info:
            p       = self.packet_info
            content = Text(
                f"  Src: {p.get('src', '?')}\n"
                f"  Dst: {p.get('dst', '?')}\n"
                f"  Protocol: {p.get('protocol', '?')}\n"
                f"  Length: {p.get('length', '?')} bytes",
                style="white"
            )
        else:
            content = Text("Waiting for packets…", style="dim")

        return Panel(content, title="[bold]Last Captured Packet[/bold]", border_style="yellow")

    def _build_layout(self):
        """Assemble all panels into a printable renderable."""
        top_row    = Columns([self._build_bandwidth_table(), self._build_ping_table()], equal=True)
        bottom_row = Columns([self._build_alerts_panel(),    self._build_packet_panel()], equal=True)
        return [self._build_header(), top_row, bottom_row]

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self):
        with Live(console=self._console, refresh_per_second=1, screen=False) as live:
            while not self._stop_event.is_set():
                panels = self._build_layout()
                # Render as a group
                from rich.console import Group
                live.update(Group(*panels))
                time.sleep(config.DASHBOARD_REFRESH)
