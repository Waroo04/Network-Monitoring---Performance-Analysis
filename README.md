# Network Monitoring & Performance Analysis

A modular, beginner-friendly Python tool for real-time network monitoring, performance analysis, bottleneck detection, and data visualization.

---

## 📁 Project Structure

```
Network Monitoring & Performance Analysis/
├── config.py               # ← Edit thresholds & settings here
├── bandwidth_monitor.py    # Upload/Download speed (psutil)
├── ping_monitor.py         # Latency & packet loss (subprocess ping)
├── packet_sniffer.py       # Packet capture (Scapy)
├── bottleneck_detector.py  # Anomaly detection & alerts
├── logger.py               # Thread-safe CSV logging
├── visualizer.py           # Matplotlib graphs
├── dashboard.py            # Live CLI dashboard (rich)
├── main.py                 # Entry point
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Install Python
Make sure you have **Python 3.10+** installed.
```bash
python --version
```

### 2. (Recommended) Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Windows note for Scapy:**  
> Scapy on Windows requires **Npcap** (packet driver).  
> Download and install from: https://npcap.com/#download  
> During install, check **"Install Npcap in WinPcap API-compatible mode"**.

---

## ▶️ Running the Tool

> **Important:** Packet capture (Scapy) requires **Administrator** privileges on Windows or **sudo** on Linux/macOS.

### Option A – Run indefinitely (Ctrl+C to stop)
```bash
# Windows – Run as Administrator:
python main.py

# Linux/macOS:
sudo python main.py
```

### Option B – Run for a fixed duration
```bash
python main.py --duration 120   # stops after 120 seconds
```

### Option C – Disable packet sniffer (no admin needed)
```bash
python main.py --no-sniff
python main.py --no-sniff --duration 60
```

### Option D – Disable the CLI dashboard (plain text output)
```bash
python main.py --no-dashboard
```

### Option E – Generate a performance graph from existing CSV
```bash
python main.py --report
```
This reads `network_log.csv` and saves a graph to `network_report.png`.

---

## 📊 Output Files

| File | Description |
|---|---|
| `network_log.csv` | All measurements: timestamp, speeds, latency, alerts |
| `network_report.png` | Performance graph (created with `--report`) |

### Viewing the CSV
```bash
# Windows PowerShell
Get-Content network_log.csv | Select-Object -First 10

# Linux/macOS
head network_log.csv
```

---

## 🔧 Configuration

Edit **`config.py`** to customise everything:

| Setting | Default | Description |
|---|---|---|
| `PING_TARGETS` | 8.8.8.8, 1.1.1.1, google.com | Hosts to ping |
| `BANDWIDTH_INTERVAL` | 1 s | How often bandwidth is sampled |
| `PING_INTERVAL` | 5 s | How often ping tests run |
| `MIN_DOWNLOAD_MBPS` | 1.0 | Alert threshold – download speed |
| `MIN_UPLOAD_MBPS` | 0.5 | Alert threshold – upload speed |
| `MAX_LATENCY_MS` | 150 | Alert threshold – ping latency |
| `MAX_PACKET_LOSS_PCT` | 10 | Alert threshold – packet loss |

---

## 🚨 Alerts

The tool automatically prints alerts when:
- Download speed drops below `MIN_DOWNLOAD_MBPS`
- Upload speed drops below `MIN_UPLOAD_MBPS`
- Ping latency exceeds `MAX_LATENCY_MS`
- Packet loss exceeds `MAX_PACKET_LOSS_PCT`
- A host is completely unreachable

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| `PermissionError` from Scapy | Run as Administrator / sudo |
| `ModuleNotFoundError: scapy` | `pip install scapy` + install Npcap (Windows) |
| Dashboard looks garbled | Use Windows Terminal or a modern terminal emulator |
| No packets captured | Check Npcap is installed; try `--no-sniff` |
| CSV is empty | Increase `--duration` or check firewall isn't blocking ping |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `psutil` | Bandwidth measurement |
| `scapy` | Packet capture |
| `matplotlib` | Graph generation |
| `rich` | CLI dashboard |

Install all with: `pip install -r requirements.txt`
