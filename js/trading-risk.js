(() => {
  'use strict';

  const panel = document.getElementById('risk-panel');
  if (!panel) return;
  const shell = document.getElementById('risk-content');
  const source = panel.dataset.url || '/trading/risk-ytd.json';
  let loaded = false;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
  const parseDay = iso => Date.parse(`${iso}T12:00:00Z`);
  const shortDay = iso => {
    const day = new Date(`${iso}T12:00:00Z`);
    return day.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  };
  const longDay = iso => {
    const day = new Date(`${iso}T12:00:00Z`);
    return day.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  };
  const fixed = (value, places = 2) => Number(value).toFixed(places);
  const signed = (value, places = 2) => `${Number(value) >= 0 ? '+' : '−'}${Math.abs(Number(value)).toFixed(places)}`;
  const regimeClass = label => `risk-${String(label).toLowerCase()}`;

  function metricCard(label, value, band, asOf, suffix = '') {
    return `<div class="risk-metric">
      <strong>${esc(value)}${esc(suffix)}</strong>
      <span>${esc(label)} · <span class="${regimeClass(band === 'High' || band === 'Elevated' || band === 'Backwardation' ? 'Elevated' : band === 'Moderate' || band === 'Flattening' ? 'Watchful' : 'Contained')}">${esc(band)}</span></span>
      <small>Close · ${esc(shortDay(asOf))}</small>
    </div>`;
  }

  function normalizeSeries(rows, key = 'value') {
    return (rows || []).map(row => ({ date: row.date, value: Number(row[key]) })).filter(row => Number.isFinite(row.value));
  }

  function linePanel({ name, series, current, band, domain, zones = [], thresholds = [], windows = [], accent = false, zero = false, asOf }) {
    const W = 720, H = 82, left = 3, right = 717, top = 3, bottom = 79;
    const start = parseDay(`${asOf.slice(0, 4)}-01-01`), end = parseDay(asOf);
    const [low, high] = domain;
    const x = iso => left + (parseDay(iso) - start) / Math.max(1, end - start) * (right - left);
    const y = value => bottom - (value - low) / Math.max(.0001, high - low) * (bottom - top);
    const clampY = value => Math.max(top, Math.min(bottom, y(value)));
    const zoneMarkup = zones.map(zone => {
      const y1 = clampY(zone.to), y2 = clampY(zone.from);
      return `<rect class="${esc(zone.className)}" x="${left}" y="${Math.min(y1, y2).toFixed(2)}" width="${right - left}" height="${Math.abs(y2 - y1).toFixed(2)}"/>`;
    }).join('');
    const windowMarkup = windows.map(window => {
      const x1 = Math.max(left, x(window.start));
      const x2 = Math.min(right, x(window.end) + 4);
      return x2 > x1 ? `<rect class="risk-spike" x="${x1.toFixed(2)}" y="${top}" width="${(x2 - x1).toFixed(2)}" height="${bottom - top}"/>` : '';
    }).join('');
    const thresholdMarkup = thresholds.filter(value => value >= low && value <= high).map(value =>
      `<line class="risk-threshold" x1="${left}" y1="${y(value).toFixed(2)}" x2="${right}" y2="${y(value).toFixed(2)}"/>`
    ).join('');
    const zeroMarkup = zero && low < 0 && high > 0 ? `<line class="risk-zero" x1="${left}" y1="${y(0).toFixed(2)}" x2="${right}" y2="${y(0).toFixed(2)}"/>` : '';
    const points = series.filter(row => parseDay(row.date) <= end).map(row => `${x(row.date).toFixed(2)},${clampY(row.value).toFixed(2)}`).join(' ');
    const last = series[series.length - 1];
    const lastX = last ? x(last.date) : right;
    const lastY = last ? clampY(last.value) : bottom;
    const values = series.map(row => row.value);
    const min = Math.min(...values), max = Math.max(...values);
    return `<div class="risk-line-panel">
      <div class="risk-line-head"><span class="risk-line-name">${esc(name)}</span><span class="risk-line-now ${regimeClass(band === 'High' || band === 'Elevated' || band === 'Backwardation' ? 'Elevated' : band === 'Moderate' || band === 'Flattening' ? 'Watchful' : 'Contained')}">${esc(current)} · ${esc(band)}</span></div>
      <svg class="risk-chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(name)} YTD, current ${current}, low ${fixed(min, 2)}, high ${fixed(max, 2)}">
        ${zoneMarkup}${windowMarkup}${thresholdMarkup}${zeroMarkup}
        <polyline class="risk-line ${accent ? 'risk-line-accent' : ''}" points="${points}"/>
        <circle class="risk-dot ${accent ? 'risk-dot-accent' : ''}" cx="${lastX.toFixed(2)}" cy="${lastY.toFixed(2)}" r="3"/>
      </svg>
      <div class="risk-axis-footer"><span>Jan 1</span><span>range ${fixed(min, 1)}–${fixed(max, 1)}</span><span>${esc(shortDay(asOf))}</span></div>
    </div>`;
  }

  function dynamicDomain(series, floor, ceiling, padding = .08) {
    const values = series.map(row => row.value);
    const min = Math.min(floor, ...values), max = Math.max(ceiling, ...values);
    const spread = Math.max(1, max - min);
    return [min - spread * padding, max + spread * padding];
  }

  function curveFigure(curve) {
    const W = 720, H = 160, left = 12, right = 708, top = 12, bottom = 148;
    const values = curve.map(row => Number(row.value));
    const min = Math.min(...values), max = Math.max(...values), pad = Math.max(.6, (max - min) * .18);
    const low = min - pad, high = max + pad;
    const x = index => left + index / Math.max(1, curve.length - 1) * (right - left);
    const y = value => bottom - (value - low) / (high - low) * (bottom - top);
    const points = curve.map((row, index) => `${x(index).toFixed(2)},${y(Number(row.value)).toFixed(2)}`).join(' ');
    const dots = curve.map((row, index) => `<circle class="${index === 0 ? 'risk-dot' : 'risk-dot-accent'}" cx="${x(index).toFixed(2)}" cy="${y(Number(row.value)).toFixed(2)}" r="4"/>`).join('');
    return `<svg class="risk-chart-svg risk-curve-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Current VIX curve from spot ${fixed(values[0])} through M6 ${fixed(values[values.length - 1])}">
      <polyline class="risk-line risk-line-accent" points="${points}"/>${dots}
    </svg>
    <div class="risk-curve-labels">${curve.map(row => `<div class="risk-curve-label"><b>${esc(row.label)} · ${fixed(row.value, 2)}</b><span>${row.expiration ? esc(shortDay(row.expiration)) : 'cash index'}</span></div>`).join('')}</div>`;
  }

  function scoreBody(score) {
    const labels = { vvix: 'VVIX', curve: 'Curve', move: 'MOVE', skew: 'SKEW' };
    const order = ['vvix', 'curve', 'move', 'skew'];
    const components = order.map(name => [name, score.components[name]]).filter(([, row]) => row).map(([name, row]) => {
      const percent = Number(row.maximum) ? Number(row.points) / Number(row.maximum) * 100 : 0;
      return `<div class="risk-component">
        <div class="risk-component-head"><span>${esc(labels[name] || name)}</span><b>${esc(row.points)} / ${esc(row.maximum)}</b></div>
        <div class="risk-component-track"><span class="risk-component-fill" style="width:${percent.toFixed(1)}%"></span></div>
      </div>`;
    }).join('');
    return `<div class="risk-score-body">
      <div class="risk-score-large ${regimeClass(score.label)}"><b>${esc(score.total)}</b><span>${esc(score.label)}</span></div>
      <div class="risk-components">${components}</div>
      <details class="risk-rules"><summary>Score rules</summary><ul>${score.rules.map(rule => `<li>${esc(rule)}</li>`).join('')}</ul></details>
    </div>`;
  }

  function render(payload) {
    const c = payload.current, dates = c.dates;
    const vix = normalizeSeries(payload.series.vix);
    const vvix = normalizeSeries(payload.series.vvix);
    const move = normalizeSeries(payload.series.move);
    const skew = normalizeSeries(payload.series.skew);
    const spread = normalizeSeries(payload.series.curve_spread, 'spread');
    const asOf = payload.as_of;
    const maxVix = Math.max(...vix.map(row => row.value));
    const maxVvix = Math.max(...vvix.map(row => row.value));
    const maxMove = Math.max(...move.map(row => row.value));
    const maxSkew = Math.max(...skew.map(row => row.value));
    const maxSpread = Math.max(...spread.map(row => row.value));
    const minSpread = Math.min(...spread.map(row => row.value));

    const mainPanels = [
      linePanel({ name: 'VIX · current equity volatility', series: vix, current: fixed(c.vix), band: c.bands.vix, domain: dynamicDomain(vix, 10, Math.max(30, maxVix)), zones: [
        { from: 0, to: 15, className: 'risk-zone-calm' }, { from: 15, to: 25, className: 'risk-zone-watch' }, { from: 25, to: 100, className: 'risk-zone-high' },
      ], thresholds: [15, 20, 25], windows: payload.windows.vix_spikes, accent: true, asOf }),
      linePanel({ name: 'VVIX · volatility of VIX', series: vvix, current: fixed(c.vvix), band: c.bands.vvix, domain: dynamicDomain(vvix, 70, Math.max(125, maxVvix)), zones: [
        { from: 0, to: 90, className: 'risk-zone-calm' }, { from: 90, to: 110, className: 'risk-zone-watch' }, { from: 110, to: 300, className: 'risk-zone-high' },
      ], thresholds: [90, 110], windows: payload.windows.vix_spikes, asOf }),
      linePanel({ name: 'VIX curve · M2 − M1', series: spread, current: signed(c.curve_spread), band: c.curve_band, domain: [Math.min(-1.5, minSpread - .3), Math.max(1.5, maxSpread + .3)], zones: [
        { from: -20, to: 0, className: 'risk-zone-high' }, { from: 0, to: .5, className: 'risk-zone-watch' }, { from: .5, to: 20, className: 'risk-zone-calm' },
      ], thresholds: [0, .5], windows: payload.windows.vix_spikes, zero: true, asOf }),
      linePanel({ name: 'MOVE · Treasury volatility', series: move, current: fixed(c.move), band: c.bands.move, domain: dynamicDomain(move, 55, Math.max(110, maxMove)), zones: [
        { from: 0, to: 80, className: 'risk-zone-calm' }, { from: 80, to: 100, className: 'risk-zone-watch' }, { from: 100, to: 300, className: 'risk-zone-high' },
      ], thresholds: [80, 100], windows: payload.windows.vix_spikes, asOf }),
      linePanel({ name: 'SKEW · priced tail risk', series: skew, current: fixed(c.skew), band: c.bands.skew, domain: dynamicDomain(skew, 115, Math.max(155, maxSkew)), zones: [
        { from: 0, to: 130, className: 'risk-zone-calm' }, { from: 130, to: 145, className: 'risk-zone-watch' }, { from: 145, to: 300, className: 'risk-zone-high' },
      ], thresholds: [130, 145], windows: payload.windows.vix_spikes, asOf }),
    ].join('');

    const vvixFocus = [
      linePanel({ name: 'VVIX with >110 expansion-risk periods', series: vvix, current: fixed(c.vvix), band: c.bands.vvix, domain: dynamicDomain(vvix, 70, Math.max(125, maxVvix)), zones: [
        { from: 0, to: 90, className: 'risk-zone-calm' }, { from: 90, to: 110, className: 'risk-zone-watch' }, { from: 110, to: 300, className: 'risk-zone-high' },
      ], thresholds: [90, 110], windows: payload.windows.vvix_high, accent: true, asOf }),
      linePanel({ name: 'VIX follow-through', series: vix, current: fixed(c.vix), band: c.bands.vix, domain: dynamicDomain(vix, 10, Math.max(30, maxVix)), thresholds: [15, 20, 25], windows: payload.windows.vvix_high, asOf }),
    ].join('');

    const spreadPanel = linePanel({ name: 'Historical M2 − M1 spread', series: spread, current: signed(c.curve_spread), band: c.curve_band, domain: [Math.min(-1.5, minSpread - .3), Math.max(1.5, maxSpread + .3)], zones: [
      { from: -20, to: 0, className: 'risk-zone-high' }, { from: 0, to: .5, className: 'risk-zone-watch' }, { from: .5, to: 20, className: 'risk-zone-calm' },
    ], thresholds: [0, .5], zero: true, asOf });

    const moveLag = dates.move === asOf ? '' : ` · MOVE latest available ${shortDay(dates.move)}`;
    shell.innerHTML = `<div class="risk-shell">
      <div class="risk-header">
        <div><h2>Forward Market Riskiness</h2><p>Leading and confirming signals for elevated equity risk over the next 1–2 months. YTD closes; descriptive, not a trading signal.</p></div>
        <div class="risk-updated">Last updated<br>${esc(longDay(asOf))}${esc(moveLag)}</div>
      </div>
      <div class="risk-summary" aria-label="Current market risk readings">
        <div class="risk-score-card"><div class="risk-score-top"><span class="risk-score-number ${regimeClass(payload.score.label)}">${esc(payload.score.total)}</span><span class="risk-score-denom">/ 100</span></div><strong class="risk-regime ${regimeClass(payload.score.label)}">${esc(payload.score.label)}</strong><small>Forward conditions score</small></div>
        ${metricCard('VIX', fixed(c.vix), c.bands.vix, dates.vix)}
        ${metricCard('VVIX', fixed(c.vvix), c.bands.vvix, dates.vvix)}
        ${metricCard('Curve', signed(c.curve_spread), c.curve_band, c.curve_as_of)}
        ${metricCard('MOVE', fixed(c.move), c.bands.move, dates.move)}
        ${metricCard('SKEW', fixed(c.skew), c.bands.skew, dates.skew)}
      </div>
      <ul class="risk-commentary">${payload.commentary.map(line => `<li>${esc(line)}</li>`).join('')}</ul>
      <div class="risk-grid">
        <section class="risk-card risk-card--wide" aria-labelledby="risk-main-heading"><div class="risk-card-head"><div><h3 id="risk-main-heading">YTD risk stack</h3><p>Aligned small multiples; red shading marks VIX ≥25 periods.</p></div><time datetime="${esc(asOf)}">Updated ${esc(shortDay(asOf))}</time></div><div class="risk-stack">${mainPanels}</div><p class="risk-spike-key">Historical VIX ≥25 context</p></section>
        <section class="risk-card" aria-labelledby="risk-vvix-heading"><div class="risk-card-head"><div><h3 id="risk-vvix-heading">VVIX focus</h3><p>High VVIX can lead large VIX moves; it does not guarantee one.</p></div><time datetime="${esc(asOf)}">Updated ${esc(shortDay(asOf))}</time></div><div class="risk-stack">${vvixFocus}</div><p class="risk-spike-key">VVIX &gt;110 periods, aligned across both panels</p></section>
        <section class="risk-card" aria-labelledby="risk-curve-heading"><div class="risk-card-head"><div><h3 id="risk-curve-heading">Term structure monitor</h3><p>Spot through M6 plus the historical front spread.</p></div><time datetime="${esc(c.curve_as_of)}">Updated ${esc(shortDay(c.curve_as_of))}</time></div><div class="risk-curve-body">${curveFigure(payload.curve)}<div class="risk-traffic ${regimeClass(c.curve_band === 'Backwardation' ? 'Elevated' : c.curve_band === 'Flattening' ? 'Watchful' : 'Contained')}"><span class="risk-traffic-dot" aria-hidden="true"></span><strong>${esc(c.curve_band)}</strong><span>M2−M1 ${esc(signed(c.curve_spread))} points (${esc(signed(c.curve_spread_percent))}%)</span></div>${spreadPanel}</div></section>
        <section class="risk-card risk-card--wide" aria-labelledby="risk-score-heading"><div class="risk-card-head"><div><h3 id="risk-score-heading">Combined forward risk score</h3><p>Transparent 0–100 threshold score; not a calibrated probability.</p></div><time datetime="${esc(asOf)}">Updated ${esc(shortDay(asOf))}</time></div>${scoreBody(payload.score)}</section>
      </div>
      <p class="risk-method">${esc(payload.method)} HY OAS: ${c.hy_oas == null ? 'unavailable' : `${fixed(c.hy_oas)}% as of ${shortDay(c.hy_oas_as_of)}`}. Sources: <a href="https://finance.yahoo.com/quote/%5EVIX/" rel="noopener" target="_blank">Yahoo Finance</a>, <a href="https://www.cboe.com/markets/us/futures/market-statistics/settlement/futures/daily/" rel="noopener" target="_blank">Cboe</a>, and <a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2" rel="noopener" target="_blank">FRED</a>.</p>
    </div>`;
  }

  async function load() {
    if (loaded) return;
    loaded = true;
    try {
      const response = await fetch(source, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`Risk data HTTP ${response.status}`);
      const payload = await response.json();
      if (payload.schema_version !== 1 || !payload.current || !payload.score || !payload.series || !payload.curve) throw new Error('Risk data contract is incomplete');
      render(payload);
    } catch (error) {
      loaded = false;
      console.error('Unable to load risk dashboard', error);
      shell.innerHTML = '<p class="risk-error">Risk dashboard data failed to load. Try refreshing this tab.</p>';
    }
  }

  panel.addEventListener('panelactivate', load);
  if (!panel.hidden) load();
})();
