# =============================================================================
# packet_sniffer.py – Basic Packet Capture using Scapy
# =============================================================================
# Scapy requires administrator / root privileges on most systems.
# On Windows: Run your terminal as Administrator.
# On Linux:   Run with 'sudo python main.py'.
#
# The sniffer runs in short bursts (SNIFF_PACKET_COUNT packets or SNIFF_TIMEOUT
# seconds, whichever comes first) so it never blocks other threads.

import threading
import time
from datetime import datetime

import config

# We import Scapy lazily to allow --no-sniff mode to work without Scapy present.
_scapy_available = False
try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP
    _scapy_available = True
except ImportError:
    pass


def _parse_packet(packet) -> dict:
    """
    Extract key fields from a captured packet.

    Returns a dict with:
        timestamp  – capture time
        src        – source IP (or 'N/A')
        dst        – destination IP (or 'N/A')
        protocol   – TCP / UDP / ICMP / Other
        length     – packet size in bytes
    """
    info = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "src":       "N/A",
        "dst":       "N/A",
        "protocol":  "Other",
        "length":    len(packet),
    }

    if IP in packet:
        info["src"] = packet[IP].src
        info["dst"] = packet[IP].dst
        # Identify the transport-layer protocol
        if TCP in packet:
            info["protocol"] = "TCP"
        elif UDP in packet:
            info["protocol"] = "UDP"
        elif ICMP in packet:
            info["protocol"] = "ICMP"

    return info


class PacketSniffer:
    """
    Captures packets in bursts inside a background thread.

    Usage:
        sniffer = PacketSniffer()
        sniffer.start()
        ...
        pkts = sniffer.captured_packets  # list of packet info dicts
        ...
        sniffer.stop()
    """

    def __init__(self, on_packet=None):
        """
        Args:
            on_packet: Optional callback(packet_dict) called for each captured packet.
                       Useful for logging or dashboard updates.
        """
        self.captured_packets: list = []
        self.enabled: bool = _scapy_available
        self._on_packet = on_packet
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PacketSniffer")

    def start(self):
        if not self.enabled:
            print("[PacketSniffer] Scapy not available or --no-sniff set. Skipping packet capture.")
            return
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=config.SNIFF_TIMEOUT + 2)

    def _handle_packet(self, packet):
        """Callback handed to scapy.sniff() for each received packet."""
        info = _parse_packet(packet)
        self.captured_packets.append(info)
        # Keep only the last 100 packets to avoid unbounded memory growth
        if len(self.captured_packets) > 100:
            self.captured_packets.pop(0)
        if self._on_packet:
            self._on_packet(info)

    def _run(self):
        """Run repeated sniff bursts until stop() is called."""
        while not self._stop_event.is_set():
            try:
                sniff(
                    prn=self._handle_packet,
                    count=config.SNIFF_PACKET_COUNT,
                    timeout=config.SNIFF_TIMEOUT,
                    store=False,  # Don't store in Scapy's internal list (saves memory)
                )
            except Exception as e:
                # Scapy can raise PermissionError if not running as admin
                print(f"[PacketSniffer] Error: {e}. Make sure you are running as Administrator/root.")
                time.sleep(5)
