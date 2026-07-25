/* Trading desk prototype runtime: live risk/performance data + sparkline hover.
   Fetches the SAME JSONs the live /trading/ page uses, so these surfaces
   cannot go stale the way an embedded snapshot does. */
(() => {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v, dp = 2) => Number(v).toFixed(dp);
  const signed = (v, dp = 2, suf = '') => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(dp) + suf;

  const riskData = fetch('/trading/risk-ytd.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);

  /* ── status chip: always show the live score ─────────────────────── */
  riskData.then(d => {
    const chip = $('.chip');
    if (!d || !chip) return;
    chip.innerHTML = '<span class="dot"></span>Risk: ' + esc(d.score.label) + ' ' + Math.round(d.score.total);
  });

  /* ── desk sparklines: month ticks are server-drawn; hover here ───── */
  document.querySelectorAll('.spark-wrap[data-dates]').forEach(wrap => {
    const dates = wrap.dataset.dates.split(',');
    const closes = wrap.dataset.closes.split(',').map(Number);
    const entry = Number(wrap.dataset.entry);
    const svg = wrap.querySelector('svg');
    const tip = wrap.querySelector('.spark-tip');
    if (!svg || !tip || !dates.length) return;
    const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const show = i => {
      i = Math.max(0, Math.min(dates.length - 1, i));
      const d = dates[i];
      const pct = entry ? (closes[i] / entry - 1) * 100 : null;
      tip.innerHTML = '<b>' + MONTHS[+d.slice(5, 7) - 1] + ' ' + (+d.slice(8, 10)) + '</b> · ' + num(closes[i]) +
        (pct == null ? '' : ' · <span class="' + (pct >= 0 ? 'up' : 'down') + '">' + signed(pct, 1, '%') + ' vs cost</span>');
      tip.hidden = false;
    };
    svg.addEventListener('pointermove', e => {
      const r = svg.getBoundingClientRect();
      show(Math.round((e.clientX - r.left) / r.width * (dates.length - 1)));
    });
    svg.addEventListener('pointerleave', () => { tip.hidden = true; });
  });

  /* ── risk page: render live risk-ytd + the gauntlet verdict ──────── */
  const riskRoot = $('#risk-live');
  if (riskRoot) {
    const evalData = fetch('/trading/risk-evaluation.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null);
    Promise.all([riskData, evalData]).then(([d, ev]) => {
      if (!d) { riskRoot.innerHTML = '<p class="footnote">Could not load /trading/risk-ytd.json — the live feed this page mirrors.</p>'; return; }
      const rc = d.current, rs = d.score;
      const ORDER = [['VVIX', 'vvix'], ['Curve M2−M1', 'curve'], ['MOVE', 'move'], ['SKEW', 'skew']];
      const bars = ORDER.map(([label, key]) => {
        const c = rs.components[key] || { points: 0, maximum: 0 };
        const pct = c.maximum ? c.points / c.maximum * 100 : 0;
        return '<div class="risk-bar"><span>' + label + '</span><span class="t"><span class="f" style="width:' + pct.toFixed(0) +
          '%"></span></span><span class="n">' + num(c.points, 1).replace(/\.0$/, '') + '/' + c.maximum + '</span></div>';
      }).join('');
      const gauges = [
        ['VIX', num(rc.vix), rc.bands.vix], ['VVIX', num(rc.vvix), rc.bands.vvix],
        ['MOVE', num(rc.move), rc.bands.move], ['SKEW', num(rc.skew), rc.bands.skew],
        ['HY OAS', num(rc.hy_oas) + '%', 'Credit'], ['VIX curve M2−M1', signed(rc.curve_spread), rc.curve_band]
      ].map(g => '<tr><td class="sym">' + g[0] + '</td><td class="num">' + g[1] + '</td><td>' + esc(g[2]) + '</td></tr>').join('');
      const curve = (d.curve || []).map(x =>
        '<tr><td class="sym">' + esc(x.label) + '</td><td class="num">' + num(x.value) + '</td><td>' + esc(x.expiration || 'spot') + '</td></tr>').join('');
      const commentary = (d.commentary || []).map(c => '<div class="mkt"><span class="lbl">' + esc(c) + '</span></div>').join('');
      const rules = ((rs.rules) || []).map(r => '<div class="mkt"><span class="lbl">' + esc(r) + '</span></div>').join('');

      let gauntlet = '';
      if (ev && ev.model_status) {
        const ms = ev.model_status;
        const reasons = (ms.reasons || []).map(r => '<div class="mkt"><span class="lbl">' + esc(r) + '</span></div>').join('');
        gauntlet =
          '<div class="card"><h2>Forecast model — persistence gauntlet<span class="card-r">' + esc(ms.status) + '</span></h2>' +
          '<div style="padding:14px 16px;font-size:13px;line-height:1.55">' + esc(ms.message) + '</div>' + reasons +
          '<div class="mkt"><span class="lbl">Walk-forward folds: ' + (ev.folds ? ev.folds.length : 0) +
          ' · feature rows: ' + (ev.feature_rows || '—') + ' · out-of-sample predictions: ' +
          (ev.oos_predictions ? ev.oos_predictions.length : 0) + '</span></div></div>';
      }

      riskRoot.innerHTML =
        '<div class="card"><h2>Regime score<span class="card-r">as of ' + esc(d.as_of) + ' · live feed</span></h2>' +
        '<div style="padding:18px"><div class="risk-score"><div><div class="risk-dial">' + Math.round(rs.total) +
        '</div><div style="font-size:12px;color:var(--bl-muted)">of 100 · ' + esc(rs.label) + '</div></div>' +
        '<div class="risk-bars">' + bars + '</div></div></div></div>' +
        '<div class="card"><h2>Current readings<span class="card-r">6 gauges</span></h2><div class="tw"><table style="min-width:420px">' +
        '<thead><tr><th>Gauge</th><th class="num">Level</th><th>Band</th></tr></thead><tbody>' + gauges + '</tbody></table></div></div>' +
        '<div class="card"><h2>VIX futures curve<span class="card-r">spot → M6</span></h2><div class="tw"><table style="min-width:380px">' +
        '<thead><tr><th>Contract</th><th class="num">Level</th><th>Expiry</th></tr></thead><tbody>' + curve + '</tbody></table></div></div>' +
        gauntlet +
        '<div class="card"><h2>Read</h2>' + commentary + '</div>' +
        '<div class="card"><h2>Scoring rules<span class="card-r">transparent heuristic</span></h2>' + rules + '</div>';
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
