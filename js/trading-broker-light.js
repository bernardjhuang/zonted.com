/* Broker Light behavior for /trading/ (design handoff 2026-07-21).
   Parses the cron-emitted markup in #bl-raw (positions chips, activity rows,
   YTD extremes) into sortable/filterable tables. The raw markup stays in the
   DOM (hidden) so the nightly snapshot cron keeps working unchanged. */
(() => {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const fmtISO = iso => {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '');
    return m ? `${MONTHS[+m[2] - 1]} ${+m[3]} ${m[1]}` : '—';
  };

  /* ── tabs ─────────────────────────────────────────────────────────── */
  const tabs = $$('[role="tab"]');
  const panelOf = t => document.getElementById(t.getAttribute('aria-controls'));
  const panels = [...new Set(tabs.map(panelOf))];
  function activate(tab, push) {
    tabs.forEach(t => { const on = t === tab; t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1; });
    const target = panelOf(tab);
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

  /* ── momentum-scan Spread Z accordions ───────────────────────────── */
  const scanPanel = $('#scan-panel');
  const spreadSource = $('#scan-spread-data');
  if (scanPanel && spreadSource) {
    let spreadData = {};
    try { spreadData = JSON.parse(spreadSource.textContent); } catch (error) { console.error('Invalid Spread Z data', error); }
    const chartDate = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' });
    let openToggle = null;

    const fmtChartDate = iso => chartDate.format(new Date(`${iso}T12:00:00`));
    const fmtZ = value => `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(2)}`;
    const chartStatus = value => value > 1 ? 'Leading SPY' : value < -1 ? 'Lagging SPY' : 'Inside neutral band';

    function renderSpreadChart(shell, symbol) {
      if (shell.dataset.rendered === 'true') return;
      const series = spreadData[symbol];
      if (!series || !series.values || !series.values.length) {
        shell.innerHTML = '<p class="scan-null">Spread Z history unavailable.</p>';
        shell.dataset.rendered = 'true';
        return;
      }
      const values = series.values, dates = series.dates;
      const W = 960, H = 220, L = 46, R = 16, T = 16, B = 30;
      const iw = W - L - R, ih = H - T - B;
      const rawMin = Math.min(-1.5, ...values), rawMax = Math.max(1.5, ...values);
      const pad = Math.max(0.2, (rawMax - rawMin) * 0.08);
      const lo = rawMin - pad, hi = rawMax + pad;
      const x = i => L + (values.length === 1 ? 0 : i / (values.length - 1) * iw);
      const y = value => T + (hi - value) / (hi - lo) * ih;
      const points = values.map((value, i) => `${x(i).toFixed(1)},${y(value).toFixed(1)}`).join(' ');
      const baseY = y(0).toFixed(1);
      const fillPoints = `${L},${baseY} ${points} ${W - R},${baseY}`;
      const levels = [-2, -1, 0, 1, 2].filter(value => value >= lo && value <= hi);
      const grid = levels.map(value => `<line x1="${L}" y1="${y(value).toFixed(1)}" x2="${W - R}" y2="${y(value).toFixed(1)}" class="${Math.abs(value) === 1 ? 'scan-spread-threshold' : 'scan-spread-grid'}"/><text x="${L - 8}" y="${(y(value) + 3.5).toFixed(1)}" text-anchor="end" class="scan-spread-axis">${value > 0 ? '+' : ''}${value}</text>`).join('');
      const mid = Math.floor((dates.length - 1) / 2);
      const current = values[values.length - 1];
      const observedMin = Math.min(...values), observedMax = Math.max(...values);
      const detailId = shell.closest('[data-scan-detail]').id;
      const titleId = `${detailId}-title`, descId = `${detailId}-desc`;
      const range = `${fmtZ(observedMin)} to ${fmtZ(observedMax)}`;
      shell.innerHTML = `<div class="scan-spread-head"><h4 id="${titleId}">${symbol} Spread Z</h4><p>${fmtChartDate(dates[0])}–${fmtChartDate(dates[dates.length - 1])} · ${values.length} sessions · range ${range}</p><span class="scan-spread-current ${current >= 0 ? 'scan-z-pos' : 'scan-z-neg'}">${fmtZ(current)} · ${chartStatus(current)}</span></div>
        <svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="${titleId} ${descId}" preserveAspectRatio="none">
          <desc id="${descId}">${symbol} Spread Z ranged from ${range} and finished at ${fmtZ(current)}. Guides mark the long threshold at plus one, the SPY baseline at zero, and the short threshold at minus one.</desc>
          <rect x="${L}" y="${T}" width="${iw}" height="${Math.max(0, y(1) - T).toFixed(1)}" class="scan-spread-band--long"/>
          <rect x="${L}" y="${y(-1).toFixed(1)}" width="${iw}" height="${Math.max(0, T + ih - y(-1)).toFixed(1)}" class="scan-spread-band--short"/>
          ${grid}<polygon points="${fillPoints}" class="scan-spread-fill"/><polyline points="${points}" class="scan-spread-line"/>
          <circle cx="${x(values.length - 1).toFixed(1)}" cy="${y(current).toFixed(1)}" r="4" class="${current >= 0 ? 'scan-spread-dot--pos' : 'scan-spread-dot--neg'}"/>
          <text x="${L}" y="${H - 7}" class="scan-spread-axis">${fmtChartDate(dates[0])}</text>
          <text x="${x(mid).toFixed(1)}" y="${H - 7}" text-anchor="middle" class="scan-spread-axis">${fmtChartDate(dates[mid])}</text>
          <text x="${W - R}" y="${H - 7}" text-anchor="end" class="scan-spread-axis">${fmtChartDate(dates[dates.length - 1])}</text>
        </svg><div class="scan-spread-legend"><span>+1 long threshold</span><span>0 matches SPY</span><span>−1 short threshold</span></div>`;
      shell.dataset.rendered = 'true';
    }

    function syncChartParam(symbol) {
      const url = new URL(location.href);
      if (symbol) url.searchParams.set('chart', symbol); else url.searchParams.delete('chart');
      history.replaceState(null, '', url);
    }

    function closeChart(toggle, sync = true) {
      if (!toggle) return;
      const detail = document.getElementById(toggle.getAttribute('aria-controls'));
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', `Show ${toggle.closest('[data-scan-row]').dataset.scanSymbol} Spread Z chart`);
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
      toggle.setAttribute('aria-label', `Hide ${row.dataset.scanSymbol} Spread Z chart`);
      row.classList.add('is-open');
      detail.hidden = false;
      renderSpreadChart($('[data-scan-chart]', detail), row.dataset.scanSymbol);
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
      if (initialToggle) openChart(initialToggle, false);
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

  const arrow = (sort, key) => sort.key === key ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ⇅';
  const pnlCls = v => v > 0 ? 'bl-gain' : v < 0 ? 'bl-loss' : '';
  const sideCls = s => /long|call/i.test(s) ? 'bl-gain' : /short|put/i.test(s) ? 'bl-loss' : '';

  function render() {
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
    const posRows = pos.map(p => `<div class="bl-row g-pos">
      <span class="sym">${p.sym}</span><span>${p.type}</span>
      <span class="${sideCls(p.side)}">${p.side}</span>
      <span class="mono">${p.strike}</span><span class="mono mut">${p.expiry}</span>
      <span class="r mono ${p.since === '—' ? 'mut' : pnlCls(parseFloat(p.since.replace('−', '-')))}">${p.since}</span>
    </div>`).join('') || '<div class="bl-empty">No positions match the current filters.</div>';

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
        <div class="bl-card"><div class="bl-card-title">Recent buys <span>· $2K+ · same-day round trips excluded</span></div>
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
