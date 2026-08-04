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

  const subnav = $('.subnav .wrap');
  const activeNav = subnav && $('a[aria-current="page"]', subnav);
  if (activeNav && subnav.scrollWidth > subnav.clientWidth) {
    subnav.scrollLeft = Math.max(0, activeNav.offsetLeft - (subnav.clientWidth - activeNav.offsetWidth) / 2);
  }

  const riskJournalData = fetch('/trading/risk-journal.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);

  /* ── status chips: three independent risk-appetite reads, all 0–10.
     Each updates on its own; a failed fetch leaves that chip's static
     fallback text in place. Scores above 5 are green, below 5 are red,
     and exactly 5 keeps the neutral treatment. ── */
  const setChip = (key, name, value, stanceText) => {
    const chip = $('.chip-' + key);
    if (!chip || !Number.isFinite(value)) return;
    chip.classList.remove('chip-on', 'chip-off', 'chip-neutral');
    chip.classList.add(value > 5 ? 'chip-on' : value < 5 ? 'chip-off' : 'chip-neutral');
    chip.textContent = name + ' ' + Math.round(value * 10) / 10;
    if (stanceText) chip.title = name + ' risk appetite — ' + stanceText + ' · ' + Math.round(value * 10) / 10 + '/10';
  };
  riskJournalData.then(d => {
    const latest = d && d.entries && d.entries[0];
    if (latest) setChip('gpt', 'GPT', Number(latest.risk_appetite), latest.stance);
  });
  fetch('/trading/fable-risk.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null).then(d => {
    const sessionRank = { 'pre-market': 0, intraday: 1, 'post-close': 2 };
    const rows = d ? [...(d.entries || []), ...(d.model_entries || [])] : [];
    const latest = rows.sort((a, b) => {
      const dateOrder = String(b.date || b.as_of_date).localeCompare(String(a.date || a.as_of_date));
      return dateOrder || (sessionRank[b.session] ?? 1) - (sessionRank[a.session] ?? 1);
    })[0];
    if (latest) setChip('fable', 'Fable', Number(latest.risk_appetite ?? latest.rating), latest.stance || latest.verdict);
  });

  fetch('/trading/grok-risk.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null).then(d => {
    const latest = d && d.entries && d.entries[0];
    if (latest) setChip('grok', 'Grok', Number(latest.risk_appetite), latest.stance);
  });

  /* ── position risk charts: levels + interactive metrics ─────────── */
  document.querySelectorAll('.position-risk-chart').forEach(chart => {
    const source = $('.spark-data[data-dates]', chart.closest('.pos'));
    if (!source) return;
    const dates = source.dataset.dates.split(',');
    const closes = source.dataset.closes.split(',').map(Number);
    const entry = Number(source.dataset.entry);
    const kill = chart.dataset.kill === undefined ? null : Number(chart.dataset.kill);
    const hasKill = Number.isFinite(kill);
    source.remove();
    if (dates.length < 2 || dates.length !== closes.length || !closes.every(Number.isFinite) || !Number.isFinite(entry)) return;

    const W = 760, H = 190, left = 46, right = 22, top = 18, bottom = 30;
    const levels = hasKill ? [entry, kill] : [entry];
    const rawLow = Math.min(...closes, ...levels), rawHigh = Math.max(...closes, ...levels);
    const padding = Math.max((rawHigh - rawLow) * .08, rawHigh * .01);
    const lo = rawLow - padding, hi = rawHigh + padding;
    const x = i => left + i / (closes.length - 1) * (W - left - right);
    const y = value => top + (hi - value) / (hi - lo || 1) * (H - top - bottom);
    const points = closes.map((value, i) => x(i).toFixed(2) + ',' + y(value).toFixed(2)).join(' ');
    const last = closes[closes.length - 1];
    const symbol = $('.pos-sym', chart.closest('.pos'))?.textContent.trim() || 'Position';
    const tooltipId = 'prc-tooltip-' + symbol.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const invalidationAria = hasKill ? ', horizontal invalidation at $' + num(kill) : '';
    const entryLabelY = y(entry) - 8;
    const killLabelY = hasKill ? Math.min(H - bottom - 4, y(kill) + 13) : null;
    const invalidationLines = hasKill ?
      '<line class="prc-invalidation" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(kill).toFixed(2) + '" y2="' + y(kill).toFixed(2) + '"></line>' +
      '<text class="prc-label prc-label-kill" x="' + (left + 5) + '" y="' + killLabelY.toFixed(2) + '">Invalidation $' + num(kill) + '</text>' : '';
    chart.insertAdjacentHTML('beforeend',
      '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" tabindex="0" aria-describedby="' + tooltipId + '" aria-label="' +
      esc(symbol + ' 60-session price history' + invalidationAria + ', horizontal entry price at $' + num(entry) + ', latest $' + num(last) + '. Hover or use arrow keys for daily metrics.') + '">' +
      '<line class="prc-grid" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(hi).toFixed(2) + '" y2="' + y(hi).toFixed(2) + '"></line>' +
      '<line class="prc-grid" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(lo).toFixed(2) + '" y2="' + y(lo).toFixed(2) + '"></line>' +
      invalidationLines +
      '<line class="prc-entry-level" x1="' + left + '" x2="' + (W - right) + '" y1="' + y(entry).toFixed(2) + '" y2="' + y(entry).toFixed(2) + '"></line>' +
      '<text class="prc-label prc-label-entry-level" x="' + (left + 5) + '" y="' + entryLabelY.toFixed(2) + '">Entry $' + num(entry) + '</text>' +
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
      const metric = (value, suffix = '') => '<em class="' + (value >= 0 ? 'up' : 'down') + '">' + signed(value, 1, suffix) + '</em>';
      const money = value => '<em class="' + (value >= 0 ? 'up' : 'down') + '">' + (value >= 0 ? '+' : '−') + '$' + Math.abs(value).toFixed(2) + '</em>';
      const invalidationMetric = hasKill ? (() => {
        const room = close - kill, roomPct = room / kill * 100;
        return '<span>room to invalidation ' + money(room) + ' · ' + metric(roomPct, '%') + '</span>';
      })() : '<span>invalidation <em>not recorded</em></span>';
      tooltip.innerHTML = '<b><span>' + esc(prettyDate(dates[activeIndex])) + '</span><strong>$' + num(close) + '</strong></b>' +
        '<span>Day ' + (dayPct == null ? '<em>—</em>' : metric(dayPct, '%')) + '</span>' +
        '<span>vs entry ' + money(vsEntry) + ' · ' + metric(vsEntryPct, '%') + '</span>' +
        invalidationMetric;
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

/* Trading desk v3 blotter interactions. Generated rows remain useful without JS. */
(function () {
  'use strict';
  let thesisDocument = null;
  let thesisOpener = null;

  function toggleDeskRow(button, force) {
    var id = button.getAttribute('aria-controls');
    var detail = id ? document.getElementById(id) : null;
    if (!detail) return;
    var open = typeof force === 'boolean' ? force : button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(open));
    detail.hidden = !open;
    button.closest('tr').classList.toggle('is-open', open);
  }

  function initDeskBlotter() {
    var toggles = Array.prototype.slice.call(document.querySelectorAll('.desk-row-toggle'));
    toggles.forEach(function (button, index) {
      button.addEventListener('click', function () { toggleDeskRow(button); });
      button.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault();
          var direction = event.key === 'ArrowDown' ? 1 : -1;
          var next = toggles[(index + direction + toggles.length) % toggles.length];
          next.focus();
        }
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          toggleDeskRow(button);
        }
      });
    });
  }

  function initDeskYtdCharts() {
    var activeHide = null;
    document.querySelectorAll('[data-desk-ytd-chart]').forEach(function (figure) {
      var symbol = figure.getAttribute('data-desk-ytd-chart');
      var history = document.querySelector('[data-desk-one-year-chart="' + symbol + '"]');
      var svg = figure.querySelector('svg');
      var tooltip = figure.querySelector('[data-desk-ytd-tooltip]');
      var hoverLine = figure.querySelector('.desk-ytd-hover-line');
      var hoverDot = figure.querySelector('.desk-ytd-hover-dot');
      if (!history || !svg || !tooltip || !hoverLine || !hoverDot) return;
      var allDates = (history.getAttribute('data-desk-chart-dates') || '').split(',').filter(Boolean);
      var allCloses = (history.getAttribute('data-desk-chart-closes') || '').split(',').map(Number);
      if (allDates.length < 2 || allDates.length !== allCloses.length || !allCloses.every(Number.isFinite)) return;
      var dates = allDates, closes = allCloses;
      var base = closes[0];
      var entry = Number(figure.getAttribute('data-desk-ytd-entry'));
      var kill = Number(figure.getAttribute('data-desk-ytd-kill'));
      var hasEntry = Number.isFinite(entry) && entry > 0;
      var hasKill = Number.isFinite(kill) && kill > 0;
      var domain = closes.slice();
      if (hasEntry) domain.push(entry);
      if (hasKill) domain.push(kill);
      var rawLow = Math.min.apply(null, domain), rawHigh = Math.max.apply(null, domain);
      var margin = Math.max((rawHigh - rawLow) * .06, .5);
      var low = Math.max(0, rawLow - margin), high = rawHigh + margin;
      var width = 236, height = 88, leftBound = 36, rightBound = 232, topBound = 6, bottomBound = 68;
      var x = function (index) { return leftBound + index * (rightBound - leftBound) / Math.max(closes.length - 1, 1); };
      var y = function (value) { return topBound + (high - value) * (bottomBound - topBound) / (high - low || 1); };
      var activeIndex = closes.length - 1;
      var signed = function (value) { return (value >= 0 ? '+' : '−') + Math.abs(value).toFixed(1) + '%'; };
      function hideMetrics() {
        tooltip.hidden = true;
        hoverLine.setAttribute('hidden', '');
        hoverDot.setAttribute('hidden', '');
        if (activeHide === hideMetrics) activeHide = null;
      }
      function showMetrics(index) {
        if (activeHide && activeHide !== hideMetrics) activeHide();
        activeHide = hideMetrics;
        activeIndex = Math.max(0, Math.min(closes.length - 1, index));
        var close = closes[activeIndex];
        var day = activeIndex ? (close / closes[activeIndex - 1] - 1) * 100 : null;
        var extras = '';
        if (hasEntry) extras += '<span>vs entry <b>' + signed((close / entry - 1) * 100) + '</b></span>';
        if (hasKill) extras += '<span>room to kill <b>' + signed((close / kill - 1) * 100) + '</b></span>';
        tooltip.innerHTML = '<strong>' + dates[activeIndex] + ' · $' + close.toFixed(2) + '</strong>' +
          '<span>Day <b>' + (day === null ? '—' : signed(day)) + '</b></span>' +
          '<span>Trailing 1Y <b>' + signed((close / base - 1) * 100) + '</b></span>' + extras;
        var hoverX = x(activeIndex), hoverY = y(close);
        hoverLine.setAttribute('x1', hoverX.toFixed(1));
        hoverLine.setAttribute('x2', hoverX.toFixed(1));
        hoverDot.setAttribute('cx', hoverX.toFixed(1));
        hoverDot.setAttribute('cy', hoverY.toFixed(1));
        hoverLine.removeAttribute('hidden');
        hoverDot.removeAttribute('hidden');
        tooltip.hidden = false;
        var rect = svg.getBoundingClientRect();
        var pointLeft = rect.left + hoverX / width * rect.width;
        var left = Math.min(Math.max(8, pointLeft - tooltip.offsetWidth / 2), window.innerWidth - tooltip.offsetWidth - 8);
        var above = rect.top - tooltip.offsetHeight - 8;
        tooltip.style.left = left + 'px';
        tooltip.style.top = (above >= 8 ? above : rect.bottom + 8) + 'px';
      }
      function pointerIndex(event) {
        var rect = svg.getBoundingClientRect();
        var viewX = (event.clientX - rect.left) / rect.width * width;
        return Math.round((viewX - leftBound) / (rightBound - leftBound) * (closes.length - 1));
      }
      svg.addEventListener('pointermove', function (event) { showMetrics(pointerIndex(event)); });
      svg.addEventListener('pointerdown', function (event) { showMetrics(pointerIndex(event)); });
      svg.addEventListener('pointerleave', function () { if (document.activeElement !== svg) hideMetrics(); });
      svg.addEventListener('focus', function () { showMetrics(activeIndex); });
      svg.addEventListener('blur', hideMetrics);
      svg.addEventListener('keydown', function (event) {
        var next = null;
        if (event.key === 'ArrowLeft') next = activeIndex - 1;
        if (event.key === 'ArrowRight') next = activeIndex + 1;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = closes.length - 1;
        if (next === null) return;
        event.preventDefault();
        showMetrics(next);
      });
    });
    window.addEventListener('scroll', function () { if (activeHide) activeHide(); }, {passive: true});
  }

  function initDeskHistoryCharts() {
    document.querySelectorAll('[data-desk-one-year-chart]').forEach(function (figure) {
      var svg = figure.querySelector('svg');
      var tooltip = figure.querySelector('[data-desk-chart-tooltip]');
      var hoverLine = figure.querySelector('.desk-chart-hover-line');
      var hoverDot = figure.querySelector('.desk-chart-hover-dot');
      if (!svg || !tooltip || !hoverLine || !hoverDot) return;
      var dates = (figure.getAttribute('data-desk-chart-dates') || '').split(',').filter(Boolean);
      var closes = (figure.getAttribute('data-desk-chart-closes') || '').split(',').map(Number);
      if (dates.length < 2 || dates.length !== closes.length || !closes.every(Number.isFinite)) return;
      var entry = Number(figure.getAttribute('data-desk-chart-entry'));
      var kill = Number(figure.getAttribute('data-desk-chart-kill'));
      var hasEntry = Number.isFinite(entry) && entry > 0;
      var hasKill = Number.isFinite(kill) && kill > 0;
      var width = 520, height = 210, left = 44, right = 510, top = 10, bottom = 182;
      var rawLow = Math.min.apply(null, closes);
      var rawHigh = Math.max.apply(null, closes);
      var scenarioPrices = Array.prototype.map.call(figure.querySelectorAll('.desk-detail-rule title'), function (title) {
        var match = title.textContent.match(/\$([\d,.]+)/);
        return match ? Number(match[1].replace(/,/g, '')) : NaN;
      }).filter(Number.isFinite);
      if (scenarioPrices.length) {
        rawLow = Math.min.apply(null, [rawLow].concat(scenarioPrices));
        rawHigh = Math.max.apply(null, [rawHigh].concat(scenarioPrices));
      }
      var margin = Math.max((rawHigh - rawLow) * .04, 1);
      var low = Math.max(0, rawLow - margin), high = rawHigh + margin;
      var x = function (index) { return left + index * (right - left) / Math.max(closes.length - 1, 1); };
      var y = function (value) { return top + (high - value) * (bottom - top) / (high - low || 1); };
      var activeIndex = closes.length - 1;
      var signed = function (value) { return (value >= 0 ? '+' : '−') + Math.abs(value).toFixed(1) + '%'; };
      function hideMetrics() {
        tooltip.hidden = true;
        hoverLine.setAttribute('hidden', '');
        hoverDot.setAttribute('hidden', '');
      }
      function showMetrics(index) {
        activeIndex = Math.max(0, Math.min(closes.length - 1, index));
        var close = closes[activeIndex];
        var day = activeIndex ? (close / closes[activeIndex - 1] - 1) * 100 : null;
        var year = (close / closes[0] - 1) * 100;
        var extras = '';
        if (hasEntry) extras += '<span>vs entry <b>' + signed((close / entry - 1) * 100) + '</b></span>';
        if (hasKill) extras += '<span>room to kill <b>' + signed((close / kill - 1) * 100) + '</b></span>';
        tooltip.innerHTML = '<strong>' + dates[activeIndex] + ' · $' + close.toFixed(2) + '</strong>' +
          '<span>Day <b>' + (day === null ? '—' : signed(day)) + '</b></span>' +
          '<span>1Y path <b>' + signed(year) + '</b></span>' + extras;
        var hoverX = x(activeIndex), hoverY = y(close);
        hoverLine.setAttribute('x1', hoverX.toFixed(1));
        hoverLine.setAttribute('x2', hoverX.toFixed(1));
        hoverDot.setAttribute('cx', hoverX.toFixed(1));
        hoverDot.setAttribute('cy', hoverY.toFixed(1));
        hoverLine.removeAttribute('hidden');
        hoverDot.removeAttribute('hidden');
        tooltip.hidden = false;
        var svgRect = svg.getBoundingClientRect(), figureRect = figure.getBoundingClientRect();
        var pointLeft = svgRect.left - figureRect.left + hoverX / width * svgRect.width;
        var pointTop = svgRect.top - figureRect.top + hoverY / height * svgRect.height;
        tooltip.style.left = Math.min(Math.max(8, pointLeft + 12), figure.clientWidth - tooltip.offsetWidth - 8) + 'px';
        tooltip.style.top = Math.max(8, pointTop - tooltip.offsetHeight - 10) + 'px';
      }
      function pointerIndex(event) {
        var rect = svg.getBoundingClientRect();
        var viewX = (event.clientX - rect.left) / rect.width * width;
        return Math.round((viewX - left) / (right - left) * (closes.length - 1));
      }
      svg.addEventListener('pointermove', function (event) { showMetrics(pointerIndex(event)); });
      svg.addEventListener('pointerdown', function (event) { showMetrics(pointerIndex(event)); });
      svg.addEventListener('pointerleave', function () { if (document.activeElement !== svg) hideMetrics(); });
      svg.addEventListener('focus', function () { showMetrics(activeIndex); });
      svg.addEventListener('blur', hideMetrics);
      svg.addEventListener('keydown', function (event) {
        var next = null;
        if (event.key === 'ArrowLeft') next = activeIndex - 1;
        if (event.key === 'ArrowRight') next = activeIndex + 1;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = closes.length - 1;
        if (next === null) return;
        event.preventDefault();
        showMetrics(next);
      });
    });
  }

  function closeThesisDialog(dialog) {
    dialog.close();
    if (thesisOpener) thesisOpener.focus();
  }

  async function openThesis(button) {
    var dialog = document.getElementById('desk-thesis-dialog');
    if (!dialog) return;
    thesisOpener = button;
    var symbol = button.getAttribute('data-thesis-open');
    var thesisSource = dialog.getAttribute('data-thesis-source');
    var body = dialog.querySelector('[data-thesis-body]');
    var summary = dialog.querySelector('[data-thesis-summary]');
    dialog.querySelector('#desk-thesis-title').textContent = symbol + ' full thesis';
    body.innerHTML = '<p>Loading thesis…</p>';
    dialog.showModal();
    try {
      if (!thesisDocument) {
        var response = await fetch(thesisSource, {credentials: 'same-origin'});
        if (!response.ok) throw new Error('Thesis source returned ' + response.status);
        thesisDocument = new DOMParser().parseFromString(await response.text(), 'text/html');
      }
      var article = thesisDocument.querySelector('article.hypothesis-detail#hypothesis-' + symbol.toLowerCase() + '-setup');
      if (!article) throw new Error('No canonical thesis found for ' + symbol);
      var clone = article.cloneNode(true);
      clone.querySelectorAll('details').forEach(function (details) { details.removeAttribute('open'); });
      body.replaceChildren(clone);
      var row = button.closest('.desk-main-row');
      if (!row) {
        var detailRow = button.closest('.desk-detail-row');
        row = detailRow ? detailRow.previousElementSibling : null;
      }
      var catalyst = row ? row.querySelector('.desk-catalyst') : null;
      summary.innerHTML = '<div class="desk-thesis-summary"><b>' + symbol + '</b><span>Next catalyst ' + (catalyst ? catalyst.textContent : '—') + '</span></div>';
    } catch (error) {
      body.innerHTML = '<p class="bl-empty">Could not load the full thesis. Reload the Trading Desk and try again.</p>';
      console.error(error);
    }
  }

  function initThesisDialog() {
    var dialog = document.getElementById('desk-thesis-dialog');
    if (!dialog) return;
    document.addEventListener('click', function (event) {
      var opener = event.target.closest('[data-thesis-open]');
      if (opener) openThesis(opener);
      if (event.target.closest('[data-thesis-close]')) closeThesisDialog(dialog);
    });
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) closeThesisDialog(dialog);
    });
    dialog.addEventListener('cancel', function (event) {
      event.preventDefault();
      closeThesisDialog(dialog);
    });
  }

  function initDeskV3() {
    initDeskBlotter();
    initDeskYtdCharts();
    initDeskHistoryCharts();
    initThesisDialog();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDeskV3);
  else initDeskV3();
})();
