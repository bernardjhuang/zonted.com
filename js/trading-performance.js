(() => {
  'use strict';

  // Progressive enhancement over the cron-owned RESULTS panel. Everything here
  // reads the markup the generator already emits (data-performance-* on each
  // action) plus results-ytd.json, so a cron refresh cannot desync it.
  const panel = document.querySelector('#results-panel');
  if (!panel) return;
  const list = panel.querySelector('.performance-action-list');
  if (!list) return;

  const esc = value => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const SESSIONS = 10;
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const DOW = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  // Dates are plain YYYY-MM-DD; parse as local parts so the label never shifts a day.
  const parts = iso => iso.split('-').map(Number);
  const short = iso => { const [, m, d] = parts(iso); return `${MONTHS[m - 1]} ${d}`; };
  const long = iso => {
    const [y, m, d] = parts(iso);
    return `${DOW[new Date(y, m - 1, d).getDay()]} ${MONTHS[m - 1]} ${d}`;
  };
  const pct = value => `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;

  const actions = [...list.querySelectorAll('.performance-action')].map(row => {
    const raw = row.querySelector('strong');
    const text = raw ? raw.textContent.trim() : '';
    const parsed = Number(text.replace('−', '-').replace('%', '').replace('+', ''));
    return {
      date: row.dataset.performanceDate,
      side: row.dataset.performanceSide,
      type: row.dataset.performanceType,
      symbol: row.dataset.performanceSymbol,
      pct: Number.isFinite(parsed) ? parsed : null,
    };
  }).filter(a => a.date && a.symbol);
  if (!actions.length) return;

  const dates = [...new Set(actions.map(a => a.date))].sort();
  const sessionDates = dates.slice(-SESSIONS);
  const inWindow = actions.filter(a => sessionDates.includes(a.date));

  const daily = sessionDates.map(date => {
    const closed = inWindow.filter(a => a.date === date && a.side === 'sell' && a.pct !== null);
    const all = inWindow.filter(a => a.date === date);
    return {
      date,
      n: closed.length,
      avg: closed.length ? closed.reduce((s, a) => s + a.pct, 0) / closed.length : 0,
      actions: all.length,
    };
  });
  const tape = inWindow.filter(a => a.side === 'sell' && a.pct !== null)
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

  const hv = (t, s, v, x, pos) =>
    `data-t="${esc(t)}" data-s="${esc(s)}" data-v="${esc(v)}"${x ? ` data-x="${esc(x)}"` : ''} data-pos="${pos ? 1 : 0}"`;

  // ── trade tape ─────────────────────────────────────────────────────
  const renderTape = () => {
    const W = 1160, H = 150, MID = 75;
    const step = W / tape.length;
    const mx = Math.max(...tape.map(t => Math.abs(t.pct))) || 1;
    const bars = tape.map((t, i) => {
      const h = Math.max(2, Math.abs(t.pct) / mx * 58);
      const y = t.pct > 0 ? MID - h : MID;
      const kind = t.type === 'option' ? 'Option' : 'Stock';
      const tradeLabel = `${t.symbol}. Type: ${kind}. P&L: ${pct(t.pct)}. Closed ${short(t.date)}.`;
      return `<rect class="pf-hv pf-trade" tabindex="0" role="img" aria-label="${esc(tradeLabel)}" data-trade-detail="1"
        x="${(i * step).toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(1, step - 1.6).toFixed(1)}"
        height="${h.toFixed(1)}" rx="1.5" fill="${t.pct > 0 ? '#087a42' : '#c93a4a'}"
        ${hv(t.symbol, kind, pct(t.pct), short(t.date), t.pct > 0)}/>`;
    }).join('');
    const best = tape.reduce((a, b) => (b.pct > a.pct ? b : a));
    const worst = tape.reduce((a, b) => (b.pct < a.pct ? b : a));
    return `<section class="pf-card">
      <h2 class="pf-h">Every decided trade, in order</h2>
      <p class="pf-sub">One bar per closed trade across the last ${daily.length} sessions, height = size of the move. Hover any bar for the ticker and its result. Runs of colour are the point — look for clusters, not individual bars.</p>
      <div class="pf-scroll"><svg viewBox="0 0 ${W} ${H}" class="pf-svg" role="img" aria-label="Closed trades in sequence">
        <line x1="0" y1="${MID}" x2="${W}" y2="${MID}" stroke="var(--bl-border)"/>
        ${bars}
        <text x="4" y="14" font-size="11" fill="#087a42" font-weight="600">WINS</text>
        <text x="4" y="146" font-size="11" fill="#c93a4a" font-weight="600">LOSSES</text>
      </svg></div>
      <p class="pf-note">${tape.length} closed trades · best ${esc(best.symbol)} ${pct(best.pct)} · worst ${esc(worst.symbol)} ${pct(worst.pct)}</p>
    </section>`;
  };

  // ── trade log ──────────────────────────────────────────────────────
  const renderLog = () => {
    const rows = [...daily].reverse().map(d => {
      const sorted = [...inWindow.filter(a => a.date === d.date)]
        .sort((a, b) => (a.side === b.side ? a.symbol.localeCompare(b.symbol) : a.side === 'sell' ? -1 : 1));
      const head = `<tr class="pf-dayrow"><td colspan="4"><b>${short(d.date)}</b>
        <span>${d.actions} actions · ${d.n} closed</span></td>
        <td class="pf-r pf-dayavg ${d.avg >= 0 ? 'up' : 'down'}">${d.n ? `${d.avg >= 0 ? '+' : ''}${d.avg.toFixed(2)}%` : '—'}</td></tr>`;
      return head + sorted.map(a => `<tr>
        <td class="pf-sym">${esc(a.symbol)}</td>
        <td><span class="pf-pill pf-${esc(a.side)}">${a.side === 'sell' ? 'Sell' : 'Buy'}</span></td>
        <td><span class="pf-pill pf-${esc(a.type)}">${a.type === 'option' ? 'Option' : 'Stock'}</span></td>
        <td class="pf-basis">${a.side === 'sell' ? (a.pct === null ? 'pending' : 'realized') : 'marked'}</td>
        <td class="pf-r pf-pnl ${a.side === 'sell' && a.pct !== null ? (a.pct >= 0 ? 'up' : 'down') : ''}">${a.side === 'sell' && a.pct !== null ? pct(a.pct) : '—'}</td></tr>`).join('');
    }).join('');
    return `<section class="pf-card">
      <h2 class="pf-h">Trade log — last ${daily.length} trading sessions</h2>
      <p class="pf-sub">Every action, newest session first. P&amp;L is shown only for sells with a posted or safely reconstructed realized result; pending sells and buys stay listed as unavailable.</p>
      <div class="pf-logwrap"><table class="pf-log">
        <thead><tr><th>Ticker</th><th>Side</th><th>Type</th><th>Basis</th><th class="pf-r">P&amp;L %</th></tr></thead>
        <tbody>${rows}</tbody></table></div>
      <p class="pf-note">${inWindow.length} actions · ${inWindow.filter(a => a.side === 'sell').length} sells ·
        ${inWindow.filter(a => a.side === 'buy').length} buys · ${inWindow.filter(a => a.type === 'option').length} option legs</p>
    </section>`;
  };

  // ── YTD hero ───────────────────────────────────────────────────────
  const renderHero = points => {
    if (!points || points.length < 2) return '';
    const W = 720, H = 210, L = 34, R = 58, T = 22, B = 34;
    const values = points.map(p => p.ytd_percent);
    let lo = Math.min(...values), hi = Math.max(...values);
    const pad = (hi - lo) * 0.22 || 1;
    lo -= pad; hi += pad;
    const x = i => L + i * (W - L - R) / (points.length - 1);
    const y = v => T + (hi - v) / (hi - lo) * (H - T - B);
    const line = points.map((p, i) => `${x(i).toFixed(1)},${y(p.ytd_percent).toFixed(1)}`).join(' ');
    const dots = points.map((p, i) => {
      const prev = i ? points[i - 1].ytd_percent : null;
      const delta = prev === null ? 'first snapshot' : `day change ${(p.ytd_percent - prev >= 0 ? '+' : '')}${(p.ytd_percent - prev).toFixed(1)} pts`;
      return `<circle class="pf-hv" cx="${x(i).toFixed(1)}" cy="${y(p.ytd_percent).toFixed(1)}" r="5" fill="var(--bl-card)" stroke="var(--bl-accent)" stroke-width="2.5"
        ${hv(long(p.date), 'end-of-day portfolio snapshot', `${p.ytd_percent >= 0 ? '+' : ''}${p.ytd_percent.toFixed(2)}% YTD`, delta, prev === null || p.ytd_percent >= prev)}/>
        <text x="${x(i).toFixed(1)}" y="${H - 14}" font-size="10.5" text-anchor="middle" fill="var(--bl-faint)" font-family="var(--bl-mono)">${short(p.date)}</text>`;
    }).join('');
    const cur = values[values.length - 1];
    const chg = cur - values[values.length - 2];
    return `<section class="pf-hero">
      <div class="pf-hero-l">
        <span class="pf-hk">Robinhood · YTD</span>
        <div class="pf-hnum ${cur >= 0 ? 'up' : 'down'}">${cur >= 0 ? '+' : ''}${cur.toFixed(2)}%</div>
        <div class="pf-hchg ${chg >= 0 ? 'up' : 'down'}">${chg >= 0 ? '+' : ''}${chg.toFixed(1)} pts on the day</div>
        <div class="pf-hmeta">
          <div><span>Peak</span><b>${Math.max(...values) >= 0 ? '+' : ''}${Math.max(...values).toFixed(0)}%</b></div>
          <div><span>Trough</span><b>${Math.min(...values) >= 0 ? '+' : ''}${Math.min(...values).toFixed(0)}%</b></div>
          <div><span>Snapshots</span><b>${points.length}</b></div>
        </div>
      </div>
      <div class="pf-hero-r">
        <svg viewBox="0 0 ${W} ${H}" class="pf-ytd" preserveAspectRatio="none" role="img" aria-label="Year-to-date portfolio performance">
          <polygon points="${x(0).toFixed(1)},${(H - B).toFixed(1)} ${line} ${x(points.length - 1).toFixed(1)},${(H - B).toFixed(1)}" fill="var(--bl-accent)" fill-opacity=".09"/>
          <polyline points="${line}" fill="none" stroke="var(--bl-accent)" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round"/>
          ${dots}
          <text x="${W - 4}" y="${(y(hi) + 16).toFixed(1)}" font-size="10.5" text-anchor="end" fill="var(--bl-faint)" font-family="var(--bl-mono)">${hi.toFixed(0)}%</text>
          <text x="${W - 4}" y="${(y(lo) - 4).toFixed(1)}" font-size="10.5" text-anchor="end" fill="var(--bl-faint)" font-family="var(--bl-mono)">${lo.toFixed(0)}%</text>
        </svg>
        <p class="pf-hnote">Daily end-of-day snapshots, tracking since ${short(points[0].date)}.
          <b>${points.length} point${points.length === 1 ? '' : 's'} so far</b> — the headline number, not yet a trend.
          The charts below are the honest read on recent form until this series fills in.</p>
      </div>
    </section>`;
  };

  const mount = document.createElement('div');
  mount.className = 'pf-mount';
  const draw = points => {
    const statsNodes = ['.results-stats', '.results-statline', '.results-method']
      .map(selector => panel.querySelector(selector))
      .filter(Boolean);
    mount.innerHTML = renderHero(points) + '<section class="pf-winrates" data-pf-winrates></section>' + renderTape() + renderLog();
    const statsHost = mount.querySelector('[data-pf-winrates]');
    statsNodes.forEach(node => statsHost.appendChild(node));
    // The cron block remains the no-JS fallback. Once enhanced, its headline,
    // sparkline, and action ledger are replaced by the hero, win-rate rail,
    // trade tape, and log above.
    panel.querySelector('.results-only')?.setAttribute('hidden', '');
    // Mount OUTSIDE .results-only: that wrapper is a 920px centred column whose
    // `.results-only h2` rule (up to 104px) also outranks our section headings.
    panel.appendChild(mount);
    mount.dataset.ready = 'true';
  };

  const tip = document.createElement('div');
  tip.className = 'pf-tip';
  tip.hidden = true;
  document.body.appendChild(tip);

  const showTip = el => {
    tip.innerHTML = el.dataset.tradeDetail === '1'
      ? `<b><small>Ticker</small> ${esc(el.dataset.t)}</b><span><small>Type</small> ${esc(el.dataset.s)}</span>`
        + `<em><small>P&amp;L</small> ${esc(el.dataset.v)}</em>${el.dataset.x ? `<i>Closed ${esc(el.dataset.x)}</i>` : ''}`
      : `<b>${esc(el.dataset.t)}</b><span>${esc(el.dataset.s)}</span>`
        + `<em>${esc(el.dataset.v)}</em>${el.dataset.x ? `<i>${esc(el.dataset.x)}</i>` : ''}`;
    tip.className = `pf-tip ${el.dataset.pos === '1' ? 'pos' : 'neg'}`;
    tip.hidden = false;
    const box = tip.getBoundingClientRect();
    const target = el.getBoundingClientRect();
    const left = target.left + target.width / 2 - box.width / 2;
    const above = target.top - box.height - 10;
    tip.style.left = `${Math.max(12, Math.min(left, window.innerWidth - box.width - 12))}px`;
    tip.style.top = `${above >= 12 ? above : Math.min(target.bottom + 10, window.innerHeight - box.height - 12)}px`;
  };
  document.addEventListener('pointermove', event => {
    const el = event.target.closest ? event.target.closest('.pf-hv') : null;
    if (!el) { tip.hidden = true; return; }
    showTip(el);
  });
  document.addEventListener('focusin', event => {
    const el = event.target.closest ? event.target.closest('.pf-hv') : null;
    if (!el) return;
    requestAnimationFrame(() => {
      if (document.activeElement === el) showTip(el);
    });
  });
  document.addEventListener('focusout', event => {
    if (event.target.closest && event.target.closest('.pf-hv')) tip.hidden = true;
  });

  fetch('/trading/results-ytd.json', { cache: 'no-store' })
    .then(response => (response.ok ? response.json() : null))
    .then(payload => draw(payload && payload.points))
    .catch(() => draw(null));   // charts and log still render without the series
})();
