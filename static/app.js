const POLL_MS = 2000;   // How often to refresh live data
const MAX_POINTS = 60;     // Max data points on live charts (last 60 samples)

// ── Chart colour palette ───────────────────────────────────────────────────
const COLORS = {
  cyan: '#00d4ff',
  orange: '#ff7b54',
  green: '#39d98a',
  purple: '#9b72f8',
  red: '#ff4d6d',
  blue: '#4f9ef8',
  yellow: '#ffc857',
};

// Protocol → colour mapping for the pie/doughnut chart
const PROTO_COLORS = {
  TCP: COLORS.blue,
  UDP: COLORS.purple,
  ICMP: COLORS.green,
  Other: COLORS.orange,
};

// ── Shared Chart.js defaults (dark theme) ─────────────────────────────────
Chart.defaults.color = '#8891aa';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.display = false;
Chart.defaults.animation.duration = 400;

function gridColor() { return 'rgba(255,255,255,0.06)'; }

// ── Utility: create a time-series line chart ───────────────────────────────
function makeLineChart(canvasId, datasets, yLabel = '', min = undefined) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          ticks: { maxTicksLimit: 8, maxRotation: 0 },
          grid: { color: gridColor() },
        },
        y: {
          title: { display: !!yLabel, text: yLabel, color: '#8891aa' },
          min,
          beginAtZero: min === undefined,
          grid: { color: gridColor() },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(2)}`
          }
        }
      },
    },
  });
}

// ── Utility: push a new value to a live chart, trimming old points ─────────
function pushPoint(chart, label, values) {
  chart.data.labels.push(label);
  if (chart.data.labels.length > MAX_POINTS) chart.data.labels.shift();

  chart.data.datasets.forEach((ds, i) => {
    ds.data.push(values[i] ?? null);
    if (ds.data.length > MAX_POINTS) ds.data.shift();
  });
  chart.update('none');   // 'none' = skip animation for smoother feel
}

// ── Utility: format a timestamp for chart labels ───────────────────────────
function fmtTime(isoStr) {
  if (!isoStr) return '';
  try { return isoStr.split('T')[1] || isoStr; } catch { return isoStr; }
}

// ── Utility: set KPI card state ────────────────────────────────────────────
function setKpi(id, value, unit, state /* 'good'|'warn'|'bad'|'' */) {
  const card = document.getElementById(id);
  card.className = `kpi-card ${state || ''}`;
  card.querySelector('.kpi-value').textContent = value ?? '—';
}

// =============================================================================
// 1. SPARKLINE CHARTS (tiny inline line charts in KPI cards)
// =============================================================================
function makeSparkline(canvasId, color) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [], borderColor: color, borderWidth: 1.5,
        pointRadius: 0, tension: 0.4, fill: false
      }],
    },
    options: {
      responsive: false, maintainAspectRatio: false,
      animation: { duration: 0 },
      scales: { x: { display: false }, y: { display: false } },
      plugins: { tooltip: { enabled: false } },
    },
  });
}

const sparkDownload = makeSparkline('sparkDownload', COLORS.cyan);
const sparkUpload = makeSparkline('sparkUpload', COLORS.orange);

function pushSpark(chart, val) {
  chart.data.labels.push('');
  chart.data.datasets[0].data.push(val);
  if (chart.data.labels.length > 30) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update('none');
}

// =============================================================================
// 2. BANDWIDTH LIVE CHART
// =============================================================================
const bandwidthChart = makeLineChart('bandwidthChart', [
  {
    label: 'Download', data: [], borderColor: COLORS.cyan,
    backgroundColor: 'rgba(0,212,255,0.07)', fill: true, tension: 0.4, pointRadius: 0
  },
  {
    label: 'Upload', data: [], borderColor: COLORS.orange,
    backgroundColor: 'rgba(255,123,84,0.07)', fill: true, tension: 0.4, pointRadius: 0,
    borderDash: [4, 3]
  },
], 'Mbps', 0);

// =============================================================================
// 3. LATENCY LIVE CHART (one dataset per host, added dynamically)
// =============================================================================
const latencyChart = (function () {
  const ctx = document.getElementById('latencyChart').getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { maxTicksLimit: 8, maxRotation: 0 }, grid: { color: gridColor() } },
        y: {
          beginAtZero: true, grid: { color: gridColor() },
          title: { display: true, text: 'ms', color: '#8891aa' }
        },
      },
      plugins: { legend: { display: true, labels: { color: '#8891aa', boxWidth: 12 } } },
    },
  });
})();

const hostColors = [COLORS.green, COLORS.purple, COLORS.yellow, COLORS.red];
const hostDataset = {};   // hostname → dataset index

function ensureHostDataset(host) {
  if (hostDataset[host] !== undefined) return;
  const idx = Object.keys(hostDataset).length;
  const color = hostColors[idx % hostColors.length];
  hostDataset[host] = latencyChart.data.datasets.length;
  latencyChart.data.datasets.push({
    label: host, data: [], borderColor: color,
    pointRadius: 2, tension: 0.4, borderWidth: 1.5,
  });
}

function pushLatency(host, latencyMs, label) {
  ensureHostDataset(host);
  // Sync labels length
  if (!latencyChart.data.labels.includes(label) || latencyChart.data.labels.at(-1) !== label) {
    latencyChart.data.labels.push(label);
    if (latencyChart.data.labels.length > MAX_POINTS) latencyChart.data.labels.shift();
  }
  const ds = latencyChart.data.datasets[hostDataset[host]];
  ds.data.push(latencyMs ?? null);
  if (ds.data.length > MAX_POINTS) ds.data.shift();
  latencyChart.update('none');
}

// =============================================================================
// 4. PACKET LOSS LIVE CHART
// =============================================================================
const lossChart = makeLineChart('lossChart', [
  {
    label: 'Packet Loss %', data: [], borderColor: COLORS.red,
    backgroundColor: 'rgba(255,77,109,0.07)', fill: true, tension: 0.4, pointRadius: 0
  },
], '%', 0);

// =============================================================================
// 5. PROTOCOL DOUGHNUT CHART
// =============================================================================
const protoCounts = { TCP: 0, UDP: 0, ICMP: 0, Other: 0 };

const protocolChart = (function () {
  const ctx = document.getElementById('protocolChart').getContext('2d');
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: Object.keys(protoCounts),
      datasets: [{
        data: Object.values(protoCounts),
        backgroundColor: Object.keys(protoCounts).map(p => PROTO_COLORS[p] || COLORS.blue),
        borderWidth: 2, borderColor: '#11112a', hoverOffset: 6,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}` } },
      },
    },
  });
})();

