/* Trading desk prototype runtime: live risk/performance data + sparkline hover.
   Fetches the SAME JSONs the live /trading/ page uses, so these surfaces
   cannot go stale the way an embedded snapshot does. */
(() => {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v, dp = 2) => Number(v).toFixed(dp);
  const signed = (v, dp = 2, suf = '') => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(dp) + suf;

  const riskJournalData = fetch('/trading/risk-journal.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);

  /* ── status chip: always show the latest subjective stance ───────── */
  riskJournalData.then(d => {
    const chip = $('.chip');
    const latest = d && d.entries && d.entries[0];
    if (!latest || !chip) return;
    chip.innerHTML = '<span class="dot"></span>Risk: ' + esc(latest.stance) + ' ' + esc(latest.risk_appetite) + '/10';
    chip.href = '/trading/risk/';
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
    let entryIndex = closes.findIndex((value, i) => i > 0 && (closes[i - 1] - entry) * (value - entry) <= 0);
    if (entryIndex < 0) entryIndex = closes.reduce((best, value, i) => Math.abs(value - entry) < Math.abs(closes[best] - entry) ? i : best, 0);
    const last = closes[closes.length - 1];
    const symbol = $('.pos-sym', chart.closest('.pos'))?.textContent.trim() || 'Position';
    const tooltipId = 'prc-tooltip-' + symbol.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    chart.insertAdjacentHTML('beforeend',
      '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" tabindex="0" aria-describedby="' + tooltipId + '" aria-label="' +
      esc(symbol + ' 60-session price history. Horizontal invalidation at $' + num(kill) + ', horizontal entry price at $' + num(entry) + ', vertical entry reference, latest $' + num(last) + '. Hover or use arrow keys for daily metrics.') + '">' +
      '<line class="prc-grid" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(hi).toFixed(2) + '" y2="' + y(hi).toFixed(2) + '"></line>' +
      '<line class="prc-grid" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(lo).toFixed(2) + '" y2="' + y(lo).toFixed(2) + '"></line>' +
      '<line class="prc-invalidation" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(kill).toFixed(2) + '" y2="' + y(kill).toFixed(2) + '"></line>' +
      '<text class="prc-label prc-label-kill" x="' + (left + 5) + '" y="' + (y(kill) - 6).toFixed(2) + '">Invalidation $' + num(kill) + '</text>' +
      '<line class="prc-entry-level" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(entry).toFixed(2) + '" y2="' + y(entry).toFixed(2) + '"></line>' +
      '<text class="prc-label prc-label-entry-level" x="' + (left + 5) + '" y="' + (y(entry) - 6).toFixed(2) + '">Entry $' + num(entry) + '</text>' +
      '<line class="prc-entry" x1="' + x(entryIndex).toFixed(2) + '" x2="' + x(entryIndex).toFixed(2) + '" y1="' + top + '" y2="' + (H - bottom) + '"></line>' +
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
    const prettyDate = iso => new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
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
