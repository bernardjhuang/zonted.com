(() => {
  'use strict';

  const panel = document.getElementById('risk-panel');
  if (!panel) return;
  const shell = document.getElementById('risk-content');
  const source = panel.dataset.url || '/trading/risk-ytd.json';
  let loaded = false;
  let chartSequence = 0;
  let sharedTooltipSeries = [];
  const chartRegistry = new Map();

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
  const parseDay = iso => Date.parse(`${iso}T12:00:00Z`);
  const shortDay = iso => new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  const longDay = iso => new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  const fixed = (value, places = 2) => Number(value).toFixed(places);
  const signed = (value, places = 2) => `${Number(value) >= 0 ? '+' : '−'}${Math.abs(Number(value)).toFixed(places)}`;
  const regimeClass = label => `risk-${String(label).toLowerCase()}`;
  const trendGlyph = direction => ({ improving: '↓', deteriorating: '↑', stable: '→', mixed: '↔', unavailable: '—' }[direction] || '—');
  const toneForBand = band => band === 'High' || band === 'Elevated' || band === 'Backwardation' ? 'Elevated' : band === 'Moderate' || band === 'Flattening' || band === 'Watchful' ? 'Watchful' : 'Contained';

  function metricCard(label, value, band, meta, suffix = '') {
    const stale = Boolean(meta?.stale);
    const percentile = Number.isFinite(Number(meta?.percentile)) ? `P${Math.round(Number(meta.percentile))}` : 'percentile n/a';
    const changes = `${trendGlyph(meta?.direction)} Δ5 ${meta?.change_5d == null ? '—' : signed(meta.change_5d)} · Δ20 ${meta?.change_20d == null ? '—' : signed(meta.change_20d)}`;
    return `<div class="risk-metric${stale ? ' risk-metric--stale' : ''}">
      <strong>${esc(value)}${esc(suffix)}</strong>
      <span>${esc(label)} · <span class="${regimeClass(toneForBand(band))}">${esc(band)}</span></span>
      <small>${esc(percentile)} · ${esc(changes)}</small>
      <small>${stale ? `STALE · ${meta.age_sessions} sessions · zero weight` : `Close · ${shortDay(meta.source_date)}`}</small>
    </div>`;
  }

  function normalizeSeries(rows, key = 'value') {
    return (rows || []).map(row => ({ date: row.date, value: Number(row[key]) })).filter(row => Number.isFinite(row.value));
  }

  const tooltipMetric = (key, label, series, places = 2, suffix = '', useSign = false) => ({ key, label, series, places, suffix, useSign });
  const tooltipValue = (metric, value) => `${metric.useSign ? signed(value, metric.places) : fixed(value, metric.places)}${metric.suffix}`;

  function nearestPoint(points, chartX) {
    let low = 0, high = points.length - 1;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (points[middle].x < chartX) low = middle + 1;
      else high = middle;
    }
    if (low > 0 && Math.abs(points[low - 1].x - chartX) <= Math.abs(points[low].x - chartX)) return low - 1;
    return low;
  }

  function bindChartInteractions() {
    shell.querySelectorAll('.risk-chart-svg[data-chart-id]').forEach(svg => {
      const chart = chartRegistry.get(svg.dataset.chartId);
      const host = svg.closest('.risk-chart-interactive') || svg.closest('.risk-line-panel');
      const tooltip = host?.querySelector('.risk-chart-tooltip');
      const marker = svg.querySelector('.risk-hover-marker');
      if (!chart || !tooltip || !marker || !chart.points.length) return;
      let selected = chart.points.length - 1;

      const hide = () => {
        marker.classList.remove('is-active');
        tooltip.hidden = true;
      };
      const show = index => {
        selected = Math.max(0, Math.min(chart.points.length - 1, index));
        const point = chart.points[selected];
        marker.querySelector('line').setAttribute('x1', point.x);
        marker.querySelector('line').setAttribute('x2', point.x);
        marker.querySelector('circle').setAttribute('cx', point.x);
        marker.querySelector('circle').setAttribute('cy', point.y);
        marker.classList.add('is-active');

        const rows = chart.metrics.map(metric => {
          const value = metric.values.get(point.date);
          return Number.isFinite(value) ? `<div><span>${esc(metric.label)}</span><b>${esc(tooltipValue(metric, value))}</b></div>` : '';
        }).filter(Boolean).join('');
        tooltip.innerHTML = `<time datetime="${esc(point.date)}">${esc(point.title || longDay(point.date))}</time>${rows}`;
        tooltip.hidden = false;
        const svgRect = svg.getBoundingClientRect();
        const desired = svgRect.left + point.x / chart.width * svgRect.width;
        const half = tooltip.offsetWidth / 2;
        tooltip.style.left = `${Math.max(half + 8, Math.min(window.innerWidth - half - 8, desired))}px`;
        tooltip.style.top = `${Math.max(8, Math.min(window.innerHeight - tooltip.offsetHeight - 8, svgRect.top + 8))}px`;
        svg.setAttribute('aria-label', `${chart.name}. ${tooltip.innerText.replaceAll('\n', ', ')}`);
      };
      const showFromPointer = event => {
        const rect = svg.getBoundingClientRect();
        const chartX = Math.max(0, Math.min(chart.width, (event.clientX - rect.left) / Math.max(1, rect.width) * chart.width));
        show(nearestPoint(chart.points, chartX));
      };

      svg.addEventListener('pointerenter', showFromPointer);
      svg.addEventListener('pointermove', showFromPointer);
      svg.addEventListener('pointerdown', event => { svg.focus(); showFromPointer(event); });
      svg.addEventListener('pointerleave', () => { if (document.activeElement !== svg) hide(); });
      svg.addEventListener('focus', () => show(selected));
      svg.addEventListener('blur', hide);
      svg.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End', 'Escape'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'Escape') return hide();
        if (event.key === 'Home') selected = 0;
        else if (event.key === 'End') selected = chart.points.length - 1;
        else selected += event.key === 'ArrowLeft' ? -1 : 1;
        show(selected);
      });
    });
  }

  function linePanel({ name, series, current, band = '', domain, zones = [], thresholds = [], windows = [], accent = false, zero = false, asOf, startDate = null, startLabel = null, metric = null, tooltipSeries = sharedTooltipSeries }) {
    const W = 720, H = 82, left = 3, right = 717, top = 3, bottom = 79;
    const startIso = startDate || `${asOf.slice(0, 4)}-01-01`;
    const start = parseDay(startIso), end = parseDay(asOf);
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
    const visible = series.filter(row => parseDay(row.date) >= start && parseDay(row.date) <= end);
    const points = visible.map(row => `${x(row.date).toFixed(2)},${clampY(row.value).toFixed(2)}`).join(' ');
    const last = visible[visible.length - 1];
    const values = visible.map(row => row.value);
    const min = Math.min(...values), max = Math.max(...values);
    const tone = ['Contained', 'Watchful', 'Elevated', 'High', 'Moderate', 'Backwardation', 'Flattening'].includes(band) ? regimeClass(toneForBand(band)) : '';
    const chartId = `risk-chart-${++chartSequence}`;
    const primary = metric || tooltipSeries.find(row => row.series === series) || tooltipMetric(name, name.split(' · ')[0], series);
    const metrics = [primary, ...tooltipSeries.filter(row => row.key !== primary.key)].map(row => row.values ? row : ({
      ...row,
      values: new Map(row.series.map(point => [point.date, point.value])),
    }));
    chartRegistry.set(chartId, {
      name,
      width: W,
      points: visible.map(row => ({ date: row.date, value: row.value, x: x(row.date), y: clampY(row.value) })),
      metrics,
    });
    return `<div class="risk-line-panel">
      <div class="risk-line-head"><span class="risk-line-name">${esc(name)}</span><span class="risk-line-now ${tone}">${esc(current)}${band ? ` · ${esc(band)}` : ''}</span></div>
      <svg class="risk-chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" tabindex="0" data-chart-id="${chartId}" aria-label="${esc(name)}, current ${current}, low ${fixed(min, 2)}, high ${fixed(max, 2)}. Hover or focus for date values.">
        ${zoneMarkup}${windowMarkup}${thresholdMarkup}${zeroMarkup}
        <polyline class="risk-line ${accent ? 'risk-line-accent' : ''}" points="${points}"/>
        ${last ? `<circle class="risk-dot ${accent ? 'risk-dot-accent' : ''}" cx="${x(last.date).toFixed(2)}" cy="${clampY(last.value).toFixed(2)}" r="3"/>` : ''}
        <g class="risk-hover-marker" aria-hidden="true"><line y1="${top}" y2="${bottom}"/><circle r="3.5"/></g>
      </svg>
      <div class="risk-chart-tooltip" role="status" aria-live="polite" hidden></div>
      <div class="risk-axis-footer"><span>${esc(startLabel || shortDay(startIso))}</span><span>range ${fixed(min, 1)}–${fixed(max, 1)}</span><span>${esc(shortDay(asOf))}</span></div>
    </div>`;
  }

  function dynamicDomain(series, floor, ceiling, padding = .08) {
    const values = series.map(row => row.value);
    const min = Math.min(floor, ...values), max = Math.max(ceiling, ...values);
    const spread = Math.max(.01, max - min);
    return [min - spread * padding, max + spread * padding];
  }

  function curveFigure(curve, asOf) {
    const W = 720, H = 160, left = 12, right = 708, top = 12, bottom = 148;
    const values = curve.map(row => Number(row.value));
    const min = Math.min(...values), max = Math.max(...values), pad = Math.max(.6, (max - min) * .18);
    const low = min - pad, high = max + pad;
    const x = index => left + index / Math.max(1, curve.length - 1) * (right - left);
    const y = value => bottom - (value - low) / (high - low) * (bottom - top);
    const points = curve.map((row, index) => `${x(index).toFixed(2)},${y(Number(row.value)).toFixed(2)}`).join(' ');
    const dots = curve.map((row, index) => `<circle class="${index === 0 ? 'risk-dot' : 'risk-dot-accent'}" cx="${x(index).toFixed(2)}" cy="${y(Number(row.value)).toFixed(2)}" r="4"/>`).join('');
    const chartId = `risk-chart-${++chartSequence}`;
    const curvePoints = curve.map((row, index) => ({
      date: row.expiration || asOf,
      title: row.expiration ? `${row.label} expires ${longDay(row.expiration)}` : `${row.label} · ${longDay(asOf)}`,
      value: Number(row.value),
      x: x(index),
      y: y(Number(row.value)),
    }));
    chartRegistry.set(chartId, {
      name: 'Current VIX curve',
      width: W,
      points: curvePoints,
      metrics: [{ ...tooltipMetric('curve-point', 'VIX level', [], 2), values: new Map(curvePoints.map(row => [row.date, row.value])) }],
    });
    return `<div class="risk-chart-interactive"><svg class="risk-chart-svg risk-curve-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" tabindex="0" data-chart-id="${chartId}" aria-label="Current VIX curve from spot ${fixed(values[0])} through M6 ${fixed(values[values.length - 1])}. Hover or focus for contract values.">
      <polyline class="risk-line risk-line-accent" points="${points}"/>${dots}
      <g class="risk-hover-marker" aria-hidden="true"><line y1="${top}" y2="${bottom}"/><circle r="4.5"/></g>
    </svg><div class="risk-chart-tooltip" role="status" aria-live="polite" hidden></div></div>
    <div class="risk-curve-labels">${curve.map(row => `<div class="risk-curve-label"><b>${esc(row.label)} · ${fixed(row.value, 2)}</b><span>${row.expiration ? esc(shortDay(row.expiration)) : 'cash index'}</span></div>`).join('')}</div>`;
  }

  function scoreBody(score) {
    const labels = { vvix: 'VVIX', curve: '30→60d curve', move: 'MOVE', skew: 'SKEW', hy_oas: 'HY OAS' };
    const order = ['vvix', 'curve', 'move', 'skew', 'hy_oas'];
    const components = order.map(name => [name, score.components[name]]).filter(([, row]) => row).map(([name, row]) => {
      const percent = Number(row.maximum) ? Number(row.points) / Number(row.maximum) * 100 : 0;
      const value = row.active ? `${fixed(row.points, 2)} / ${fixed(row.maximum, 2)}` : 'stale · zero weight';
      return `<div class="risk-component${row.active ? '' : ' risk-component--inactive'}">
        <div class="risk-component-head"><span>${esc(labels[name] || name)} · ${row.risk_percentile == null ? 'P—' : `P${Math.round(row.risk_percentile)}`}</span><b>${esc(value)}</b></div>
        <div class="risk-component-track"><span class="risk-component-fill" style="width:${percent.toFixed(1)}%"></span></div>
      </div>`;
    }).join('');
    return `<div class="risk-score-body">
      <div class="risk-score-large ${regimeClass(score.label)}"><b>${Math.round(Number(score.total))}</b><span>${esc(score.label)} · exact ${fixed(score.total, 2)}</span></div>
      <div class="risk-components">${components}</div>
      <details class="risk-rules"><summary>Score rules</summary><ul>${score.rules.map(rule => `<li>${esc(rule)}</li>`).join('')}</ul></details>
    </div>`;
  }

  function frequencyCell(row, label) {
    if (row.frequency == null) return `<td data-label="${esc(label)}">—</td>`;
    return `<td data-label="${esc(label)}"><b>${fixed(row.frequency, 1)}%</b><small>${esc(row.events)} / ${esc(row.observations)}</small></td>`;
  }

  function frequencyTable(table) {
    const labels = { vix_above_25: 'VIX closes >25', spy_drawdown_5: 'SPY drawdown ≥5%' };
    const rows = [];
    Object.entries(table.targets).forEach(([target, horizons]) => {
      ['21', '42'].forEach(horizon => {
        const item = horizons[horizon];
        rows.push(`<tr><th scope="row">${esc(labels[target])}<small>within ${horizon} sessions</small></th>${frequencyCell({ frequency: item.frequency, events: item.events, observations: item.observations }, 'Base rate')}${frequencyCell(item.bands.Contained, 'Contained')}${frequencyCell(item.bands.Watchful, 'Watchful')}${frequencyCell(item.bands.Elevated, 'Elevated')}</tr>`);
      });
    });
    return `<div class="risk-frequency-wrap"><table class="risk-frequency"><thead><tr><th>Observed outcome</th><th>Base rate</th><th>Contained</th><th>Watchful</th><th>Elevated</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }

  function modelStatus(status) {
    const endpointCopy = Number.isFinite(Number(status.endpoints_total))
      ? `${status.endpoints_passed}/${status.endpoints_total} endpoints passed.` : '';
    const receipt = status.evaluation_url && status.evaluation_digest
      ? ` <a href="${esc(status.evaluation_url)}?v=${esc(status.evaluation_digest)}" target="_blank" rel="noopener">Full Brier receipt</a>` : '';
    return `<div class="risk-model-status"><b>${esc(status.status.replaceAll('_', ' '))}</b><span>${esc(status.message)} ${esc(endpointCopy)}${receipt}</span></div>`;
  }

  function render(payload) {
    const c = payload.current, dates = c.dates, metrics = c.metrics, context = c.context_metrics;
    const vix = normalizeSeries(payload.series.vix);
    const vvix = normalizeSeries(payload.series.vvix);
    const move = normalizeSeries(payload.series.move);
    const skew = normalizeSeries(payload.series.skew);
    const slope = normalizeSeries(payload.series.curve_spread, 'slope_percent');
    const vix9dRatio = normalizeSeries(payload.series.vix9d_vix);
    const vix3mRatio = normalizeSeries(payload.series.vix_vix3m);
    const scoreHistory = normalizeSeries(payload.history.score, 'score');
    const spy = normalizeSeries(payload.history.spy);
    const asOf = payload.as_of;
    chartSequence = 0;
    chartRegistry.clear();
    sharedTooltipSeries = [
      tooltipMetric('vix', 'VIX', vix),
      tooltipMetric('vvix', 'VVIX', vvix),
      tooltipMetric('curve', '30→60d curve', slope, 2, '%', true),
      tooltipMetric('move', 'MOVE', move),
      tooltipMetric('skew', 'SKEW', skew),
      tooltipMetric('score', 'Conditions Score', scoreHistory),
      tooltipMetric('spy', 'S&P 500 (SPY)', spy),
      tooltipMetric('vix9d-vix', 'VIX9D / VIX', vix9dRatio, 3),
      tooltipMetric('vix-vix3m', 'VIX / VIX3M', vix3mRatio, 3),
    ].map(row => ({ ...row, values: new Map(row.series.map(point => [point.date, point.value])) }));

    const mainPanels = [
      linePanel({ name: 'VIX · current equity volatility', series: vix, current: fixed(c.vix), band: c.bands.vix, domain: dynamicDomain(vix, 10, 30), zones: [{ from: 0, to: 15, className: 'risk-zone-calm' }, { from: 15, to: 25, className: 'risk-zone-watch' }, { from: 25, to: 100, className: 'risk-zone-high' }], thresholds: [15, 20, 25], windows: payload.windows.vix_spikes, accent: true, asOf }),
      linePanel({ name: 'VVIX · volatility of VIX', series: vvix, current: fixed(c.vvix), band: c.bands.vvix, domain: dynamicDomain(vvix, 70, 125), zones: [{ from: 0, to: 90, className: 'risk-zone-calm' }, { from: 90, to: 110, className: 'risk-zone-watch' }, { from: 110, to: 300, className: 'risk-zone-high' }], thresholds: [90, 110], windows: payload.windows.vix_spikes, asOf }),
      linePanel({ name: 'VIX curve · constant-maturity 30→60d slope', series: slope, current: signed(c.curve_slope_percent), band: c.curve_band, domain: dynamicDomain(slope, -5, 10), thresholds: [0], windows: payload.windows.vix_spikes, zero: true, asOf }),
      linePanel({ name: 'MOVE · Treasury volatility', series: move, current: fixed(c.move), band: metrics.move.stale ? 'STALE' : c.bands.move, domain: dynamicDomain(move, 55, 110), thresholds: [80, 100], windows: payload.windows.vix_spikes, asOf }),
      linePanel({ name: 'SKEW · priced tail risk', series: skew, current: fixed(c.skew), band: c.bands.skew, domain: dynamicDomain(skew, 115, 155), thresholds: [130, 145], windows: payload.windows.vix_spikes, asOf }),
    ].join('');

    const vvixFocus = [
      linePanel({ name: 'VVIX with >110 periods', series: vvix, current: fixed(c.vvix), band: `P${Math.round(metrics.vvix.percentile)}`, domain: dynamicDomain(vvix, 70, 125), thresholds: [110], windows: payload.windows.vvix_high, accent: true, asOf }),
      linePanel({ name: 'VIX follow-through', series: vix, current: fixed(c.vix), band: `P${Math.round(context.vix.percentile)}`, domain: dynamicDomain(vix, 10, 30), thresholds: [25], windows: payload.windows.vvix_high, asOf }),
    ].join('');

    const slopePanel = linePanel({ name: 'Historical constant-maturity slope', series: slope, current: signed(c.curve_slope_percent), band: c.curve_band, domain: dynamicDomain(slope, -5, 10), thresholds: [0], zero: true, asOf });
    const ratioPanels = [
      linePanel({ name: 'VIX9D / VIX · near-term event pressure', series: vix9dRatio, current: fixed(context.vix9d_vix.value, 3), band: `P${Math.round(context.vix9d_vix.percentile)}`, domain: dynamicDomain(vix9dRatio, .65, 1.15), thresholds: [1], zero: false, asOf }),
      linePanel({ name: 'VIX / VIX3M · short-vs-quarterly stress', series: vix3mRatio, current: fixed(context.vix_vix3m.value, 3), band: `P${Math.round(context.vix_vix3m.percentile)}`, domain: dynamicDomain(vix3mRatio, .65, 1.15), thresholds: [1], zero: false, asOf }),
    ].join('');
    const spyValues = spy.map(row => row.value);
    const spyPanel = linePanel({ name: 'S&P 500 (SPY) · daily close', series: spy, current: fixed(spy[spy.length - 1].value, 2), domain: dynamicDomain(spy, Math.min(...spyValues), Math.max(...spyValues), .05), windows: payload.history.vix_spikes, asOf, startDate: payload.comparison_start, startLabel: payload.comparison_start.slice(0, 4) });
    const scorePanel = linePanel({ name: 'Conditions Score history', series: scoreHistory, current: fixed(payload.score.total, 2), band: payload.score.label, domain: [0, 100], zones: [{ from: 0, to: 25, className: 'risk-zone-calm' }, { from: 25, to: 50, className: 'risk-zone-watch' }, { from: 50, to: 100, className: 'risk-zone-high' }], thresholds: [25, 50], windows: payload.history.vix_spikes, accent: true, asOf, startDate: payload.comparison_start, startLabel: payload.comparison_start.slice(0, 4) });

    const moveLag = metrics.move.stale ? ` · MOVE stale by ${metrics.move.age_sessions} sessions` : '';
    const gateTone = payload.gate_policy.hard_gate_enabled ? 'risk-elevated' : 'risk-watchful';
    shell.innerHTML = `<div class="risk-shell">
      <div class="risk-header">
        <div><h2>Market Risk Conditions</h2><p>Current conditions, historical forward outcomes, and an evidence-gated 1–2 month decision layer. Daily closes; no fitted forecast is published without beating persistence.</p></div>
        <div class="risk-updated">Last updated<br>${esc(longDay(asOf))}${esc(moveLag)}</div>
      </div>
      <div class="risk-summary" aria-label="Current market risk readings">
        <div class="risk-score-card"><div class="risk-score-top"><span class="risk-score-number ${regimeClass(payload.score.label)}">${Math.round(Number(payload.score.total))}</span><span class="risk-score-denom">/ 100</span></div><strong class="risk-regime ${regimeClass(payload.score.label)}">${esc(payload.score.label)}</strong><small>Conditions Score · exact ${fixed(payload.score.total, 2)}</small></div>
        ${metricCard('VIX', fixed(c.vix), c.bands.vix, context.vix)}
        ${metricCard('VVIX', fixed(c.vvix), c.bands.vvix, metrics.vvix)}
        ${metricCard('Curve', signed(c.curve_slope_percent), c.curve_band, metrics.curve, '%')}
        ${metricCard('MOVE', fixed(c.move), c.bands.move, metrics.move)}
        ${metricCard('SKEW', fixed(c.skew), c.bands.skew, metrics.skew)}
        ${metricCard('HY OAS', fixed(c.hy_oas), metrics.hy_oas.direction, metrics.hy_oas, '%')}
      </div>
      <ul class="risk-commentary">${payload.commentary.map(line => `<li>${esc(line)}</li>`).join('')}</ul>
      ${modelStatus(payload.model_status)}
      <div class="risk-grid">
        <section class="risk-card risk-card--wide" aria-labelledby="risk-evidence-heading"><div class="risk-card-head"><div><h3 id="risk-evidence-heading">What happened next?</h3><p>Trailing two years of SPY closes aligned with the Conditions Score. Red shading marks VIX ≥25 windows.</p></div><time datetime="${esc(asOf)}">Through ${esc(shortDay(asOf))}</time></div><div class="risk-stack">${spyPanel}${scorePanel}</div><div class="risk-frequency-section"><h4>Historical outcome frequencies</h4><p>Overlapping daily rows are descriptive, not independent episodes. Stage 3 uses blocked evaluation.</p>${frequencyTable(payload.conditional_frequencies)}</div><div class="risk-gate-note ${gateTone}"><b>Scanner policy · ${esc(payload.gate_policy.elevated_action.replace('_', ' '))}</b><span>${esc(payload.gate_policy.reason)}</span></div></section>
        <section class="risk-card risk-card--wide" aria-labelledby="risk-main-heading"><div class="risk-card-head"><div><h3 id="risk-main-heading">YTD conditions stack</h3><p>Absolute levels remain readable; percentile ranks—not fixed levels—drive the score.</p></div><time datetime="${esc(asOf)}">Updated ${esc(shortDay(asOf))}</time></div><div class="risk-stack">${mainPanels}</div><p class="risk-spike-key">Historical VIX ≥25 context</p></section>
        <section class="risk-card" aria-labelledby="risk-vvix-heading"><div class="risk-card-head"><div><h3 id="risk-vvix-heading">VVIX lead/confirmation</h3><p>Direction and percentile matter more than one static threshold.</p></div></div><div class="risk-stack">${vvixFocus}</div></section>
        <section class="risk-card" aria-labelledby="risk-ratios-heading"><div class="risk-card-head"><div><h3 id="risk-ratios-heading">Short-horizon curve ratios</h3><p>Ratios above 1 flag near-term volatility pricing above longer horizons.</p></div></div><div class="risk-stack">${ratioPanels}</div></section>
        <section class="risk-card" aria-labelledby="risk-curve-heading"><div class="risk-card-head"><div><h3 id="risk-curve-heading">Term structure monitor</h3><p>Spot→M6 context plus roll-resistant constant-maturity slope.</p></div><time datetime="${esc(c.curve_as_of)}">Updated ${esc(shortDay(c.curve_as_of))}</time></div><div class="risk-curve-body">${curveFigure(payload.curve, c.curve_as_of)}<div class="risk-traffic ${regimeClass(c.curve_band === 'Backwardation' ? 'Elevated' : 'Contained')}"><span class="risk-traffic-dot" aria-hidden="true"></span><strong>${esc(c.curve_band)}</strong><span>30→60d ${esc(signed(c.curve_slope_percent))}% · raw M2−M1 ${esc(signed(c.curve_spread))}</span></div>${slopePanel}</div></section>
        <section class="risk-card" aria-labelledby="risk-score-heading"><div class="risk-card-head"><div><h3 id="risk-score-heading">Conditions Score</h3><p>Percentile-based, stale-aware, and fully disclosed. Not a calibrated probability.</p></div><time datetime="${esc(asOf)}">Updated ${esc(shortDay(asOf))}</time></div>${scoreBody(payload.score)}</section>
      </div>
      <p class="risk-method">${esc(payload.method)} Public FRED HY OAS history currently begins ${esc(shortDay(payload.series.hy_oas[0].date))}; earlier scores normalize across available components. HY OAS ${fixed(c.hy_oas)}% observed ${shortDay(c.hy_oas_as_of)}, usable ${shortDay(c.hy_oas_available_as_of)}. Sources: <a href="https://finance.yahoo.com/quote/%5EVIX/" rel="noopener" target="_blank">Yahoo Finance</a>, <a href="https://www.cboe.com/markets/us/futures/market-statistics/historical-data/futures" rel="noopener" target="_blank">Cboe</a>, and <a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2" rel="noopener" target="_blank">FRED</a>.</p>
    </div>`;
    bindChartInteractions();
  }

  async function load() {
    if (loaded) return;
    loaded = true;
    try {
      const response = await fetch(source, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`Risk data HTTP ${response.status}`);
      const payload = await response.json();
      if (payload.schema_version !== 2 || !payload.current || !payload.score || !payload.series || !payload.curve || !payload.history || !payload.conditional_frequencies) throw new Error('Risk data contract is incomplete');
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
