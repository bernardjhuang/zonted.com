(() => {
  'use strict';

  const shell = document.querySelector('#gpt-brief-shell');
  if (!shell) return;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  const finite = value => Number.isFinite(Number(value)) ? Number(value) : null;
  const signed = (value, digits = 1, suffix = '') => {
    const number = finite(value);
    if (number == null) return '—';
    return `${number >= 0 ? '+' : '−'}${Math.abs(number).toFixed(digits)}${suffix}`;
  };
  const shortDate = value => {
    const date = new Date(`${value}T12:00:00Z`);
    return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  };
  const formatDate = value => {
    const date = new Date(`${value}T12:00:00Z`);
    return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  };
  const formatMarketCap = value => {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return String(value);
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(amount >= 10e9 ? 1 : 2)}B`;
    return `$${(amount / 1e6).toFixed(0)}M`;
  };
  const point = (x, y) => `${x.toFixed(1)},${y.toFixed(1)}`;

  function renderMarketChart(symbol, label, record, kind) {
    const dates = record?.dates || [];
    const close = (record?.close || []).map(finite);
    const vwap = (record?.vwap || []).map(finite);
    const z50 = (record?.z50 || []).map(finite);
    if (dates.length < 2 || close.length !== dates.length || vwap.length !== dates.length || z50.length !== dates.length) {
      return '<p class="gpt-chart-error">Chart data unavailable.</p>';
    }

    const W = 560, H = 304, L = 12, R = 50, PT = 12, PB = 178, ZT = 211, ZB = 276;
    const iw = W - L - R, n = dates.length;
    const x = index => L + index / (n - 1) * iw;
    const priceValues = [...close, ...vwap].filter(value => value != null);
    let lo = Math.min(...priceValues), hi = Math.max(...priceValues);
    const pad = Math.max((hi - lo) * 0.06, Math.max(Math.abs(hi), 1) * 0.005);
    lo -= pad; hi += pad;
    const yp = value => PT + (hi - value) / (hi - lo) * (PB - PT);
    const zValues = z50.filter(value => value != null);
    const zLimit = Math.max(2, ...zValues.map(value => Math.abs(value) * 1.08));
    const yz = value => ZT + (zLimit - value) / (2 * zLimit) * (ZB - ZT);
    const grid = [], labels = [];

    for (let i = 1; i < n; i += 1) {
      if (dates[i].slice(5, 7) !== dates[i - 1].slice(5, 7)) {
        grid.push(`<line x1="${x(i).toFixed(1)}" y1="${PT}" x2="${x(i).toFixed(1)}" y2="${ZB}" class="gpt-chart-rule"/>`);
        labels.push(`<text x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle" class="gpt-chart-axis">${esc(shortDate(dates[i]).split(' ')[0])}</text>`);
      }
    }
    for (let index = 0; index < 3; index += 1) {
      const value = lo + (hi - lo) * index / 2;
      grid.push(`<line x1="${L}" y1="${yp(value).toFixed(1)}" x2="${L + iw}" y2="${yp(value).toFixed(1)}" class="gpt-chart-rule"/>`);
      labels.push(`<text x="${W - 2}" y="${(yp(value) + 3.5).toFixed(1)}" text-anchor="end" class="gpt-chart-axis">${value >= 100 ? value.toFixed(0) : value.toFixed(1)}</text>`);
    }
    [1, 0, -1].forEach(value => {
      grid.push(`<line x1="${L}" y1="${yz(value).toFixed(1)}" x2="${L + iw}" y2="${yz(value).toFixed(1)}" class="${value === 0 ? 'gpt-chart-zero' : 'gpt-chart-threshold'}"/>`);
      labels.push(`<text x="${W - 2}" y="${(yz(value) + 3.5).toFixed(1)}" text-anchor="end" class="gpt-chart-axis">${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value)}</text>`);
    });

    const pricePoints = close.map((value, index) => point(x(index), yp(value))).join(' ');
    const vwapPoints = vwap.map((value, index) => point(x(index), yp(value))).join(' ');
    const zRuns = [];
    let active = [];
    let activeClass = '';
    z50.forEach((value, index) => {
      if (value == null) {
        if (active.length > 1) zRuns.push([activeClass, active]);
        active = []; activeClass = '';
        return;
      }
      const nextClass = value >= 1 ? 'gpt-chart-z--positive' : value <= -1 ? 'gpt-chart-z--negative' : 'gpt-chart-z--neutral';
      if (!activeClass) {
        activeClass = nextClass; active = [[index, value]];
      } else if (nextClass === activeClass) {
        active.push([index, value]);
      } else {
        active.push([index, value]);
        if (active.length > 1) zRuns.push([activeClass, active]);
        activeClass = nextClass; active = [[index, value]];
      }
    });
    if (active.length > 1) zRuns.push([activeClass, active]);
    const zPaths = zRuns.map(([className, values]) => `<polyline points="${values.map(([index, value]) => point(x(index), yz(value))).join(' ')}" class="gpt-chart-z ${className}"/>`).join('');
    const latest = record.latest || {};
    const zClass = finite(latest.z50) >= 1 ? 'is-positive' : finite(latest.z50) <= -1 ? 'is-negative' : '';
    const aria = `${symbol} ${kind} chart from ${dates[0]} through ${dates[n - 1]}. Latest price ${latest.price}, year-to-date return ${signed(latest.ytd_return_pct, 1, ' percent')}, and 50-session z-score ${signed(latest.z50, 2)}.`;

    return `<figure class="gpt-market-chart" data-chart-symbol="${esc(symbol)}">
      <figcaption>
        <span><strong>${esc(symbol)}</strong><small>${esc(label)}</small></span>
        <span class="gpt-chart-stats"><b>${signed(latest.ytd_return_pct, 1, '%')} YTD</b><b class="${zClass}">${signed(latest.z50, 2)} Z</b></span>
      </figcaption>
      <div class="gpt-chart-key"><span>Price</span><span>YTD VWAP</span><span>50D Z-score</span></div>
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(aria)}">
        ${grid.join('')}${labels.join('')}
        <text x="${L}" y="${ZT - 7}" class="gpt-chart-label">50D Z-SCORE</text>
        <polyline points="${vwapPoints}" class="gpt-chart-vwap"/>
        <polyline points="${pricePoints}" class="gpt-chart-price"/>
        ${zPaths}
      </svg>
    </figure>`;
  }

  let chartPromise = null;
  const loadChartPayload = () => {
    if (!chartPromise) {
      chartPromise = fetch(shell.dataset.chartUrl, { credentials: 'same-origin' })
        .then(response => {
          if (!response.ok) throw new Error(`chart data HTTP ${response.status}`);
          return response.json();
        })
        .catch(error => { chartPromise = null; throw error; });
    }
    return chartPromise;
  };

  async function renderCharts(card, event) {
    const chartShell = card.querySelector('[data-gpt-charts]');
    if (!chartShell || chartShell.dataset.rendered === 'true' || chartShell.dataset.loading === 'true') return;
    chartShell.dataset.loading = 'true';
    chartShell.setAttribute('aria-busy', 'true');
    chartShell.innerHTML = '<p class="gpt-chart-loading">Loading YTD stock and sector charts…</p>';
    try {
      const payload = await loadChartPayload();
      const mapping = payload.events?.[event.id];
      const stock = payload.series?.[mapping?.stock];
      const sector = payload.series?.[mapping?.sector];
      if (!mapping || !stock || !sector) throw new Error('chart mapping unavailable');
      chartShell.innerHTML = `<div class="gpt-charts-heading"><h3>Price context</h3><span>Through ${esc(formatDate(payload.last_bar))} · same YTD window and 50-day Z-score</span></div>
        <div class="gpt-chart-grid">
          ${renderMarketChart(mapping.stock, 'Stock', stock, 'stock')}
          ${renderMarketChart(mapping.sector, mapping.sector_name, sector, 'sector')}
        </div>`;
      chartShell.dataset.rendered = 'true';
    } catch (error) {
      console.error('Unable to load GPT brief charts', error);
      chartShell.innerHTML = '<p class="gpt-chart-error">Price charts failed to load.</p>';
    } finally {
      delete chartShell.dataset.loading;
      chartShell.removeAttribute('aria-busy');
    }
  }

  function renderEvent(event, index) {
    const sources = event.sources.map(source => `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.label)}</a>`).join(' · ');
    const confidence = Math.round(Number(event.confidence) * 100);
    return `<details class="brief-risk-card gpt-catalyst-card" data-event-id="${esc(event.id)}" data-tier="${esc(event.tier)}" data-primary-ticker="${esc(event.primary_ticker)}">
      <summary class="gpt-card-summary">
        <span class="gpt-card-chevron" aria-hidden="true">›</span>
        <span class="gpt-summary-main">
          <span class="gpt-summary-heading"><span class="gpt-rank">${String(index + 1).padStart(2, '0')}</span><code class="brief-ticker">${esc(event.primary_ticker)}</code><strong class="gpt-catalyst-date">${esc(event.date)}</strong></span>
          <span class="gpt-plain-summary">${esc(event.plain_summary)}</span>
          <span class="gpt-summary-meta"><span>${esc(event.sector)}</span><span>${esc(event.category)}</span></span>
        </span>
        <span class="gpt-risk-badge" data-grade="${esc(event.binary_grade.toLowerCase())}">${esc(event.binary_grade)} move risk</span>
      </summary>
      <div class="gpt-card-body">
        <div class="gpt-plain-grid" aria-label="Quick read">
          <section class="gpt-plain-outcome gpt-plain-good"><h4>Good news</h4><p>${esc(event.plain_good)}</p></section>
          <section class="gpt-plain-outcome gpt-plain-bad"><h4>Bad news</h4><p>${esc(event.plain_bad)}</p></section>
          <section class="gpt-plain-outcome gpt-plain-watch"><h4>What to watch</h4><p>${esc(event.plain_watch)}</p></section>
        </div>
        <section class="gpt-charts" data-gpt-charts aria-label="YTD stock and sector price charts"></section>
        <details class="gpt-full-research">
          <summary>Full research and sources</summary>
          <div class="gpt-research-body">
            <p class="brief-para"><strong>${esc(event.primary_ticker)} snapshot:</strong> ${formatMarketCap(event.market_cap_usd)} market cap · $${Number(event.reference_price).toFixed(2)} reference · ${esc(event.binary_grade)} binary grade · source/date confidence ${confidence}%</p>
            <p class="brief-para"><strong>Exact trigger:</strong> ${esc(event.trigger)}</p>
            <p class="brief-para"><strong>Why it matters:</strong> ${esc(event.implication)}</p>
            <ul class="brief-bullets"><li><strong>White swan:</strong> ${esc(event.white_swan)}</li><li><strong>Base case:</strong> ${esc(event.base_case)}</li><li><strong>Black swan:</strong> ${esc(event.black_swan)}</li></ul>
            <p class="brief-para"><strong>Why it may be mispriced:</strong> ${esc(event.why_mispriced)}</p>
            <p class="brief-para"><strong>Expected move:</strong> ${esc(event.magnitude)}</p>
            <p class="brief-para"><strong>Research plan:</strong> ${esc(event.action)}</p>
            <p class="brief-para"><strong>What would prove this wrong:</strong> ${esc(event.invalidation)}</p>
            <p class="brief-para"><strong>Sources:</strong> ${sources}</p>
          </div>
        </details>
      </div>
    </details>`;
  }

  fetch(shell.dataset.url, { credentials: 'same-origin' })
    .then(response => {
      if (!response.ok) throw new Error(`GPT brief fetch failed: ${response.status}`);
      return response.json();
    })
    .then(data => {
      const sectorCount = new Set(data.events.map(event => event.sector)).size;
      shell.innerHTML = `
        <div class="position-head"><h2 id="gpt-brief-heading">Events that could move a stock</h2><span>${data.events.length} events · ${sectorCount} sectors · ${formatDate(data.window_start)} → ${formatDate(data.window_end)} · 6:30 AM CT cadence</span></div>
        <p class="trading-takeaway">${esc(data.summary)}</p>
        <p class="gpt-quick-read"><strong>Quick read:</strong> Open a stock for its upside, downside, YTD chart, and sector comparison. Full research stays folded.</p>
        <div class="brief-log gpt-brief-list" data-gpt-brief-as-of="${esc(data.as_of)}">${data.events.map(renderEvent).join('')}</div>
        <details class="trading-method"><summary>How this list was picked</summary><ul class="brief-bullets">${data.context.map(item => `<li>${esc(item)}</li>`).join('')}</ul><p>${esc(data.methodology)}</p></details>
        <p class="trading-note">Research and monitoring only. Market data is adjusted daily close data, not an executable quote or recommendation.</p>`;
      shell.querySelectorAll('.gpt-catalyst-card').forEach((card, index) => {
        card.addEventListener('toggle', () => { if (card.open) renderCharts(card, data.events[index]); });
      });
    })
    .catch(error => {
      shell.innerHTML = `<div class="position-head"><h2>Events that could move a stock</h2></div><p class="trading-note">Brief unavailable: ${esc(error.message)}</p>`;
      console.error(error);
    });
})();
