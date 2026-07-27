(() => {
  'use strict';

  const dialog = document.getElementById('hypothesis-chart-dialog');
  const configSource = document.getElementById('scan-chart-config');
  const shell = dialog?.querySelector('[data-hypothesis-chart-shell]');
  const title = dialog?.querySelector('[data-hypothesis-chart-title]');
  const closeButton = dialog?.querySelector('[data-hypothesis-chart-close]');
  const launchers = [...document.querySelectorAll('[data-hypothesis-chart-open]')];
  if (!dialog || !configSource || !shell || !title || !closeButton || !launchers.length) return;

  let config;
  try {
    config = JSON.parse(configSource.textContent);
  } catch (error) {
    console.error('Invalid hypothesis chart config', error);
    return;
  }

  const $ = (selector, root = document) => root.querySelector(selector);
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const W = 1120;
  const PXH = 280;
  const SUBH = 78;
  const GAP = 14;
  const AXISH = 22;
  const ML = 8;
  const MR = 66;
  const H = PXH + (SUBH + GAP) * 2 + AXISH;
  const COLORS = {
    up: '#1a7a3c', down: '#8f2222', earn: '#4a3aa7', ytd: '#6b655c',
    pos: '#2a78d6', neg: '#e34948', mut: '#a09a90',
  };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[character]));
  const signed = (value, suffix = '') => value == null
    ? '—'
    : `${Number(value) >= 0 ? '+' : '−'}${Math.abs(Number(value)).toFixed(2)}${suffix}`;
  const shortDate = iso => iso ? `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(8, 10))}` : '—';
  const point = (x, y) => `${x.toFixed(1)},${y.toFixed(1)}`;

  let chartDataPromise;
  let sectorDataPromise;
  let activeLauncher = null;
  let renderToken = 0;

  const fetchCharts = (key, url) => {
    if (!url) return Promise.reject(new Error(`Missing ${key} chart URL`));
    if (key === 'stock' && chartDataPromise) return chartDataPromise;
    if (key === 'sector' && sectorDataPromise) return sectorDataPromise;
    const request = fetch(url, { credentials: 'same-origin' })
      .then(response => {
        if (!response.ok) throw new Error(`${key} chart data HTTP ${response.status}`);
        return response.json();
      })
      .then(payload => payload.charts || {})
      .catch(error => {
        if (key === 'stock') chartDataPromise = null;
        if (key === 'sector') sectorDataPromise = null;
        throw error;
      });
    if (key === 'stock') chartDataPromise = request;
    if (key === 'sector') sectorDataPromise = request;
    return request;
  };

  function wireSectorChart(figure) {
    if (!figure || figure.dataset.comparisonWired === 'true') return;
    let data;
    try {
      data = JSON.parse(figure.dataset.d);
    } catch (error) {
      console.error('Invalid sector chart data', error);
      return;
    }
    const svg = $('svg', figure);
    const tooltip = $('.vwap-tip', figure);
    const crosshair = $('.vxh', figure);
    if (!svg || !tooltip || !crosshair || !data?.dates?.length || data.close?.length !== data.dates.length || data.vwap?.length !== data.dates.length) return;

    figure.dataset.comparisonWired = 'true';
    tooltip.setAttribute('aria-live', 'polite');
    svg.setAttribute('tabindex', '0');
    const viewBox = svg.viewBox.baseVal;
    const count = data.dates.length;
    const leftPad = 10;
    const rightPad = 58;
    let activeIndex = count - 1;

    const showPoint = (index, left, top) => {
      activeIndex = Math.max(0, Math.min(count - 1, index));
      const x = leftPad + activeIndex / (count - 1) * (viewBox.width - leftPad - rightPad);
      crosshair.setAttribute('x1', x);
      crosshair.setAttribute('x2', x);
      crosshair.removeAttribute('visibility');
      const difference = (data.close[activeIndex] / data.vwap[activeIndex] - 1) * 100;
      const z = data.z50?.[activeIndex];
      const date = document.createElement('b');
      date.textContent = data.dates[activeIndex];
      const nodes = [
        date, document.createElement('br'),
        document.createTextNode(`close ${Number(data.close[activeIndex]).toFixed(2)}`), document.createElement('br'),
        document.createTextNode(`vwap ${Number(data.vwap[activeIndex]).toFixed(2)}`), document.createElement('br'),
        document.createTextNode(`${difference >= 0 ? '+' : ''}${difference.toFixed(2)}%`),
      ];
      if (z != null) nodes.push(document.createElement('br'), document.createTextNode(`50d z ${z >= 0 ? '+' : ''}${Number(z).toFixed(2)}`));
      tooltip.replaceChildren(...nodes);
      tooltip.hidden = false;
      tooltip.style.left = `${Math.max(8, Math.min(figure.clientWidth - tooltip.offsetWidth - 8, left))}px`;
      tooltip.style.top = `${top}px`;
    };

    svg.addEventListener('pointermove', event => {
      const rectangle = svg.getBoundingClientRect();
      const virtualX = (event.clientX - rectangle.left) / rectangle.width * viewBox.width;
      const index = Math.max(0, Math.min(count - 1, Math.round((virtualX - leftPad) / (viewBox.width - leftPad - rightPad) * (count - 1))));
      const figureRectangle = figure.getBoundingClientRect();
      let left = event.clientX - figureRectangle.left + 14;
      showPoint(index, left, event.clientY - figureRectangle.top - 10);
      if (left + tooltip.offsetWidth > figureRectangle.width - 8) {
        left = event.clientX - figureRectangle.left - tooltip.offsetWidth - 14;
        tooltip.style.left = `${Math.max(8, left)}px`;
      }
    });
    svg.addEventListener('pointerleave', () => {
      if (document.activeElement !== svg) {
        tooltip.hidden = true;
        crosshair.setAttribute('visibility', 'hidden');
      }
    });
    svg.addEventListener('focus', () => showPoint(activeIndex, figure.clientWidth - 150, svg.offsetTop + 18));
    svg.addEventListener('keydown', event => {
      let next = null;
      if (event.key === 'ArrowLeft') next = activeIndex - 1;
      if (event.key === 'ArrowRight') next = activeIndex + 1;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = count - 1;
      if (next == null) return;
      event.preventDefault();
      const clamped = Math.max(0, Math.min(count - 1, next));
      showPoint(clamped, leftPad + clamped / (count - 1) * (figure.clientWidth - leftPad - rightPad) + 10, svg.offsetTop + 18);
    });
    svg.addEventListener('blur', () => {
      tooltip.hidden = true;
      crosshair.setAttribute('visibility', 'hidden');
    });
  }

  function buildStockCard(symbol, record, detailId) {
    const series = record.series;
    const count = series.dates.length;
    const innerWidth = W - ML - MR;
    const x = index => ML + (index + 0.5) / count * innerWidth;
    const candleWidth = Math.max(1.6, innerWidth / count * 0.6);
    const earningsPoints = series.ev.map((value, index) => value == null ? null : [index, value]).filter(Boolean);
    const priceValues = [...series.l, ...series.h, ...series.yv, ...earningsPoints.map(pair => pair[1])];
    let low = Math.min(...priceValues);
    let high = Math.max(...priceValues);
    const padding = Math.max((high - low) * 0.05, Math.max(Math.abs(high), 1) * 0.005);
    low -= padding;
    high += padding;
    const priceY = value => (high - value) / (high - low) * (PXH - 8) + 4;
    const parts = [];
    const axis = [];

    for (let index = 1; index < count; index += 1) {
      if (series.dates[index].slice(5, 7) !== series.dates[index - 1].slice(5, 7)) {
        parts.push(`<line x1="${x(index).toFixed(1)}" y1="0" x2="${x(index).toFixed(1)}" y2="${H - AXISH}" class="sg"/>`);
        axis.push(`<text x="${x(index).toFixed(1)}" y="${H - 7}" class="sa" text-anchor="middle">${MONTHS[Number(series.dates[index].slice(5, 7)) - 1]}</text>`);
      }
    }
    for (let step = 0; step < 4; step += 1) {
      const value = low + (high - low) * step / 3;
      parts.push(`<line x1="${ML}" y1="${priceY(value).toFixed(1)}" x2="${ML + innerWidth}" y2="${priceY(value).toFixed(1)}" class="sg"/><text x="${ML + innerWidth + 6}" y="${(priceY(value) + 3.5).toFixed(1)}" class="sa">${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}</text>`);
    }
    for (let index = 0; index < count; index += 1) {
      const color = series.c[index] >= series.o[index] ? COLORS.up : COLORS.down;
      const top = Math.max(series.o[index], series.c[index]);
      const bottom = Math.min(series.o[index], series.c[index]);
      parts.push(`<line x1="${x(index).toFixed(1)}" y1="${priceY(series.h[index]).toFixed(1)}" x2="${x(index).toFixed(1)}" y2="${priceY(series.l[index]).toFixed(1)}" stroke="${color}" stroke-width="1"/><rect x="${(x(index) - candleWidth / 2).toFixed(1)}" y="${priceY(top).toFixed(1)}" width="${candleWidth.toFixed(1)}" height="${Math.max(0.8, priceY(bottom) - priceY(top)).toFixed(1)}" fill="${color}"/>`);
    }
    parts.push(`<polyline points="${series.yv.map((value, index) => point(x(index), priceY(value))).join(' ')}" fill="none" stroke="${COLORS.ytd}" stroke-width="1.5" stroke-dasharray="5 4"/>`);
    if (earningsPoints.length) {
      parts.push(`<polyline points="${earningsPoints.map(([index, value]) => point(x(index), priceY(value))).join(' ')}" fill="none" stroke="${COLORS.earn}" stroke-width="2"/>`);
      parts.push(`<text x="${x(earningsPoints[0][0]).toFixed(1)}" y="${(priceY(earningsPoints[0][1]) - 6).toFixed(1)}" class="sa" fill="${COLORS.earn}" text-anchor="middle">E</text>`);
    }
    const tags = [[series.c[count - 1], '#1a1815', series.c[count - 1].toFixed(2)]];
    if (earningsPoints.length) tags.push([earningsPoints.at(-1)[1], COLORS.earn, earningsPoints.at(-1)[1].toFixed(2)]);
    tags.push([series.yv[count - 1], COLORS.ytd, series.yv[count - 1].toFixed(2)]);
    tags.forEach(([value, color, text]) => parts.push(`<text x="${W - 2}" y="${(priceY(value) + 3.5).toFixed(1)}" class="st" fill="${color}" text-anchor="end">${text}</text>`));

    const spreadTop = PXH + GAP;
    const spreadValues = series.sp.filter(value => value != null);
    const spreadMaximum = Math.max(2, ...spreadValues.map(value => Math.abs(value) * 1.1));
    const spreadY = value => spreadTop + (spreadMaximum - value) / (2 * spreadMaximum) * SUBH;
    parts.push(`<text x="${ML}" y="${spreadTop + 10}" class="sl">Spread Z vs SPY (50d)</text><line x1="${ML}" y1="${spreadY(0).toFixed(1)}" x2="${ML + innerWidth}" y2="${spreadY(0).toFixed(1)}" class="sz"/>`);
    for (let index = 1; index < count; index += 1) {
      if (series.sp[index - 1] == null || series.sp[index] == null) continue;
      parts.push(`<line x1="${x(index - 1).toFixed(1)}" y1="${spreadY(series.sp[index - 1]).toFixed(1)}" x2="${x(index).toFixed(1)}" y2="${spreadY(series.sp[index]).toFixed(1)}" stroke="${series.sp[index] >= 0 ? COLORS.up : COLORS.neg}" stroke-width="1.8"/>`);
    }
    const lastSpread = [...series.sp].reverse().find(value => value != null);
    if (lastSpread != null) parts.push(`<text x="${W - 2}" y="${(spreadY(lastSpread) + 3.5).toFixed(1)}" class="st" fill="${lastSpread >= 0 ? COLORS.up : COLORS.neg}" text-anchor="end">${signed(lastSpread)}</text>`);

    const distanceTop = spreadTop + SUBH + GAP;
    const distanceValues = series.dz.filter(value => value != null);
    const distanceMaximum = Math.max(2.5, ...distanceValues.map(value => Math.abs(value) * 1.1));
    const distanceY = value => distanceTop + (distanceMaximum - value) / (2 * distanceMaximum) * SUBH;
    parts.push(`<text x="${ML}" y="${distanceTop + 10}" class="sl">Dist Z — YTD VWAP</text><line x1="${ML}" y1="${distanceY(0).toFixed(1)}" x2="${ML + innerWidth}" y2="${distanceY(0).toFixed(1)}" class="sz"/>`);
    [1, -1].forEach(level => parts.push(`<line x1="${ML}" y1="${distanceY(level).toFixed(1)}" x2="${ML + innerWidth}" y2="${distanceY(level).toFixed(1)}" class="sd"/>`));
    const barWidth = Math.max(1.2, innerWidth / count * 0.55);
    series.dz.forEach((value, index) => {
      if (value == null) return;
      const color = value > 1 ? COLORS.pos : value < -1 ? COLORS.neg : COLORS.mut;
      parts.push(`<rect x="${(x(index) - barWidth / 2).toFixed(1)}" y="${Math.min(distanceY(0), distanceY(value)).toFixed(1)}" width="${barWidth.toFixed(1)}" height="${Math.abs(distanceY(value) - distanceY(0)).toFixed(1)}" fill="${color}"/>`);
    });
    const lastDistance = [...series.dz].reverse().find(value => value != null);

    const titleId = `${detailId}-stock-title`;
    const descriptionId = `${detailId}-stock-description`;
    const stats = record.stats || {};
    const earningsSide = stats.evwap_side == null ? '—' : `${stats.evwap_side ? '▲' : '▼'} ${stats.evwap_streak}d`;
    const badgeClass = ({ 'ENTER+': 'setup-b--long', ENTER: 'setup-b--long', 'SHORT+': 'setup-b--short', SHORT: 'setup-b--short', BREAKING: 'setup-b--break' })[record.label] || 'setup-b--watch';
    const lastEarnings = earningsPoints.length ? earningsPoints.at(-1)[1] : null;
    const description = `${symbol} setup chart with ${count} daily candles from ${series.dates[0]} through ${series.dates[count - 1]}. Latest close ${series.c[count - 1].toFixed(2)}, YTD VWAP ${series.yv[count - 1].toFixed(2)}, earnings VWAP ${lastEarnings == null ? 'unavailable' : lastEarnings.toFixed(2)}, Spread Z ${lastSpread == null ? 'unavailable' : signed(lastSpread)}, and Dist Z ${lastDistance == null ? 'unavailable' : signed(lastDistance)}. Focus the chart and use Left and Right Arrow, Home, or End to inspect exact historical values.`;

    return `<section class="setup-card scan-setup-card"><header><b id="${titleId}">${esc(symbol)}</b><span>${esc(record.sector)}</span><span class="setup-b ${badgeClass}">${esc(record.label)}</span><span class="setup-stats">spread Z <b>${signed(stats.spread_z)}</b> · dist Z <b>${signed(stats.dist_z)}</b> · vs earn VWAP <b>${signed(stats.evwap_pct, '%')}</b> (${earningsSide}) · next earnings ${shortDate(stats.next_earn)}</span></header><p class="setup-read">${esc(record.read)}</p><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" tabindex="0" aria-labelledby="${titleId} ${descriptionId}"><desc id="${descriptionId}">${esc(description)}</desc>${parts.join('')}${axis.join('')}<line class="sx" x1="0" y1="0" x2="0" y2="${H - AXISH}" visibility="hidden"/></svg><div class="setup-tip" aria-live="polite" hidden></div></section>`;
  }

  function wireStockChart(card, record) {
    const series = record.series;
    const svg = $('svg', card);
    const tooltip = $('.setup-tip', card);
    const crosshair = $('.sx', card);
    if (!svg || !tooltip || !crosshair) return;
    const count = series.dates.length;
    const innerWidth = W - ML - MR;
    const x = index => ML + (index + 0.5) / count * innerWidth;
    let activeIndex = count - 1;

    const showPoint = (index, left, top) => {
      activeIndex = Math.max(0, Math.min(count - 1, index));
      const horizontal = x(activeIndex);
      crosshair.setAttribute('x1', horizontal);
      crosshair.setAttribute('x2', horizontal);
      crosshair.removeAttribute('visibility');
      const values = [
        ['close', series.c[activeIndex]], ['earn vwap', series.ev[activeIndex]],
        ['ytd vwap', series.yv[activeIndex]], ['spread z', series.sp[activeIndex]],
        ['dist z', series.dz[activeIndex]],
      ].filter(([, value]) => value != null);
      const date = document.createElement('b');
      date.textContent = series.dates[activeIndex];
      const nodes = [date];
      values.forEach(([label, value]) => nodes.push(document.createElement('br'), document.createTextNode(`${label} ${Number(value).toFixed(2)}`)));
      tooltip.replaceChildren(...nodes);
      tooltip.hidden = false;
      tooltip.style.left = `${Math.max(8, Math.min(card.clientWidth - tooltip.offsetWidth - 8, left))}px`;
      tooltip.style.top = `${top}px`;
    };

    svg.addEventListener('pointermove', event => {
      const rectangle = svg.getBoundingClientRect();
      const virtualX = (event.clientX - rectangle.left) / rectangle.width * W;
      const index = Math.max(0, Math.min(count - 1, Math.floor((virtualX - ML) / innerWidth * count)));
      const cardRectangle = card.getBoundingClientRect();
      let left = event.clientX - cardRectangle.left + 14;
      showPoint(index, left, event.clientY - cardRectangle.top - 10);
      if (left + tooltip.offsetWidth > cardRectangle.width - 8) {
        left = event.clientX - cardRectangle.left - tooltip.offsetWidth - 14;
        tooltip.style.left = `${Math.max(8, left)}px`;
      }
    });
    svg.addEventListener('pointerleave', () => {
      if (document.activeElement !== svg) {
        tooltip.hidden = true;
        crosshair.setAttribute('visibility', 'hidden');
      }
    });
    svg.addEventListener('focus', () => showPoint(activeIndex, card.clientWidth - 150, svg.offsetTop + 18));
    svg.addEventListener('keydown', event => {
      let next = null;
      if (event.key === 'ArrowLeft') next = activeIndex - 1;
      if (event.key === 'ArrowRight') next = activeIndex + 1;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = count - 1;
      if (next == null) return;
      event.preventDefault();
      const clamped = Math.max(0, Math.min(count - 1, next));
      showPoint(clamped, x(clamped) / W * card.clientWidth + 10, svg.offsetTop + 18);
    });
    svg.addEventListener('blur', () => {
      tooltip.hidden = true;
      crosshair.setAttribute('visibility', 'hidden');
    });
  }

  async function renderCharts(symbol, token) {
    shell.dataset.symbol = symbol;
    delete shell.dataset.rendered;
    shell.setAttribute('aria-busy', 'true');
    shell.innerHTML = '<p class="hyp-chart-loading">Loading Spread Z and sector charts…</p>';

    let stockCharts;
    try {
      stockCharts = await fetchCharts('stock', config.url);
    } catch (error) {
      if (token !== renderToken) return;
      console.error('Unable to load hypothesis Spread Z data', error);
      shell.innerHTML = '<p class="hyp-chart-unavailable">Spread Z data failed to load. Open the Watchlist and try again.</p>';
      shell.removeAttribute('aria-busy');
      return;
    }
    if (token !== renderToken || shell.dataset.symbol !== symbol) return;

    const record = stockCharts[symbol];
    if (!record?.series?.dates?.length) {
      shell.innerHTML = `<div class="hyp-chart-unavailable"><strong>${esc(symbol)} is not in the current scanner universe.</strong><span>No completed-session Spread Z or sector chart is available from the Watchlist feed yet.</span><a href="/trading/watchlist/?chart=${encodeURIComponent(symbol)}#scan">Open Watchlist</a></div>`;
      shell.removeAttribute('aria-busy');
      shell.dataset.rendered = 'true';
      return;
    }

    title.textContent = `${symbol} · Spread Z + ${record.sector_etf} sector Z-score`;
    const grid = document.createElement('div');
    grid.className = 'scan-comparison-grid';
    const stockPane = document.createElement('div');
    stockPane.className = 'scan-stock-chart';
    stockPane.innerHTML = buildStockCard(symbol, record, dialog.id);
    grid.append(stockPane);
    shell.replaceChildren(grid);
    wireStockChart($('.scan-setup-card', stockPane), record);

    try {
      const sectorCharts = await fetchCharts('sector', config.vwap_url || '/trading/vwap-charts.json');
      if (token !== renderToken || shell.dataset.symbol !== symbol) return;
      const sectorMarkup = sectorCharts[record.sector_etf];
      if (sectorMarkup) {
        const sectorPane = document.createElement('div');
        sectorPane.className = 'scan-sector-chart';
        sectorPane.innerHTML = sectorMarkup;
        const sectorChart = $('.vwap-chart', sectorPane);
        sectorChart?.classList.remove('vwap-chart--spy');
        sectorPane.querySelector('.vwap-tip')?.replaceChildren();
        grid.append(sectorPane);
        wireSectorChart(sectorChart);
      } else {
        grid.insertAdjacentHTML('beforeend', `<p class="hyp-chart-unavailable">${esc(record.sector_etf)} sector chart is unavailable.</p>`);
      }
    } catch (error) {
      if (token === renderToken) {
        console.error('Unable to load hypothesis sector chart', error);
        grid.insertAdjacentHTML('beforeend', '<p class="hyp-chart-unavailable">Sector chart failed to load.</p>');
      }
    }

    if (token !== renderToken || shell.dataset.symbol !== symbol) return;
    shell.dataset.rendered = 'true';
    shell.removeAttribute('aria-busy');
  }

  const openDialog = launcher => {
    const symbol = launcher.dataset.hypothesisChartOpen?.toUpperCase();
    if (!symbol) return;
    activeLauncher = launcher;
    title.textContent = `${symbol} · scanner charts`;
    if (!dialog.open) dialog.showModal();
    if (shell.dataset.symbol === symbol && shell.dataset.rendered === 'true') return;
    renderToken += 1;
    renderCharts(symbol, renderToken);
  };

  launchers.forEach(launcher => launcher.addEventListener('click', () => openDialog(launcher)));
  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    activeLauncher?.focus();
  });
})();
