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
    if (tab.id === 'ytd-tab') requestAnimationFrame(() => $('#bl-ext') && $('#bl-ext').scrollIntoView({ block: 'start' }));
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
  const fromHash = () => tabs.find(t => location.hash === '#' + t.id.replace(/-tab$/, '')) || tabs[0];
  activate(fromHash());
  addEventListener('hashchange', () => activate(fromHash()));

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