// Render the custom legend below the pie chart
function updatePieLegend() {
  const legend = document.getElementById('pieLegend');
  legend.innerHTML = Object.keys(protoCounts).map(p => {
    const c = PROTO_COLORS[p] || COLORS.blue;
    return `<div class="pie-legend-item">
      <div class="pie-dot" style="background:${c}"></div>${p}: ${protoCounts[p]}
    </div>`;
  }).join('');
}

function updateProtocolChart(packets) {
  packets.forEach(pkt => {
    const proto = pkt.protocol || 'Other';
    if (protoCounts[proto] !== undefined) protoCounts[proto]++;
    else protoCounts.Other++;
  });
  protocolChart.data.datasets[0].data = Object.values(protoCounts);
  protocolChart.update('none');
  updatePieLegend();
}

// =============================================================================
// 6. ALERT BANNER + ALERT FEED
// =============================================================================
let seenAlerts = new Set();

function renderAlerts(alerts) {
  const feed = document.getElementById('alertFeed');
  const banner = document.getElementById('alertBanner');
  const badge = document.getElementById('alertCount');

  const newAlerts = alerts.filter(a => !seenAlerts.has(a.time + a.message));
  newAlerts.forEach(a => seenAlerts.add(a.time + a.message));

  if (alerts.length === 0) {
    feed.innerHTML = '<li class="feed-empty">No alerts yet — network looks healthy ✅</li>';
    banner.classList.add('hidden');
    badge.textContent = '0';
    return;
  }

  badge.textContent = alerts.length;

  // Prepend new alerts to feed
  newAlerts.reverse().forEach(a => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="alert-time">${a.time}</span>
                    <span class="alert-msg">${a.message}</span>`;
    feed.insertBefore(li, feed.firstChild);
  });

  // Remove "no alerts" placeholder
  const empty = feed.querySelector('.feed-empty');
  if (empty) empty.remove();

  // Show banner with the latest alert
  banner.classList.remove('hidden');
  banner.textContent = '🚨 ' + alerts.at(-1)?.message;
}

// =============================================================================
// 7. PACKET FEED
// =============================================================================
let renderedPacketCount = 0;

function renderPackets(packets) {
  const feed = document.getElementById('packetFeed');
  const newPkts = packets.slice(renderedPacketCount);
  renderedPacketCount = packets.length;

  if (packets.length === 0) {
    feed.innerHTML = '<li class="feed-empty">Waiting for packets… (requires Npcap + admin)</li>';
    return;
  }

  // Remove placeholder
  const empty = feed.querySelector('.feed-empty');
  if (empty) empty.remove();

  newPkts.reverse().forEach(pkt => {
    const li = document.createElement('li');
    const proto = pkt.protocol || 'Other';
    li.innerHTML = `
      <span class="pkt-tag">${proto}</span>
      <div class="pkt-info">
        <span class="pkt-route">${pkt.src || '?'} → ${pkt.dst || '?'}</span>
        <span class="pkt-meta">${pkt.length || '?'} bytes &nbsp;·&nbsp; ${pkt.timestamp || ''}</span>
      </div>`;
    feed.insertBefore(li, feed.firstChild);
    // Keep max 20 items in DOM
    if (feed.children.length > 20) feed.lastChild.remove();
  });

  updateProtocolChart(newPkts);
}

// =============================================================================
// 8. PING TABLE
// =============================================================================
function renderPingTable(pings) {
  const tbody = document.getElementById('pingTableBody');
  if (!pings || pings.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-row">Waiting for ping data…</td></tr>';
    return;
  }

  tbody.innerHTML = pings.map(p => {
    const lat = p.latency_ms;
    const loss = p.packet_loss_pct ?? 0;
    let statusClass = 'status-ok', statusText = 'OK';

    if (lat === null || lat === undefined) {
      statusClass = 'status-bad'; statusText = 'Unreachable';
    } else if (lat > 150 || loss > 10) {
      statusClass = 'status-warn'; statusText = 'Degraded';
    }

    return `<tr>
      <td>${p.host || '?'}</td>
      <td>${lat !== null && lat !== undefined ? lat.toFixed(1) + ' ms' : 'Timeout'}</td>
      <td>${loss.toFixed(0)}%</td>
      <td class="${statusClass}">${statusText}</td>
    </tr>`;
  }).join('');
}

// =============================================================================
// 9. STATUS POLL LOOP
// =============================================================================
let connected = false;

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const bw = data.bandwidth || {};
    const ts = fmtTime(bw.timestamp);
    const now = new Date().toLocaleTimeString();

    // Connection badge
    if (!connected) {
      connected = true;
      const badge = document.getElementById('connectionBadge');
      badge.classList.remove('error');
      document.getElementById('connectionText').textContent = 'Live';
    }

    // ── KPI cards ──
    const dl = bw.download_mbps ?? 0;
    const ul = bw.upload_mbps ?? 0;
    const pings = data.pings || [];
    const validLats = pings.map(p => p.latency_ms).filter(v => v !== null && v !== undefined);
    const validLoss = pings.map(p => p.packet_loss_pct ?? 0);
    const avgLat = validLats.length ? (validLats.reduce((a, b) => a + b, 0) / validLats.length) : null;
    const avgLoss = validLoss.length ? (validLoss.reduce((a, b) => a + b, 0) / validLoss.length) : 0;

    setKpi('kpiDownload', dl.toFixed(2), 'Mbps', dl >= 1.0 ? 'good' : dl > 0 ? 'warn' : 'bad');
    setKpi('kpiUpload', ul.toFixed(2), 'Mbps', ul >= 0.5 ? 'good' : ul > 0 ? 'warn' : 'bad');
    setKpi('kpiLatency', avgLat !== null ? avgLat.toFixed(1) : '—', 'ms',
      avgLat === null ? '' : avgLat <= 80 ? 'good' : avgLat <= 150 ? 'warn' : 'bad');
    setKpi('kpiPacketLoss', avgLoss.toFixed(1), '%',
      avgLoss === 0 ? 'good' : avgLoss <= 10 ? 'warn' : 'bad');

    // ── Uptime & last update ──
    document.getElementById('uptime').textContent = data.uptime || '—';
    document.getElementById('lastUpdate').textContent = now;

    // ── Sparklines ──
    pushSpark(sparkDownload, dl);
    pushSpark(sparkUpload, ul);

    // ── Bandwidth line chart ──
    pushPoint(bandwidthChart, ts, [dl, ul]);

    // ── Latency chart (one line per host) ──
    pings.forEach(p => pushLatency(p.host, p.latency_ms, ts));

    // ── Packet loss chart (average across hosts) ──
    pushPoint(lossChart, ts, [avgLoss]);

    // ── Ping table ──
    renderPingTable(pings);

    // ── Alerts ──
    renderAlerts(data.alerts || []);

    // ── Packet feed ──
    renderPackets(data.packets || []);

  } catch (err) {
    console.error('Poll error:', err);
    if (connected) {
      connected = false;
      const badge = document.getElementById('connectionBadge');
      badge.classList.add('error');
      document.getElementById('connectionText').textContent = 'Disconnected';
    }
  }
}

// =============================================================================
// 10. HISTORICAL DATA CHART
// =============================================================================
let historyChart = null;

async function loadHistory(limit) {
  // Highlight active button
  document.querySelectorAll('.history-controls .btn').forEach(b => b.classList.remove('active'));
  event?.target?.classList.add('active');

  const url = limit ? `/api/history?limit=${limit}` : '/api/history';
  const res = await fetch(url);
  const data = await res.json();
  const rows = data.rows || [];

  const labels = rows.map(r => fmtTime(r.timestamp));
  const download = rows.map(r => parseFloat(r.download_mbps) || 0);
  const upload = rows.map(r => parseFloat(r.upload_mbps) || 0);

  if (historyChart) {
    historyChart.data.labels = labels;
    historyChart.data.datasets[0].data = download;
    historyChart.data.datasets[1].data = upload;
    historyChart.update();
    return;
  }

  const ctx = document.getElementById('historyChart').getContext('2d');
  historyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Download (Mbps)', data: download,
          borderColor: COLORS.cyan, backgroundColor: 'rgba(0,212,255,0.06)',
          fill: true, tension: 0.3, pointRadius: 0, borderWidth: 1.5
        },
        {
          label: 'Upload (Mbps)', data: upload,
          borderColor: COLORS.orange, backgroundColor: 'rgba(255,123,84,0.06)',
          fill: true, tension: 0.3, pointRadius: 0, borderWidth: 1.5, borderDash: [4, 3]
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { maxTicksLimit: 12, maxRotation: 0 }, grid: { color: gridColor() } },
        y: {
          beginAtZero: true, grid: { color: gridColor() },
          title: { display: true, text: 'Mbps', color: '#8891aa' }
        },
      },
      plugins: {
        legend: { display: true, labels: { color: '#8891aa', boxWidth: 12 } },
      },
    },
  });
}

// =============================================================================
// 11. BOOT
// =============================================================================
(function init() {
  updatePieLegend();         // Draw empty pie legend
  loadHistory(200);          // Pre-load history chart

  pollStatus();              // First poll immediately
  setInterval(pollStatus, POLL_MS);
})();
