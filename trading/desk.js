/* Trading desk prototype runtime: live risk/performance data + sparkline hover.
   Fetches the SAME JSONs the live /trading/ page uses, so these surfaces
   cannot go stale the way an embedded snapshot does. */
(() => {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v, dp = 2) => Number(v).toFixed(dp);
  const signed = (v, dp = 2, suf = '') => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(dp) + suf;
  const prettyDate = iso => new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  const riskJournalData = fetch('/trading/risk-journal.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);

  /* ── status chips: three independent risk-appetite reads, all 0–10.
     Each updates on its own; a failed fetch leaves that chip's static
     fallback text in place. Stance color uses the Fable rubric bands
     (≥6.25 on, ≤3.75 off) so all three are judged on the same scale. ── */
  const setChip = (key, name, value, stanceText) => {
    const chip = $('.chip-' + key);
    if (!chip || !Number.isFinite(value)) return;
    chip.classList.remove('chip-on', 'chip-off', 'chip-neutral');
    chip.classList.add(value >= 6.25 ? 'chip-on' : value <= 3.75 ? 'chip-off' : 'chip-neutral');
    chip.innerHTML = '<span class="dot"></span>' + name + ' ' + esc(Math.round(value * 10) / 10);
    if (stanceText) chip.title = name + ' risk appetite — ' + stanceText + ' · ' + Math.round(value * 10) / 10 + '/10';
  };
  riskJournalData.then(d => {
    const latest = d && d.entries && d.entries[0];
    if (latest) setChip('gpt', 'GPT', Number(latest.risk_appetite), latest.stance);
  });
  fetch('/trading/fable-risk.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null).then(d => {
    const latest = d && d.entries && d.entries[0];
    if (latest) setChip('fable', 'Fable', Number(latest.rating), latest.verdict);
  });
  fetch('/trading/grok-risk/', { cache: 'no-cache' }).then(r => r.ok ? r.text() : '').catch(() => '').then(html => {
    const m = /Risk[\s-]*(On|Off|Neutral)\s*\((\d+(?:\.\d+)?)\s*\/\s*10\)/i.exec(html)
      || /(?:^|[^\d.])(\d+(?:\.\d+)?)\s*\/\s*10\b/.exec(html);
    if (m) setChip('grok', 'Grok', Number(m[2] !== undefined ? m[2] : m[1]), m[2] !== undefined ? 'Risk ' + m[1] : '');
  });

  /* ── position risk charts: levels + interactive metrics ─────────── */
  document.querySelectorAll('.position-risk-chart').forEach(chart => {
    const source = $('.spark-data[data-dates]', chart.closest('.pos'));
    if (!source) return;
    const dates = source.dataset.dates.split(',');
    const closes = source.dataset.closes.split(',').map(Number);
    const entry = Number(source.dataset.entry);
    const kill = Number(chart.dataset.kill);
    source.remove();
    if (dates.length < 2 || dates.length !== closes.length || !closes.every(Number.isFinite) || !Number.isFinite(entry) || !Number.isFinite(kill)) return;

    const W = 760, H = 190, left = 46, right = 22, top = 18, bottom = 30;
    const rawLow = Math.min(...closes, entry, kill), rawHigh = Math.max(...closes, entry, kill);
    const padding = Math.max((rawHigh - rawLow) * .08, rawHigh * .01);
    const lo = rawLow - padding, hi = rawHigh + padding;
    const x = i => left + i / (closes.length - 1) * (W - left - right);
    const y = value => top + (hi - value) / (hi - lo || 1) * (H - top - bottom);
    const points = closes.map((value, i) => x(i).toFixed(2) + ',' + y(value).toFixed(2)).join(' ');
    const last = closes[closes.length - 1];
    const symbol = $('.pos-sym', chart.closest('.pos'))?.textContent.trim() || 'Position';
    const tooltipId = 'prc-tooltip-' + symbol.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    chart.insertAdjacentHTML('beforeend',
      '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" tabindex="0" aria-describedby="' + tooltipId + '" aria-label="' +
      esc(symbol + ' 60-session price history. Horizontal invalidation at $' + num(kill) + ', horizontal entry price at $' + num(entry) + ', latest $' + num(last) + '. Hover or use arrow keys for daily metrics.') + '">' +
      '<line class="prc-grid" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(hi).toFixed(2) + '" y2="' + y(hi).toFixed(2) + '"></line>' +
      '<line class="prc-grid" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(lo).toFixed(2) + '" y2="' + y(lo).toFixed(2) + '"></line>' +
      '<line class="prc-invalidation" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(kill).toFixed(2) + '" y2="' + y(kill).toFixed(2) + '"></line>' +
      '<text class="prc-label prc-label-kill" x="' + (left + 5) + '" y="' + (y(kill) - 6).toFixed(2) + '">Invalidation $' + num(kill) + '</text>' +
      '<line class="prc-entry-level" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(entry).toFixed(2) + '" y2="' + y(entry).toFixed(2) + '"></line>' +
      '<text class="prc-label prc-label-entry-level" x="' + (left + 5) + '" y="' + (y(entry) - 6).toFixed(2) + '">Entry $' + num(entry) + '</text>' +
      '<polyline class="prc-price" points="' + points + '"></polyline>' +
      '<circle class="prc-now" cx="' + x(closes.length - 1).toFixed(2) + '" cy="' + y(last).toFixed(2) + '" r="4"></circle>' +
      '<text class="prc-label prc-label-now" x="' + (W - right - 5) + '" y="' + (y(last) - 7).toFixed(2) + '">Now $' + num(last) + '</text>' +
      '<line class="prc-hover-line" x1="0" x2="0" y1="' + top + '" y2="' + (H - bottom) + '" hidden></line>' +
      '<circle class="prc-hover-dot" cx="0" cy="0" r="4" hidden></circle>' +
      '<text class="prc-axis" x="' + left + '" y="' + (H - 7) + '">' + esc(dates[0]) + '</text>' +
      '<text class="prc-axis prc-axis-end" x="' + (W - right) + '" y="' + (H - 7) + '">' + esc(dates[dates.length - 1]) + '</text></svg>' +
      '<div class="prc-tooltip" id="' + tooltipId + '" role="status" aria-live="polite" hidden></div>');

    const svg = $('svg', chart), tooltip = $('.prc-tooltip', chart);
    const hoverLine = $('.prc-hover-line', svg), hoverDot = $('.prc-hover-dot', svg);
    let activeIndex = closes.length - 1;
    const hideMetrics = () => {
      tooltip.hidden = true;
      hoverLine.setAttribute('hidden', '');
      hoverDot.setAttribute('hidden', '');
    };
    const showMetrics = index => {
      activeIndex = Math.max(0, Math.min(closes.length - 1, index));
      const close = closes[activeIndex];
      const dayPct = activeIndex ? (close / closes[activeIndex - 1] - 1) * 100 : null;
      const vsEntry = close - entry, vsEntryPct = vsEntry / entry * 100;
      const room = close - kill, roomPct = room / kill * 100;
      const metric = (value, suffix = '') => '<em class="' + (value >= 0 ? 'up' : 'down') + '">' + signed(value, 1, suffix) + '</em>';
      const money = value => '<em class="' + (value >= 0 ? 'up' : 'down') + '">' + (value >= 0 ? '+' : '−') + '$' + Math.abs(value).toFixed(2) + '</em>';
      tooltip.innerHTML = '<b><span>' + esc(prettyDate(dates[activeIndex])) + '</span><strong>$' + num(close) + '</strong></b>' +
        '<span>Day ' + (dayPct == null ? '<em>—</em>' : metric(dayPct, '%')) + '</span>' +
        '<span>vs entry ' + money(vsEntry) + ' · ' + metric(vsEntryPct, '%') + '</span>' +
        '<span>room to invalidation ' + money(room) + ' · ' + metric(roomPct, '%') + '</span>';
      const hoverX = x(activeIndex), hoverY = y(close);
      hoverLine.setAttribute('x1', hoverX.toFixed(2));
      hoverLine.setAttribute('x2', hoverX.toFixed(2));
      hoverDot.setAttribute('cx', hoverX.toFixed(2));
      hoverDot.setAttribute('cy', hoverY.toFixed(2));
      hoverLine.removeAttribute('hidden');
      hoverDot.removeAttribute('hidden');
      tooltip.hidden = false;
      const svgRect = svg.getBoundingClientRect(), chartRect = chart.getBoundingClientRect();
      const pointLeft = svgRect.left - chartRect.left + hoverX / W * svgRect.width;
      const pointTop = svgRect.top - chartRect.top + hoverY / H * svgRect.height;
      const leftPx = Math.min(Math.max(8, pointLeft + 12), chart.clientWidth - tooltip.offsetWidth - 8);
      const topPx = Math.max(38, pointTop - tooltip.offsetHeight - 10);
      tooltip.style.left = leftPx + 'px';
      tooltip.style.top = topPx + 'px';
    };
    const pointerIndex = event => {
      const rect = svg.getBoundingClientRect();
      const viewX = (event.clientX - rect.left) / rect.width * W;
      return Math.round((viewX - left) / (W - left - right) * (closes.length - 1));
    };
    svg.addEventListener('pointermove', event => showMetrics(pointerIndex(event)));
    svg.addEventListener('pointerdown', event => showMetrics(pointerIndex(event)));
    svg.addEventListener('pointerleave', () => { if (document.activeElement !== svg) hideMetrics(); });
    svg.addEventListener('focus', () => showMetrics(activeIndex));
    svg.addEventListener('keydown', event => {
      let next = null;
      if (event.key === 'ArrowLeft') next = activeIndex - 1;
      if (event.key === 'ArrowRight') next = activeIndex + 1;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = closes.length - 1;
      if (next == null) return;
      event.preventDefault();
      showMetrics(next);
    });
    svg.addEventListener('blur', hideMetrics);
  });

  /* ── market rail: SPY/VIX YTD + cross-asset leadership ─────────── */
  const marketRoot = $('#market-overview-live');
  if (marketRoot) {
    const feed = path => fetch(path, { cache: 'no-cache' }).then(r => {
      if (!r.ok) throw new Error(path + ' returned ' + r.status);
      return r.json();
    });
    const parseMarkup = markup => {
      const template = document.createElement('template');
      template.innerHTML = markup || '';
      return template.content.firstElementChild;
    };
    const lastFinite = values => {
      for (let i = values.length - 1; i >= 0; i -= 1) if (values[i] != null && Number.isFinite(Number(values[i]))) return Number(values[i]);
      return null;
    };
    const rankVwap = (payload, symbols) => symbols.map(symbol => {
      const figure = parseMarkup(payload.charts && payload.charts[symbol]);
      if (!figure || !figure.dataset.d) return null;
      const data = JSON.parse(figure.dataset.d);
      return { symbol, name: symbol, z: lastFinite(data.z50 || []) };
    }).filter(row => row && Number.isFinite(row.z)).sort((a, b) => b.z - a.z);
    const rankCrypto = payload => Object.entries(payload.charts || {}).map(([symbol, markup]) => {
      const figure = parseMarkup(markup);
      if (!figure) return null;
      const name = $('figcaption span', figure)?.textContent.split('·')[0].trim() || symbol;
      return { symbol, name, z: Number(figure.dataset.spreadZ) };
    }).filter(row => row && Number.isFinite(row.z)).sort((a, b) => b.z - a.z);
    const splitRanks = rows => ({ leaders: rows.slice(0, 2), laggards: rows.slice(-2).reverse() });
    const rankGroup = (label, ranks, queryKey, hash) => {
      const chips = (rows, kind) => rows.map(row => {
        const href = '/trading/momentum/?' + queryKey + '=' + encodeURIComponent(row.symbol) + '#' + hash;
        return '<a class="market-rank-chip ' + kind + '" href="' + href + '" title="' + esc(row.name) + '"><b>' + esc(row.symbol) + '</b><em>' + signed(row.z, 2) + 'z</em></a>';
      }).join('');
      return '<section class="market-rank-group"><h4>' + esc(label) + '</h4>' +
        '<div class="market-rank-row"><span>Leaders</span><div>' + chips(ranks.leaders, 'leader') + '</div></div>' +
        '<div class="market-rank-row"><span>Laggards</span><div>' + chips(ranks.laggards, 'laggard') + '</div></div></section>';
    };

    Promise.all([
      feed('/trading/market-ytd.json'),
      feed('/trading/vwap-charts.json'),
      feed('/trading/crypto-charts.json'),
    ]).then(([market, vwap, crypto]) => {
      const points = Array.isArray(market.points) ? market.points : [];
      if (points.length < 2) throw new Error('market YTD history is empty');
      const W = 360, H = 210, x0 = 18, x1 = 342;
      const spyTop = 32, spyBottom = 91, vixTop = 124, vixBottom = 183;
      const x = i => x0 + i / (points.length - 1) * (x1 - x0);
      const domain = (values, includeZero) => {
        let low = Math.min(...values), high = Math.max(...values);
        if (includeZero) { low = Math.min(low, 0); high = Math.max(high, 0); }
        const padding = Math.max((high - low) * .08, .5);
        return [low - padding, high + padding];
      };
      const spyValues = points.map(row => Number(row.spy_ytd_percent));
      const vixValues = points.map(row => Number(row.vix));
      const [spyLow, spyHigh] = domain(spyValues, true), [vixLow, vixHigh] = domain(vixValues, false);
      const spyY = value => spyTop + (spyHigh - value) / (spyHigh - spyLow || 1) * (spyBottom - spyTop);
      const vixY = value => vixTop + (vixHigh - value) / (vixHigh - vixLow || 1) * (vixBottom - vixTop);
      const line = (values, y) => values.map((value, i) => x(i).toFixed(2) + ',' + y(value).toFixed(2)).join(' ');
      const latest = points[points.length - 1];
      const tooltipId = 'market-ytd-tooltip';
      marketRoot.innerHTML = '<div class="market-ytd-head"><strong>SPY <em class="' + (latest.spy_ytd_percent >= 0 ? 'up' : 'down') + '">$' + num(latest.spy) + ' · ' + signed(latest.spy_ytd_percent, 1, '%') + '</em></strong>' +
        '<strong>VIX <em>' + num(latest.vix) + '</em></strong></div>' +
        '<div class="market-ytd-wrap"><svg class="market-ytd-chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" tabindex="0" aria-describedby="' + tooltipId + '" aria-label="SPY year-to-date return and VIX level through ' + esc(market.as_of) + '. Hover or use arrow keys for daily values.">' +
        '<line class="market-chart-grid" x1="' + x0 + '" x2="' + x1 + '" y1="' + spyY(0).toFixed(2) + '" y2="' + spyY(0).toFixed(2) + '"></line>' +
        '<line class="market-chart-grid" x1="' + x0 + '" x2="' + x1 + '" y1="' + vixBottom + '" y2="' + vixBottom + '"></line>' +
        '<text class="market-chart-label" x="' + x0 + '" y="20">SPY · YTD %</text><text class="market-chart-label" x="' + x0 + '" y="112">VIX · LEVEL</text>' +
        '<polyline class="market-spy-line" points="' + line(spyValues, spyY) + '"></polyline>' +
        '<polyline class="market-vix-line" points="' + line(vixValues, vixY) + '"></polyline>' +
        '<circle class="market-spy-dot" cx="' + x(points.length - 1).toFixed(2) + '" cy="' + spyY(latest.spy_ytd_percent).toFixed(2) + '" r="3.5"></circle>' +
        '<circle class="market-vix-dot" cx="' + x(points.length - 1).toFixed(2) + '" cy="' + vixY(latest.vix).toFixed(2) + '" r="3.5"></circle>' +
        '<line class="market-hover-line" x1="0" x2="0" y1="' + spyTop + '" y2="' + vixBottom + '" hidden></line>' +
        '<circle class="market-hover-dot market-hover-spy" cx="0" cy="0" r="3.5" hidden></circle><circle class="market-hover-dot market-hover-vix" cx="0" cy="0" r="3.5" hidden></circle>' +
        '<text class="market-chart-axis" x="' + x0 + '" y="204">' + esc(points[0].date) + '</text><text class="market-chart-axis market-chart-axis-end" x="' + x1 + '" y="204">' + esc(latest.date) + '</text></svg>' +
        '<div class="market-ytd-tooltip" id="' + tooltipId + '" role="status" aria-live="polite" hidden></div></div>' +
        '<div class="market-leadership">' +
        rankGroup('Sectors', splitRanks(rankVwap(vwap, ['XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY'])), 'vwap', 'vwap') +
        rankGroup('Crypto', splitRanks(rankCrypto(crypto)), 'crypto', 'crypto') +
        rankGroup('Countries', splitRanks(rankVwap(vwap, (vwap.groups && vwap.groups.countries) || [])), 'vwap', 'vwap') + '</div>' +
        '<p class="market-source">As of ' + esc(market.as_of) + ' close · SPY/VIX + 50D relative momentum</p>';

      const svg = $('.market-ytd-chart', marketRoot), tooltip = $('.market-ytd-tooltip', marketRoot);
      const hoverLine = $('.market-hover-line', svg), spyDot = $('.market-hover-spy', svg), vixDot = $('.market-hover-vix', svg);
      let activeIndex = points.length - 1;
      const hide = () => {
        tooltip.hidden = true;
        [hoverLine, spyDot, vixDot].forEach(node => node.setAttribute('hidden', ''));
      };
      const show = index => {
        activeIndex = Math.max(0, Math.min(points.length - 1, index));
        const point = points[activeIndex], hoverX = x(activeIndex);
        tooltip.innerHTML = '<b>' + esc(prettyDate(point.date)) + '</b><span>SPY <em>$' + num(point.spy) + ' · ' + signed(point.spy_ytd_percent, 1, '%') + '</em></span><span>VIX <em>' + num(point.vix) + '</em></span>';
        hoverLine.setAttribute('x1', hoverX.toFixed(2)); hoverLine.setAttribute('x2', hoverX.toFixed(2));
        spyDot.setAttribute('cx', hoverX.toFixed(2)); spyDot.setAttribute('cy', spyY(point.spy_ytd_percent).toFixed(2));
        vixDot.setAttribute('cx', hoverX.toFixed(2)); vixDot.setAttribute('cy', vixY(point.vix).toFixed(2));
        [hoverLine, spyDot, vixDot].forEach(node => node.removeAttribute('hidden'));
        tooltip.hidden = false;
        const svgRect = svg.getBoundingClientRect(), wrapRect = svg.parentElement.getBoundingClientRect();
        const pointLeft = svgRect.left - wrapRect.left + hoverX / W * svgRect.width;
        tooltip.style.left = Math.min(Math.max(6, pointLeft + 8), svg.parentElement.clientWidth - tooltip.offsetWidth - 6) + 'px';
        tooltip.style.top = '34px';
      };
      const pointerIndex = event => {
        const rect = svg.getBoundingClientRect();
        return Math.round((((event.clientX - rect.left) / rect.width * W) - x0) / (x1 - x0) * (points.length - 1));
      };
      svg.addEventListener('pointermove', event => show(pointerIndex(event)));
      svg.addEventListener('pointerdown', event => show(pointerIndex(event)));
      svg.addEventListener('pointerleave', () => { if (document.activeElement !== svg) hide(); });
      svg.addEventListener('focus', () => show(activeIndex));
      svg.addEventListener('keydown', event => {
        let next = null;
        if (event.key === 'ArrowLeft') next = activeIndex - 1;
        if (event.key === 'ArrowRight') next = activeIndex + 1;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = points.length - 1;
        if (next == null) return;
        event.preventDefault(); show(next);
      });
      svg.addEventListener('blur', hide);
    }).catch(() => {
      marketRoot.innerHTML = '<p class="market-loading">Market charts are temporarily unavailable.</p>';
    });
  }

  /* ── risk page: subjective post-close journal ────────────────────── */
  const riskRoot = $('#risk-live');
  if (riskRoot) {
    const bullets = rows => '<ul>' + (rows || []).map(row => '<li>' + esc(row) + '</li>').join('') + '</ul>';
    riskJournalData.then(data => {
      const entries = data && Array.isArray(data.entries) ? data.entries : [];
      if (!entries.length) {
        riskRoot.innerHTML = '<p class="footnote">The risk journal is unavailable.</p>';
        return;
      }
      riskRoot.innerHTML = entries.map((entry, index) => {
        const stanceClass = entry.stance.toLowerCase().replace(/[^a-z]+/g, '-');
        return '<article class="card risk-journal-entry' + (index === 0 ? ' is-latest' : '') + '">' +
          '<header class="risk-journal-head"><div><time datetime="' + esc(entry.date) + '">' + esc(entry.date) + '</time>' +
          '<span class="risk-journal-author">By ' + esc(entry.author || data.author || 'GPT-5.6') + '</span>' +
          '<span class="risk-journal-stamp risk-journal-' + esc(stanceClass) + '">' + esc(entry.stance) + '</span>' +
          (entry.lean ? '<span class="risk-journal-lean">' + esc(entry.lean) + '</span>' : '') + '</div>' +
          '<strong>' + esc(entry.risk_appetite) + '/10 <small>risk appetite</small></strong></header>' +
          '<div class="risk-journal-body"><h2>' + esc(entry.headline) + '</h2>' +
          '<div class="risk-journal-prose">' + (entry.journal || []).map(row => '<p>' + esc(row) + '</p>').join('') + '</div>' +
          '<div class="risk-journal-columns"><section><h3>What supports risk</h3>' + bullets(entry.what_supports_risk) + '</section>' +
          '<section><h3>What holds it back</h3>' + bullets(entry.what_holds_it_back) + '</section>' +
          '<section><h3>What changes my mind</h3>' + bullets(entry.what_changes_my_mind) + '</section></div>' +
          '<p class="risk-journal-source">' + esc(entry.source_note) + '</p></div></article>';
      }).join('');
    });
  }

  /* ── performance page: keep the headline current from the live feed ─ */
  const perfStamp = $('#perf-live');
  if (perfStamp) {
    fetch('/trading/results-ytd.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).then(d => {
      if (!d || !d.points || !d.points.length) return;
      const last = d.points[d.points.length - 1];
      perfStamp.innerHTML = 'Live feed: <b class="' + (last.ytd_percent >= 0 ? 'up' : 'down') + '">' +
        signed(last.ytd_percent, 2, '%') + '</b> YTD as of ' + esc(last.date) +
        ' · ' + d.points.length + ' daily snapshots';
    }).catch(() => {});
  }
})();
