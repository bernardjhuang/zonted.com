/* Broker Light behavior for /trading/ (design handoff 2026-07-21).
   Parses the cron-emitted markup in #bl-raw (positions chips, activity rows,
   YTD extremes) into sortable/filterable tables. The raw markup stays in the
   DOM (hidden) so the nightly snapshot cron keeps working unchanged. */
(() => {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const htmlSafe = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const fmtISO = iso => {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? `${MONTHS[+m[2] - 1]} ${+m[3]} ${m[1]}` : '—';
  };

  /* ── tabs ─────────────────────────────────────────────────────────── */
  const tabs = $$('[role="tab"]');
  const panelOf = t => document.getElementById(t.getAttribute('aria-controls'));
  const panels = [...new Set(tabs.map(panelOf))];
  // Keep chart-heavy inactive tabs out of the live DOM until they are opened.
  // Their existing listeners survive the detach/reinsert cycle, while the
  // default Positions view starts with no SVG parsing/layout burden.
  const parkedPanelSvgs = new WeakMap();
  panels.forEach(panel => {
    if (!panel || panel.id === 'positions-panel') return;
    const parked = $$('svg', panel).map(svg => {
      const placeholder = document.createComment('lazy-tab-svg');
      svg.replaceWith(placeholder);
      return [placeholder, svg];
    });
    if (parked.length) parkedPanelSvgs.set(panel, parked);
  });
  const restorePanelSvgs = panel => {
    const parked = parkedPanelSvgs.get(panel) || [];
    parked.forEach(([placeholder, svg]) => placeholder.replaceWith(svg));
    parkedPanelSvgs.delete(panel);
  };
  const cloneWithParkedSvg = (source, panel) => {
    const clone = source.cloneNode(true);
    if ($('svg', clone)) return clone;
    const pair = (parkedPanelSvgs.get(panel) || []).find(([placeholder]) => placeholder.parentNode === source);
    const clonePlaceholder = [...clone.childNodes].find(node => node.nodeType === Node.COMMENT_NODE && node.data === 'lazy-tab-svg');
    if (pair && clonePlaceholder) clonePlaceholder.replaceWith(pair[1].cloneNode(true));
    return clone;
  };
  function activate(tab, push) {
    tabs.forEach(t => { const on = t === tab; t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1; });
    const target = panelOf(tab);
    restorePanelSvgs(target);
    panels.forEach(p => { p.hidden = p !== target; });
    const filters = $('#bl-filters');
    if (filters) filters.hidden = target.id !== 'positions-panel';
    if (push) {
      const hash = tab.id === 'positions-tab' ? '' : '#' + tab.id.replace(/-tab$/, '');
      history.replaceState(null, '', location.pathname + location.search + hash);
    }
  }
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => activate(tab, true));
    tab.addEventListener('keydown', e => {
      let next = null;
      if (e.key === 'ArrowRight') next = tabs[(i + 1) % tabs.length];
      if (e.key === 'ArrowLeft') next = tabs[(i - 1 + tabs.length) % tabs.length];
      if (!next) return;
      e.preventDefault(); activate(next, true); next.focus();
    });
  });
  const fromHash = () => {
    const hash = location.hash === '#watchlist' ? '#scan' : location.hash;
    const exact = tabs.find(t => hash === '#' + t.id.replace(/-tab$/, ''));
    if (exact) return exact;
    if (!hash && new URL(location.href).searchParams.has('chart')) return $('#scan-tab') || tabs[0];
    const anchoredPanel = hash && document.getElementById(hash.slice(1))?.closest('[role="tabpanel"]');
    return tabs.find(t => panelOf(t) === anchoredPanel) || tabs[0];
  };
  activate(fromHash());
  addEventListener('hashchange', () => activate(fromHash()));

  /* ── momentum-scan full setup-chart accordions ───────────────────── */
  const scanPanel = $('#scan-panel');
  const chartConfigSource = $('#scan-chart-config');
  let renderSetupChartForSymbol = null;
  if (scanPanel && chartConfigSource) {
    let chartConfig = {};
    try { chartConfig = JSON.parse(chartConfigSource.textContent); } catch (error) { console.error('Invalid scan chart config', error); }
    let chartDataPromise = null;
    const loadChartData = () => {
      if (!chartDataPromise) chartDataPromise = fetch(chartConfig.url, { credentials: 'same-origin' })
        .then(response => { if (!response.ok) throw new Error(`Chart data HTTP ${response.status}`); return response.json(); })
        .then(payload => payload.charts || {})
        .catch(error => { chartDataPromise = null; throw error; });
      return chartDataPromise;
    };
    let openToggle = null;
    const W = 1120, PXH = 280, SUBH = 78, GAP = 14, AXISH = 22, ML = 8, MR = 66;
    const H = PXH + (SUBH + GAP) * 2 + AXISH;
    const COLORS = { up: '#1a7a3c', down: '#8f2222', earn: '#4a3aa7', ytd: '#6b655c', pos: '#2a78d6', neg: '#e34948', mut: '#a09a90' };
    const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
    const signed = (value, suffix = '') => value == null ? '—' : `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(2)}${suffix}`;
    const shortDate = iso => iso ? `${MONTHS[+iso.slice(5, 7) - 1]} ${+iso.slice(8, 10)}` : '—';
    const point = (x, y) => `${x.toFixed(1)},${y.toFixed(1)}`;

    function wireVwapFigure(fig) {
      if (!fig || fig.dataset.comparisonWired === 'true') return;
      let d;
      try { d = JSON.parse(fig.dataset.d); } catch (error) { console.error('Invalid sector chart data', error); return; }
      const svg = $('svg', fig), tip = $('.vwap-tip', fig), crosshair = $('.vxh', fig);
      if (!svg || !tip || !crosshair || !d?.dates?.length || d.close?.length !== d.dates.length || d.vwap?.length !== d.dates.length) return;
      tip.setAttribute('aria-live', 'polite');
      fig.dataset.comparisonWired = 'true';
      svg.setAttribute('tabindex', '0');
      const vb = svg.viewBox.baseVal, n = d.dates.length, leftPad = 10, rightPad = 58;
      let activeIndex = n - 1;
      const showPoint = (i, left, top) => {
        activeIndex = Math.max(0, Math.min(n - 1, i));
        const px = leftPad + activeIndex / (n - 1) * (vb.width - leftPad - rightPad);
        crosshair.setAttribute('x1', px); crosshair.setAttribute('x2', px); crosshair.removeAttribute('visibility');
        const diff = (d.close[activeIndex] / d.vwap[activeIndex] - 1) * 100;
        const z = d.z50?.[activeIndex];
        const date = document.createElement('b'); date.textContent = d.dates[activeIndex];
        const nodes = [date, document.createElement('br'), document.createTextNode(`close ${Number(d.close[activeIndex]).toFixed(2)}`), document.createElement('br'), document.createTextNode(`vwap ${Number(d.vwap[activeIndex]).toFixed(2)}`), document.createElement('br'), document.createTextNode(`${diff >= 0 ? '+' : ''}${diff.toFixed(2)}%`)];
        if (z != null) nodes.push(document.createElement('br'), document.createTextNode(`50d z ${z >= 0 ? '+' : ''}${Number(z).toFixed(2)}`));
        tip.replaceChildren(...nodes);
        tip.hidden = false;
        tip.style.left = `${Math.max(8, Math.min(fig.clientWidth - tip.offsetWidth - 8, left))}px`;
        tip.style.top = `${top}px`;
      };
      svg.addEventListener('pointermove', event => {
        const rect = svg.getBoundingClientRect();
        const vx = (event.clientX - rect.left) / rect.width * vb.width;
        const i = Math.max(0, Math.min(n - 1, Math.round((vx - leftPad) / (vb.width - leftPad - rightPad) * (n - 1))));
        const figRect = fig.getBoundingClientRect();
        let left = event.clientX - figRect.left + 14;
        showPoint(i, left, event.clientY - figRect.top - 10);
        if (left + tip.offsetWidth > figRect.width - 8) {
          left = event.clientX - figRect.left - tip.offsetWidth - 14;
          tip.style.left = `${Math.max(8, left)}px`;
        }
      });
      svg.addEventListener('pointerleave', () => { if (document.activeElement !== svg) { tip.hidden = true; crosshair.setAttribute('visibility', 'hidden'); } });
      svg.addEventListener('focus', () => showPoint(activeIndex, fig.clientWidth - 150, svg.offsetTop + 18));
      svg.addEventListener('keydown', event => {
        let next = null;
        if (event.key === 'ArrowLeft') next = activeIndex - 1;
        if (event.key === 'ArrowRight') next = activeIndex + 1;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = n - 1;
        if (next == null) return;
        event.preventDefault();
        showPoint(next, leftPad + Math.max(0, Math.min(n - 1, next)) / (n - 1) * (fig.clientWidth - leftPad - rightPad) + 10, svg.offsetTop + 18);
      });
      svg.addEventListener('blur', () => { tip.hidden = true; crosshair.setAttribute('visibility', 'hidden'); });
    }

    async function renderSetupChart(shell, symbol) {
      if (shell.dataset.rendered === 'true' || shell.dataset.loading === 'true') return;
      shell.dataset.loading = 'true';
      shell.setAttribute('aria-busy', 'true');
      shell.innerHTML = '<p class="scan-chart-loading">Loading full setup chart…</p>';
      let rec;
      try {
        const chartData = await loadChartData();
        rec = chartData[symbol];
      } catch (error) {
        console.error('Unable to load scan chart data', error);
        shell.innerHTML = '<p class="scan-null">Full setup chart failed to load.</p>';
        delete shell.dataset.loading;
        shell.removeAttribute('aria-busy');
        return;
      }
      const s = rec?.series;
      if (!s?.dates?.length) {
        shell.innerHTML = '<p class="scan-null">Full setup chart unavailable.</p>';
        shell.dataset.rendered = 'true';
        delete shell.dataset.loading;
        shell.removeAttribute('aria-busy');
        return;
      }
      const n = s.dates.length, iw = W - ML - MR;
      const x = i => ML + (i + 0.5) / n * iw;
      const candleW = Math.max(1.6, iw / n * 0.6);
      const earnPoints = s.ev.map((value, i) => value == null ? null : [i, value]).filter(Boolean);
      const priceValues = [...s.l, ...s.h, ...s.yv, ...earnPoints.map(pair => pair[1])];
      let lo = Math.min(...priceValues), hi = Math.max(...priceValues);
      const pad = Math.max((hi - lo) * 0.05, Math.max(Math.abs(hi), 1) * 0.005);
      lo -= pad; hi += pad;
      const yp = value => (hi - value) / (hi - lo) * (PXH - 8) + 4;
      const parts = [], axis = [];

      for (let i = 1; i < n; i += 1) {
        if (s.dates[i].slice(5, 7) !== s.dates[i - 1].slice(5, 7)) {
          parts.push(`<line x1="${x(i).toFixed(1)}" y1="0" x2="${x(i).toFixed(1)}" y2="${H - AXISH}" class="sg"/>`);
          axis.push(`<text x="${x(i).toFixed(1)}" y="${H - 7}" class="sa" text-anchor="middle">${MONTHS[+s.dates[i].slice(5, 7) - 1]}</text>`);
        }
      }
      for (let k = 0; k < 4; k += 1) {
        const value = lo + (hi - lo) * k / 3;
        parts.push(`<line x1="${ML}" y1="${yp(value).toFixed(1)}" x2="${ML + iw}" y2="${yp(value).toFixed(1)}" class="sg"/><text x="${ML + iw + 6}" y="${(yp(value) + 3.5).toFixed(1)}" class="sa">${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}</text>`);
      }
      for (let i = 0; i < n; i += 1) {
        const color = s.c[i] >= s.o[i] ? COLORS.up : COLORS.down;
        const top = Math.max(s.o[i], s.c[i]), bottom = Math.min(s.o[i], s.c[i]);
        parts.push(`<line x1="${x(i).toFixed(1)}" y1="${yp(s.h[i]).toFixed(1)}" x2="${x(i).toFixed(1)}" y2="${yp(s.l[i]).toFixed(1)}" stroke="${color}" stroke-width="1"/><rect x="${(x(i) - candleW / 2).toFixed(1)}" y="${yp(top).toFixed(1)}" width="${candleW.toFixed(1)}" height="${Math.max(0.8, yp(bottom) - yp(top)).toFixed(1)}" fill="${color}"/>`);
      }
      parts.push(`<polyline points="${s.yv.map((value, i) => point(x(i), yp(value))).join(' ')}" fill="none" stroke="${COLORS.ytd}" stroke-width="1.5" stroke-dasharray="5 4"/>`);
      if (earnPoints.length) {
        parts.push(`<polyline points="${earnPoints.map(([i, value]) => point(x(i), yp(value))).join(' ')}" fill="none" stroke="${COLORS.earn}" stroke-width="2"/>`);
        parts.push(`<text x="${x(earnPoints[0][0]).toFixed(1)}" y="${(yp(earnPoints[0][1]) - 6).toFixed(1)}" class="sa" fill="${COLORS.earn}" text-anchor="middle">E</text>`);
      }
      const tags = [[s.c[n - 1], '#1a1815', s.c[n - 1].toFixed(2)]];
      if (earnPoints.length) tags.push([earnPoints[earnPoints.length - 1][1], COLORS.earn, earnPoints[earnPoints.length - 1][1].toFixed(2)]);
      tags.push([s.yv[n - 1], COLORS.ytd, s.yv[n - 1].toFixed(2)]);
      tags.forEach(([value, color, text]) => parts.push(`<text x="${W - 2}" y="${(yp(value) + 3.5).toFixed(1)}" class="st" fill="${color}" text-anchor="end">${text}</text>`));

      const y0 = PXH + GAP;
      const spreadValues = s.sp.filter(value => value != null);
      const zmax = Math.max(2, ...(spreadValues.map(value => Math.abs(value) * 1.1)));
      const ys = value => y0 + (zmax - value) / (2 * zmax) * SUBH;
      parts.push(`<text x="${ML}" y="${y0 + 10}" class="sl">Spread Z vs SPY (50d)</text><line x1="${ML}" y1="${ys(0).toFixed(1)}" x2="${ML + iw}" y2="${ys(0).toFixed(1)}" class="sz"/>`);
      for (let i = 1; i < n; i += 1) {
        if (s.sp[i - 1] == null || s.sp[i] == null) continue;
        parts.push(`<line x1="${x(i - 1).toFixed(1)}" y1="${ys(s.sp[i - 1]).toFixed(1)}" x2="${x(i).toFixed(1)}" y2="${ys(s.sp[i]).toFixed(1)}" stroke="${s.sp[i] >= 0 ? COLORS.up : COLORS.neg}" stroke-width="1.8"/>`);
      }
      const lastSpread = [...s.sp].reverse().find(value => value != null);
      if (lastSpread != null) parts.push(`<text x="${W - 2}" y="${(ys(lastSpread) + 3.5).toFixed(1)}" class="st" fill="${lastSpread >= 0 ? COLORS.up : COLORS.neg}" text-anchor="end">${signed(lastSpread)}</text>`);

      const y1 = y0 + SUBH + GAP;
      const distValues = s.dz.filter(value => value != null);
      const dmax = Math.max(2.5, ...(distValues.map(value => Math.abs(value) * 1.1)));
      const yd = value => y1 + (dmax - value) / (2 * dmax) * SUBH;
      parts.push(`<text x="${ML}" y="${y1 + 10}" class="sl">Dist Z — YTD VWAP</text><line x1="${ML}" y1="${yd(0).toFixed(1)}" x2="${ML + iw}" y2="${yd(0).toFixed(1)}" class="sz"/>`);
      [1, -1].forEach(level => parts.push(`<line x1="${ML}" y1="${yd(level).toFixed(1)}" x2="${ML + iw}" y2="${yd(level).toFixed(1)}" class="sd"/>`));
      const barW = Math.max(1.2, iw / n * 0.55);
      s.dz.forEach((value, i) => {
        if (value == null) return;
        const color = value > 1 ? COLORS.pos : value < -1 ? COLORS.neg : COLORS.mut;
        parts.push(`<rect x="${(x(i) - barW / 2).toFixed(1)}" y="${Math.min(yd(0), yd(value)).toFixed(1)}" width="${barW.toFixed(1)}" height="${Math.abs(yd(value) - yd(0)).toFixed(1)}" fill="${color}"/>`);
      });
      const lastDist = [...s.dz].reverse().find(value => value != null);

      const detailId = shell.closest('[data-scan-detail], [data-position-chart-detail]').id;
      const titleId = `${detailId}-title`, descId = `${detailId}-desc`;
      const stats = rec.stats || {};
      const side = stats.evwap_side == null ? '—' : `${stats.evwap_side ? '▲' : '▼'} ${stats.evwap_streak}d`;
      const badgeClass = ({ 'ENTER+': 'setup-b--long', ENTER: 'setup-b--long', 'SHORT+': 'setup-b--short', SHORT: 'setup-b--short', BREAKING: 'setup-b--break' })[rec.label] || 'setup-b--watch';
      const lastEarn = earnPoints.length ? earnPoints[earnPoints.length - 1][1] : null;
      const description = `${symbol} setup chart with ${n} daily candles from ${s.dates[0]} through ${s.dates[n - 1]}. Latest close ${s.c[n - 1].toFixed(2)}, YTD VWAP ${s.yv[n - 1].toFixed(2)}, earnings VWAP ${lastEarn == null ? 'unavailable' : lastEarn.toFixed(2)}, Spread Z ${lastSpread == null ? 'unavailable' : signed(lastSpread)}, and Dist Z ${lastDist == null ? 'unavailable' : signed(lastDist)}. Focus the chart and use Left and Right Arrow, Home, or End to inspect exact historical values.`;
      const stockCard = `<section class="setup-card scan-setup-card"><header><b id="${titleId}">${esc(symbol)}</b><span>${esc(rec.sector)}</span><span class="setup-b ${badgeClass}">${esc(rec.label)}</span><span class="setup-stats">spread Z <b>${signed(stats.spread_z)}</b> · dist Z <b>${signed(stats.dist_z)}</b> · vs earn VWAP <b>${signed(stats.evwap_pct, '%')}</b> (${side}) · next earnings ${shortDate(stats.next_earn)}</span></header><p class="setup-read">${esc(rec.read)}</p><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" tabindex="0" aria-labelledby="${titleId} ${descId}"><desc id="${descId}">${esc(description)}</desc>${parts.join('')}${axis.join('')}<line class="sx" x1="0" y1="0" x2="0" y2="${H - AXISH}" visibility="hidden"/></svg><div class="setup-tip" aria-live="polite" hidden></div></section>`;
      shell.innerHTML = `<div class="scan-comparison-grid"><div class="scan-stock-chart">${stockCard}</div></div>`;
      const grid = $('.scan-comparison-grid', shell);
      const sectorSource = $$('.vwap-chart', $('#vwap-panel')).find(fig => fig.dataset.sym === rec.sector_etf);
      if (sectorSource) {
        const sectorPane = document.createElement('div');
        sectorPane.className = 'scan-sector-chart';
        const sectorChart = cloneWithParkedSvg(sectorSource, $('#vwap-panel'));
        sectorChart.classList.remove('vwap-chart--spy');
        sectorChart.querySelector('.vwap-tip')?.replaceChildren();
        sectorPane.append(sectorChart);
        grid.append(sectorPane);
        wireVwapFigure(sectorChart);
      }
      const card = $('.scan-setup-card', shell), svg = $('svg', card), tip = $('.setup-tip', card), crosshair = $('.sx', card);
      let activeIndex = n - 1;
      const showPoint = (i, left, top) => {
        activeIndex = Math.max(0, Math.min(n - 1, i));
        const px = x(activeIndex);
        crosshair.setAttribute('x1', px); crosshair.setAttribute('x2', px); crosshair.removeAttribute('visibility');
        const values = [
          ['close', s.c[activeIndex]], ['earn vwap', s.ev[activeIndex]], ['ytd vwap', s.yv[activeIndex]],
          ['spread z', s.sp[activeIndex]], ['dist z', s.dz[activeIndex]],
        ].filter(([, value]) => value != null);
        const date = document.createElement('b'); date.textContent = s.dates[activeIndex];
        const nodes = [date];
        values.forEach(([label, value]) => { nodes.push(document.createElement('br'), document.createTextNode(`${label} ${Number(value).toFixed(2)}`)); });
        tip.replaceChildren(...nodes); tip.hidden = false;
        tip.style.left = `${Math.max(8, Math.min(card.clientWidth - tip.offsetWidth - 8, left))}px`;
        tip.style.top = `${top}px`;
      };
      svg.addEventListener('pointermove', event => {
        const rect = svg.getBoundingClientRect(), vx = (event.clientX - rect.left) / rect.width * W;
        const i = Math.max(0, Math.min(n - 1, Math.floor((vx - ML) / iw * n)));
        const cardRect = card.getBoundingClientRect();
        let left = event.clientX - cardRect.left + 14;
        showPoint(i, left, event.clientY - cardRect.top - 10);
        if (left + tip.offsetWidth > cardRect.width - 8) {
          left = event.clientX - cardRect.left - tip.offsetWidth - 14;
          tip.style.left = `${Math.max(8, left)}px`;
        }
      });
      svg.addEventListener('pointerleave', () => { if (document.activeElement !== svg) { tip.hidden = true; crosshair.setAttribute('visibility', 'hidden'); } });
      svg.addEventListener('focus', () => showPoint(activeIndex, card.clientWidth - 150, svg.offsetTop + 18));
      svg.addEventListener('keydown', event => {
        let next = null;
        if (event.key === 'ArrowLeft') next = activeIndex - 1;
        if (event.key === 'ArrowRight') next = activeIndex + 1;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = n - 1;
        if (next == null) return;
        event.preventDefault();
        showPoint(next, x(Math.max(0, Math.min(n - 1, next))) / W * card.clientWidth + 10, svg.offsetTop + 18);
      });
      svg.addEventListener('blur', () => { tip.hidden = true; crosshair.setAttribute('visibility', 'hidden'); });
      shell.dataset.rendered = 'true';
      delete shell.dataset.loading;
      shell.removeAttribute('aria-busy');
    }
    renderSetupChartForSymbol = renderSetupChart;

    function syncChartParam(symbol) {
      const url = new URL(location.href);
      if (symbol) url.searchParams.set('chart', symbol); else url.searchParams.delete('chart');
      history.replaceState(null, '', url);
    }

    function closeChart(toggle, sync = true) {
      if (!toggle) return;
      const detail = document.getElementById(toggle.getAttribute('aria-controls'));
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', `Show ${toggle.closest('[data-scan-row]').dataset.scanSymbol} setup and sector charts`);
      toggle.closest('[data-scan-row]').classList.remove('is-open');
      if (detail) detail.hidden = true;
      if (openToggle === toggle) openToggle = null;
      if (sync) syncChartParam(null);
    }

    function openChart(toggle, sync = true) {
      if (openToggle && openToggle !== toggle) closeChart(openToggle, false);
      const row = toggle.closest('[data-scan-row]');
      const detail = document.getElementById(toggle.getAttribute('aria-controls'));
      if (!detail) return;
      toggle.setAttribute('aria-expanded', 'true');
      toggle.setAttribute('aria-label', `Hide ${row.dataset.scanSymbol} setup and sector charts`);
      row.classList.add('is-open');
      detail.hidden = false;
      renderSetupChart($('[data-scan-chart]', detail), row.dataset.scanSymbol);
      openToggle = toggle;
      if (sync) syncChartParam(row.dataset.scanSymbol);
    }

    function toggleChart(toggle) {
      if (toggle.getAttribute('aria-expanded') === 'true') closeChart(toggle); else openChart(toggle);
    }

    scanPanel.addEventListener('click', event => {
      const toggle = event.target.closest('[data-scan-toggle]');
      if (toggle) { event.preventDefault(); return toggleChart(toggle); }
      const row = event.target.closest('[data-scan-row]');
      if (row && !event.target.closest('a, button, input, select, textarea')) {
        const rowToggle = $('[data-scan-toggle]', row);
        if (rowToggle) toggleChart(rowToggle);
      }
    });

    const initialSymbol = new URL(location.href).searchParams.get('chart');
    if (initialSymbol) {
      const initialDetail = $$('[data-scan-detail]', scanPanel).find(detail => detail.dataset.scanSymbol === initialSymbol.toUpperCase());
      const initialToggle = initialDetail?.previousElementSibling?.querySelector('[data-scan-toggle]');
      if (initialToggle) {
        openChart(initialToggle, false);
        requestAnimationFrame(() => initialToggle.closest('[data-scan-row]').scrollIntoView({ block: 'start' }));
      }
    }
  }

  /* ── parse cron markup ────────────────────────────────────────────── */
  const raw = $('#bl-raw'), built = $('#bl-built');
  if (!raw || !built) return;

  const trades = { buy: [], sell: [] };
  $$('.activity-lane', raw).forEach(lane => {
    const kind = lane.classList.contains('activity-lane--buy') ? 'buy' : 'sell';
    $$('.activity-row', lane).forEach(row => {
      const action = ($('.activity-action', row) || {}).textContent || '';
      const typeTxt = ($('.activity-type', row) || {}).textContent || '';
      const pnlEl = $('.activity-pnl', row);
      trades[kind].push({
        iso: ($('.activity-date', row) || {}).getAttribute ? $('.activity-date', row).getAttribute('datetime') : '',
        dateTxt: (($('.activity-date', row) || {}).textContent || '').trim(),
        inst: action.trim(),
        sym: (action.trim().split(/\s+/)[0] || '').toUpperCase(),
        asset: /option/i.test(typeTxt) ? 'Options' : 'Equities',
        fills: (typeTxt.match(/(\d+)\s*fills?/) || [0, 1])[1],
        pnl: pnlEl ? parseFloat(pnlEl.textContent.replace(/[+%]/g, '').replace('−', '-')) : NaN,
        pnlTxt: pnlEl ? pnlEl.textContent.trim() : '—',
        status: /unrealized/i.test((($('.activity-status', row) || {}).textContent || '')) ? 'Unrealized' : 'Realized',
      });
    });
  });

  const sinceEntry = {};
  trades.buy.forEach(t => { if (t.status === 'Unrealized') sinceEntry[t.inst.toLowerCase()] = t.pnlTxt; });

  const positions = [];
  $$('.position-group', raw).forEach(g => {
    const h = (($('h3', g) || {}).textContent || '').trim();
    if (!/^(Equities|Equity shorts|Options)$/i.test(h)) return;
    $$('.ticker', g).forEach(t => {
      const sym = (($('.ticker-symbol', t) || {}).textContent || '').trim();
      if (!sym) return;
      const name = (($('.ticker-name', t) || {}).textContent || '').trim();
      if (/^Options$/i.test(h)) {
        const m = name.match(/(Call|Put)\s+([\d.]+)\s+(\d{4}-\d{2}-\d{2})/i);
        positions.push({
          sym, type: 'Option', side: m ? m[1] : '—',
          strike: m ? (+m[2]).toFixed(2) : '—', strikeN: m ? +m[2] : -1,
          expiry: m ? fmtISO(m[3]) : '—', expiryISO: m ? m[3] : '',
          since: sinceEntry[(sym + ' ' + (m ? m[1].toLowerCase() : '')).toLowerCase()] || '—',
        });
      } else {
        const side = /short/i.test(h) || /short/i.test(name) ? 'Short' : 'Long';
        positions.push({ sym, type: 'Equity', side, strike: '—', strikeN: -1, expiry: '—', expiryISO: '',
          since: sinceEntry[(sym + ' shares').toLowerCase()] || '—' });
      }
    });
  });

  const ext = { wins: [], losses: [] };
  $$('.ytd-lane', raw).forEach(lane => {
    const kind = lane.classList.contains('ytd-lane--wins') ? 'wins' : 'losses';
    $$('.ytd-row', lane).forEach(row => {
      const action = ($('.ytd-action', row) || {}).textContent || '';
      const typeTxt = (($('.ytd-type', row) || {}).textContent || '').trim();
      const pnlEl = $('.ytd-pnl', row);
      const pnlTxt = pnlEl ? (pnlEl.textContent.match(/[+−\-][\d.]+%/) || ['—'])[0] : '—';
      ext[kind].push({
        iso: ($('.ytd-date', row) || {}).getAttribute ? $('.ytd-date', row).getAttribute('datetime') : '',
        dateTxt: (($('.ytd-date', row) || {}).textContent || '').trim(),
        sym: (action.trim().split(/\s+/)[0] || '').toUpperCase(),
        kindTxt: (action.replace(typeTxt, '').trim().split(/\s+/).slice(1).join(' ') || '').toLowerCase(),
        pnl: parseFloat(pnlTxt.replace(/[+%]/g, '').replace('−', '-')),
        pnlTxt,
      });
    });
  });

  /* ── state ────────────────────────────────────────────────────────── */
  const state = {
    q: '', asset: 'All', status: 'All',
    posSort: { key: 'sym', dir: 1 },
    tradeSort: { key: 'date', dir: -1 },
    extBy: 'pct',
  };
  let openPositionToggle = null;

  const arrow = (sort, key) => sort.key === key ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ⇅';
  const pnlCls = v => v > 0 ? 'bl-gain' : v < 0 ? 'bl-loss' : '';
  const sideCls = s => /long|call/i.test(s) ? 'bl-gain' : /short|put/i.test(s) ? 'bl-loss' : '';

  function render() {
    openPositionToggle = null;
    const q = state.q.trim().toUpperCase();
    const matchSym = sym => !q || sym.includes(q);
    const matchAsset = a => state.asset === 'All' || a === state.asset;
    let visible = 0;

    const pos = positions
      .filter(p => matchSym(p.sym) && matchAsset(p.type === 'Option' ? 'Options' : 'Equities'))
      .sort((a, b) => {
        const k = state.posSort.key, d = state.posSort.dir;
        const va = k === 'strike' ? a.strikeN : k === 'expiry' ? a.expiryISO : a[k];
        const vb = k === 'strike' ? b.strikeN : k === 'expiry' ? b.expiryISO : b[k];
        return (va < vb ? -1 : va > vb ? 1 : 0) * d;
      });
    visible += pos.length;

    const tr = kind => trades[kind]
      .filter(t => matchSym(t.sym) && matchAsset(t.asset) && (state.status === 'All' || t.status === state.status))
      .sort((a, b) => {
        const k = state.tradeSort.key, d = state.tradeSort.dir;
        const va = k === 'date' ? a.iso : a.pnl, vb = k === 'date' ? b.iso : b.pnl;
        return (va < vb ? -1 : va > vb ? 1 : 0) * d;
      });
    const buys = tr('buy'), sells = tr('sell');
    visible += buys.length + sells.length;

    const exts = kind => {
      const rows = ext[kind].filter(r => matchSym(r.sym));
      if (state.extBy === 'date') return rows.slice().sort((a, b) => (a.iso < b.iso ? 1 : -1));
      return rows.slice().sort((a, b) => kind === 'wins' ? b.pnl - a.pnl : a.pnl - b.pnl);
    };
    const wins = exts('wins'), losses = exts('losses');
    visible += wins.length + losses.length;

    const posHead = ['sym|Symbol', 'type|Type', 'side|Side', 'strike|Strike', 'expiry|Expiry', 'since|Since entry|r']
      .map(c => { const [k, label, r] = c.split('|'); return `<button data-sort-pos="${k}" class="${r || ''}">${label}${arrow(state.posSort, k)}</button>`; }).join('');
    const posRows = pos.map((p, i) => {
      const symbol = htmlSafe(p.sym), detailId = `position-chart-${p.sym.toLowerCase().replace(/[^a-z0-9-]+/g, '-')}-${i}`;
      return `<div class="bl-row g-pos" data-position-row data-position-symbol="${symbol}">
      <span class="sym"><button type="button" class="bl-position-chart-toggle" data-position-chart-toggle aria-expanded="false" aria-controls="${detailId}" aria-label="Show ${symbol} setup and sector charts"><span class="scan-row-chevron" aria-hidden="true">›</span>${symbol}</button></span><span>${htmlSafe(p.type)}</span>
      <span class="${sideCls(p.side)}">${htmlSafe(p.side)}</span>
      <span class="mono">${htmlSafe(p.strike)}</span><span class="mono mut">${htmlSafe(p.expiry)}</span>
      <span class="r mono ${p.since === '—' ? 'mut' : pnlCls(parseFloat(p.since.replace('−', '-')))}">${htmlSafe(p.since)}</span>
    </div><div class="bl-position-chart-detail" id="${detailId}" data-position-chart-detail data-position-symbol="${symbol}" hidden><div class="scan-setup-chart" data-position-chart-shell></div></div>`;
    }).join('') || '<div class="bl-empty">No positions match the current filters.</div>';

    const tradeHead = `<button data-sort-trade="date">Date${arrow(state.tradeSort, 'date')}</button><span>Instrument</span><span>Fills</span><button data-sort-trade="pnl" class="r">P&amp;L${arrow(state.tradeSort, 'pnl')}</button>`;
    const tradeRows = rows => rows.map(t => `<div class="bl-row g-trade">
      <span class="mono mut">${t.dateTxt}</span><span class="sym">${t.inst}</span>
      <span class="mono mut">×${t.fills}</span>
      <span class="r mono ${pnlCls(t.pnl)}">${t.pnlTxt}<span class="bl-tag">${t.status}</span></span>
    </div>`).join('') || '<div class="bl-empty">No trades match the current filters.</div>';

    const extRows = rows => rows.map((r, i) => `<div class="bl-row g-ext">
      <span class="mono" style="color:var(--bl-faint);font-size:11px">${i + 1}</span>
      <span class="mut" style="font-size:12px">${r.dateTxt}</span>
      <span><span class="sym">${r.sym}</span> <span class="mut" style="font-size:11.5px">${r.kindTxt}</span></span>
      <span class="r mono ${pnlCls(r.pnl)}">${r.pnlTxt}</span>
    </div>`).join('') || '<div class="bl-empty">Nothing matches.</div>';

    const tgl = state.extBy === 'pct' ? 'By % ▾' : 'By date ▾';
    built.innerHTML = `
      <div class="bl-card">
        <div class="bl-card-title">Open positions <span>· Robinhood · ${pos.length}</span></div>
        <div class="bl-thead g-pos">${posHead}</div>${posRows}
      </div>
      <div class="bl-pair">
        <div class="bl-card"><div class="bl-card-title">Recent buys <span>· $2K+ · fills consolidated by date</span></div>
          <div class="bl-thead g-trade">${tradeHead}</div>${tradeRows(buys)}</div>
        <div class="bl-card"><div class="bl-card-title">Recent sells <span>· $2K+ · fills consolidated by date</span></div>
          <div class="bl-thead g-trade">${tradeHead}</div>${tradeRows(sells)}</div>
      </div>
      <div class="bl-pair" id="bl-ext">
        <div class="bl-card"><div class="bl-card-title">Top 10 wins <span>· closed · by ${state.extBy === 'pct' ? '% return' : 'date'}</span><button class="bl-tgl" data-ext-toggle>${tgl}</button></div>${extRows(wins)}</div>
        <div class="bl-card"><div class="bl-card-title">Top 10 losses <span>· closed · by ${state.extBy === 'pct' ? '% return' : 'date'}</span><button class="bl-tgl" data-ext-toggle>${tgl}</button></div>${extRows(losses)}</div>
      </div>`;

    const active = q || state.asset !== 'All' || state.status !== 'All';
    const note = $('#bl-match');
    if (note) { note.hidden = !active; note.textContent = `${visible} row${visible === 1 ? '' : 's'} match`; }
  }

  /* ── events ───────────────────────────────────────────────────────── */
  built.addEventListener('click', e => {
    const positionToggle = e.target.closest('[data-position-chart-toggle]');
    const positionRow = e.target.closest('[data-position-row]');
    if (positionToggle || (positionRow && !e.target.closest('a, button, input, select, textarea'))) {
      const toggle = positionToggle || $('[data-position-chart-toggle]', positionRow);
      const row = toggle.closest('[data-position-row]'), detail = document.getElementById(toggle.getAttribute('aria-controls'));
      if (!detail || !renderSetupChartForSymbol) return;
      if (openPositionToggle && openPositionToggle !== toggle) {
        const oldRow = openPositionToggle.closest('[data-position-row]');
        const oldDetail = document.getElementById(openPositionToggle.getAttribute('aria-controls'));
        openPositionToggle.setAttribute('aria-expanded', 'false');
        openPositionToggle.setAttribute('aria-label', `Show ${oldRow.dataset.positionSymbol} setup and sector charts`);
        oldRow.classList.remove('is-open');
        if (oldDetail) oldDetail.hidden = true;
      }
      const opening = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(opening));
      toggle.setAttribute('aria-label', `${opening ? 'Hide' : 'Show'} ${row.dataset.positionSymbol} setup and sector charts`);
      row.classList.toggle('is-open', opening); detail.hidden = !opening;
      if (opening) {
        renderSetupChartForSymbol($('[data-position-chart-shell]', detail), row.dataset.positionSymbol);
        openPositionToggle = toggle;
      } else if (openPositionToggle === toggle) openPositionToggle = null;
      return;
    }
    const ps = e.target.closest('[data-sort-pos]');
    if (ps) { const k = ps.dataset.sortPos; state.posSort = { key: k, dir: state.posSort.key === k ? -state.posSort.dir : 1 }; return render(); }
    const ts = e.target.closest('[data-sort-trade]');
    if (ts) { const k = ts.dataset.sortTrade; state.tradeSort = { key: k, dir: state.tradeSort.key === k ? -state.tradeSort.dir : -1 }; return render(); }
    if (e.target.closest('[data-ext-toggle]')) { state.extBy = state.extBy === 'pct' ? 'date' : 'pct'; return render(); }
  });
  $$('.bl-chip').forEach(chip => chip.addEventListener('click', () => {
    const g = chip.dataset.g;
    state[g] = chip.dataset.v;
    $$(`.bl-chip[data-g="${g}"]`).forEach(c => c.classList.toggle('on', c === chip));
    render();
  }));
  const qInput = $('#bl-q');
  if (qInput) qInput.addEventListener('input', () => { state.q = qInput.value; render(); });
  const reset = $('#bl-reset');
  if (reset) reset.addEventListener('click', () => {
    state.q = ''; state.asset = 'All'; state.status = 'All';
    if (qInput) qInput.value = '';
    $$('.bl-chip').forEach(c => c.classList.toggle('on', c.dataset.v === 'All' || c.dataset.v === 'All assets' || c.textContent.startsWith('All')));
    render();
  });
  const exportBtn = $('#bl-export');
  if (exportBtn) exportBtn.addEventListener('click', () => {
    const esc = v => `"${String(v).replace(/"/g, '""')}"`;
    const lines = [['table', 'symbol', 'type', 'side', 'strike', 'expiry', 'since_entry'].join(',')];
    positions.forEach(p => lines.push(['position', p.sym, p.type, p.side, p.strike, p.expiry, p.since].map(esc).join(',')));
    ['buy', 'sell'].forEach(k => trades[k].forEach(t =>
      lines.push([k, t.sym, t.asset, t.inst, '×' + t.fills, t.pnlTxt, t.status].map(esc).join(','))));
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'zonted-trading-snapshot.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  document.querySelector('main.bl').classList.add('bl-enhanced');
  render();
})();
