(() => {
  'use strict';

  const shell = document.querySelector('#themes-live');
  if (!shell) return;

  const esc = value => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const num = value => {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const clamp = value => Math.max(0, Math.min(100, value));

  const meter = (label, value, tone) => {
    const parsed = num(value);
    if (parsed === null) {
      return `<div class="sat-row"><span class="sat-label">${esc(label)}</span><span class="sat-none">Not scored</span></div>`;
    }
    return `<div class="sat-row">
      <span class="sat-label">${esc(label)}</span>
      <i class="sat-track sat-${tone}" aria-hidden="true"><b style="width:${clamp(parsed)}%"></b></i>
      <strong class="sat-value">${parsed}</strong>
    </div>`;
  };

  // Knowledge minus price is the actual signal: how much of a well-known
  // story the market has not yet paid for.
  const gapOf = (known, priced) => {
    const k = num(known);
    const p = num(priced);
    return k === null || p === null ? null : k - p;
  };

  const gapTone = gap => (gap >= 25 ? 'open' : gap >= 12 ? 'mid' : 'tight');

  const fmtGap = gap => `${gap > 0 ? '+' : ''}${gap}`;

  const modelIdentity = model => {
    const name = String(model ?? '').toLowerCase();
    if (name.includes('grok')) return { key: 'grok', mark: '𝕏' };
    if (name.includes('gpt')) return { key: 'gpt', mark: '◎' };
    if (name.includes('claude') || name.includes('fable')) return { key: 'claude', mark: '✦' };
    if (name.includes('gemini')) return { key: 'gemini', mark: '◆' };
    if (name.includes('meta')) return { key: 'meta', mark: '∞' };
    return { key: 'other', mark: '●' };
  };

  const modelChip = (kind, model) => {
    const identity = modelIdentity(model);
    const label = kind === 'source' ? 'Source' : 'Review';
    return `<span class="prov-chip prov-${kind} prov-${identity.key}" title="${label}: ${esc(model)}">
      <i aria-hidden="true">${identity.mark}</i><span>${label} · ${esc(model)}</span>
    </span>`;
  };

  const renderProvenance = theme => `<div class="model-provenance" aria-label="Model provenance">
    ${modelChip('source', theme.source_model)}
    ${(theme.reviewed_by || []).map(model => modelChip('review', model)).join('')}
  </div>`;

  const sortThemesByGapDescending = themes => [...themes].sort((a, b) => {
    const aGap = gapOf(a.consensus_scores.knowledge_saturation, a.consensus_scores.price_saturation);
    const bGap = gapOf(b.consensus_scores.knowledge_saturation, b.consensus_scores.price_saturation);
    if (aGap === null) return bGap === null ? 0 : 1;
    if (bGap === null) return -1;
    return bGap - aGap;
  });

  const gapNote = (known, priced) => {
    const gap = gapOf(known, priced);
    if (gap === null) return '';
    const phrase = gap >= 25 ? 'Widely understood, not fully priced'
      : gap >= 12 ? 'Understood, partly discounted'
      : gap >= 0 ? 'Priced close to the story'
      : 'Priced ahead of what is understood';
    return `<p class="sat-gap tone-${gapTone(gap)}">
      <strong>${fmtGap(gap)}</strong>
      <span>${esc(phrase)}</span>
    </p>`;
  };

  const gapBadge = (known, priced) => {
    const gap = gapOf(known, priced);
    if (gap === null) return '';
    return `<span class="layer-gap tone-${gapTone(gap)}" title="Knowledge saturation minus price saturation">
      ${fmtGap(gap)}<i>gap</i></span>`;
  };

  const bullets = items => `<ul class="theme-list">${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;

  const renderModels = models => `<div class="model-grid">${models.map(model => `
    <article class="model-card">
      <p class="model-role">${esc(model.role)}</p>
      <h4>${esc(model.model)}</h4>
      <div class="model-meters">
        ${meter('Known', model.knowledge_saturation, 'known')}
        ${meter('Priced', model.price_saturation, 'priced')}
      </div>
      <p class="model-verdict">${esc(model.verdict)}</p>
    </article>`).join('')}</div>`;

  const renderLayers = rows => `<div class="layer-grid">${rows.map(row => `
    <article class="layer-card">
      <div class="layer-head">
        <h4>${esc(row.layer)}</h4>
        ${gapBadge(row.knowledge_saturation, row.price_saturation)}
      </div>
      <p class="layer-symbols">${esc(row.symbols)}</p>
      <div class="layer-meters">
        ${meter('Known', row.knowledge_saturation, 'known')}
        ${meter('Priced', row.price_saturation, 'priced')}
      </div>
      <p class="layer-read">${esc(row.read)}</p>
    </article>`).join('')}</div>`;

  const renderBuckets = rows => `<div class="bucket-grid">${rows.map((row, index) => `
    <article class="bucket-card bucket-${index + 1}">
      <p class="bucket-label">${esc(row.bucket)}</p>
      <p class="bucket-symbols">${esc(row.symbols)}</p>
      <p class="bucket-why">${esc(row.why)}</p>
    </article>`).join('')}</div>`;

  const renderValuation = snapshot => `<div class="val-wrap">
    <table class="val-table">
      <thead><tr><th>Symbol</th><th class="num">Price</th><th class="num">Trailing P/E</th><th class="num">Off 52-wk high</th></tr></thead>
      <tbody>${snapshot.rows.map(row => `<tr>
        <td class="val-sym">${esc(row.symbol)}</td>
        <td class="num">${esc(row.price)}</td>
        <td class="num">${esc(row.pe)}</td>
        <td class="num val-off">${esc(row.off_high)}</td>
      </tr>`).join('')}</tbody>
    </table>
    <p class="val-note">${esc(snapshot.source)} · ${esc(snapshot.date)} · ${esc(snapshot.note)}</p>
  </div>`;

  const renderAdversarial = review => {
    const columns = Array.isArray(review) ? review : [
      { title: 'Where Grok breaks', bullets: review.grok },
      { title: 'Where Fable breaks', bullets: review.fable },
    ];
    return `<div class="attack-grid">${columns.map(column => `
      <article class="attack-card">
        <h4>${esc(column.title)}</h4>
        ${bullets(column.bullets)}
      </article>`).join('')}</div>`;
  };

  const openSection = (id, title, blurb, body) => `
    <section class="theme-section" id="${esc(id)}" aria-labelledby="${esc(id)}-h">
      <div class="theme-section-head">
        <h3 id="${esc(id)}-h">${esc(title)}</h3>
        <p>${esc(blurb)}</p>
      </div>
      ${body}
    </section>`;

  const foldSection = (id, title, blurb, body) => `
    <details class="theme-section theme-fold" id="${esc(id)}">
      <summary>
        <span class="fold-title">${esc(title)}</span>
        <span class="fold-blurb">${esc(blurb)}</span>
      </summary>
      <div class="fold-body">${body}</div>
    </details>`;

  const renderTheme = (theme, method) => {
    const sectionId = suffix => `${theme.id}-${suffix}`;
    const { knowledge_saturation: known, price_saturation: priced } = theme.consensus_scores;

    return `<article class="theme-record" id="${esc(theme.id)}">
    <header class="theme-hero">
      <div class="theme-kicker">
        <span>${esc(theme.category)}</span><span>${esc(theme.horizon)}</span><span>${esc(theme.status)}</span>
      </div>
      ${renderProvenance(theme)}
      <h2>${esc(theme.title)}</h2>
      ${theme.disqualified ? `<div class="theme-disqualified"><strong>Disqualified</strong><span>${esc(theme.disqualified.reason)}</span></div>` : ''}
      ${theme.qualified && !theme.disqualified ? `<div class="theme-disqualified theme-qualified"><strong>Active play</strong><span>${esc(theme.qualified.position)} · ${esc(theme.qualified.date)} — ${esc(theme.qualified.note)}</span></div>` : ''}
      <p class="theme-belief">${esc(theme.owner_belief)}</p>
      <div class="hero-scores">
        <div class="hero-meters">
          ${meter('Known', known, 'known')}
          ${meter('Priced', priced, 'priced')}
          ${gapNote(known, priced)}
        </div>
        <p class="theme-conviction">${esc(theme.conviction)}</p>
      </div>
      <div class="theme-verdict">
        <p class="verdict-label">Final verdict</p>
        <p>${esc(theme.final_verdict)}</p>
      </div>
    </header>

    <details class="theme-method">
      <summary>How to read these scores</summary>
      <div class="method-body">
        <p><strong>Known</strong> ${esc(method.knowledge_saturation)}</p>
        <p><strong>Priced</strong> ${esc(method.price_saturation)}</p>
        <p><strong>Gap</strong> Known minus priced. A wide gap flags a story the market understands but has not paid for; a narrow or negative gap flags one already discounted.</p>
        <p><strong>Consensus</strong> ${esc(method.consensus)}</p>
        <p class="method-warn"><strong>Important</strong> ${esc(method.warning)}</p>
      </div>
    </details>

    ${openSection(sectionId('layers'), 'Saturation by layer',
      'One theme, radically different prices. Sorted by the author; scan the gap column first.',
      renderLayers(theme.layer_scorecard))}

    ${openSection(sectionId('attack'), 'Adversarial review',
      'The thesis and the stock map both get punched in the face.',
      renderAdversarial(theme.adversarial_review))}

    <div class="theme-two-up">
      ${openSection(sectionId('survived'), 'What survives the attack',
        'The parts strong enough to keep.', bullets(theme.what_survived))}
      ${openSection(sectionId('edge'), 'Where edge may remain',
        'Contracts and constraints, not the headline.', bullets(theme.residual_edge))}
    </div>

    ${openSection(sectionId('priority'), 'Research priority',
      'A diligence queue, not a buy list.', renderBuckets(theme.research_priority))}

    ${openSection(sectionId('models'), 'Model reviews',
      'Missing reviewers stay missing; scores are never padded.',
      renderModels(theme.model_reviews))}

    ${foldSection(sectionId('valuation'), 'Valuation snapshot',
      `${theme.valuation_snapshot.rows.length} names · closing prices`,
      renderValuation(theme.valuation_snapshot))}

    ${foldSection(sectionId('falsifiers'), 'Falsifiers',
      `${theme.falsifiers.length} ways this thesis dies`, bullets(theme.falsifiers))}

    ${foldSection(sectionId('watch'), 'Watch next',
      `${theme.watch_next.length} signals that move the score`, bullets(theme.watch_next))}

    ${foldSection(sectionId('sources'), 'Sources',
      `${theme.sources.length} primary references`,
      `<div class="source-list">${theme.sources.map(source =>
        `<a href="${esc(source.url)}" rel="noopener noreferrer" target="_blank">${esc(source.label)}</a>`).join('')}</div>
       <p class="source-note">Thematic research, not investment advice. Scores are judgments, not forecasts.</p>`)}
  </article>`;
  };

  // ── Ledger index (v2) ──────────────────────────────────────────────
  // The page is an index now: category filters + a sortable ledger.
  // Full records render on demand inside an overlay,
  // addressed by the same #theme-id anchors the old long-scroll page
  // used, so shared deep links keep working.

  const CATEGORY_COLOR = {
    Geographies: '#2f5fb3',
    Sectors: '#0e7a63',
    Emerging: '#8a4bab',
    Energy: '#b3622f',
    'Frontier intelligence': '#5c5f66',
  };
  const catColor = category => CATEGORY_COLOR[category] || '#70757d';

  // Maturity chip = the status text before the "· N reviewers" suffix,
  // verbatim from themes.json. Reviewer count already shows as icons.
  const stageOf = status => String(status ?? '').split('·')[0].trim();

  const modelIcon = (kind, model) => {
    const identity = modelIdentity(model);
    const label = kind === 'source' ? 'Source' : 'Review';
    return `<i class="mi mi-${identity.key} mi-${kind}" title="${label}: ${esc(model)}"></i>`;
  };

  const modelIcons = theme => {
    const reviewers = theme.reviewed_by || [];
    return `<span class="micons" aria-label="Source ${esc(theme.source_model)}${
      reviewers.length ? ', reviewed by ' + esc(reviewers.join(', ')) : ''}">${
      modelIcon('source', theme.source_model)}${
      reviewers.length ? '<i class="mi-sep" aria-hidden="true"></i>' + reviewers.map(model => modelIcon('review', model)).join('') : ''
    }</span>`;
  };

  const rowOf = theme => ({
    theme,
    title: theme.title,
    category: theme.category,
    stage: stageOf(theme.status),
    known: num(theme.consensus_scores.knowledge_saturation),
    priced: num(theme.consensus_scores.price_saturation),
    gap: gapOf(theme.consensus_scores.knowledge_saturation, theme.consensus_scores.price_saturation),
    models: 1 + (theme.reviewed_by || []).length,
    horizon: theme.horizon,
  });

  const state = { cats: new Set(), minGap: 0, sortKey: 'gap', sortDir: -1 };
  let rows = [];
  let qualifiedRows = [];
  let disqualifiedRows = [];
  let byId = new Map();
  let methodRef = null;

  const visibleRows = () => rows.filter(row =>
    (!state.cats.size || state.cats.has(row.category)) &&
    (state.minGap === 0 || row.gap >= state.minGap));

  const NUMERIC_KEYS = new Set(['known', 'priced', 'gap', 'models']);
  const sortedRows = list => [...list].sort((a, b) => {
    if (NUMERIC_KEYS.has(state.sortKey)) {
      return ((a[state.sortKey] ?? -1) - (b[state.sortKey] ?? -1)) * state.sortDir;
    }
    return String(a[state.sortKey]).localeCompare(String(b[state.sortKey])) * state.sortDir;
  });

  const renderControls = () => {
    const categories = [...new Set(rows.map(row => row.category))];
    return `<div class="ledger-controls">
      <div class="fpills" role="group" aria-label="Filter by category">
        ${categories.map(category => `<button type="button" class="fpill${state.cats.has(category) ? ' on' : ''}" data-cat="${esc(category)}">
          <i style="background:${catColor(category)}" aria-hidden="true"></i>${esc(category)}<b>${rows.filter(row => row.category === category).length}</b>
        </button>`).join('')}
      </div>
      <label class="gapctl">Min gap <input type="range" min="0" max="50" step="5" value="${state.minGap}" data-gap-range>
        <b data-gap-value>${state.minGap}</b></label>
      <span class="lcount" data-count aria-live="polite"></span>
    </div>`;
  };


  const LEDGER_COLUMNS = [
    ['title', 'Theme'], ['category', 'Category'], ['models', 'Models'], ['stage', 'Maturity'],
    ['known', 'Known'], ['priced', 'Priced'], ['gap', 'Gap'], ['horizon', 'Horizon'],
  ];

  const renderLedger = list => `<table class="themes-ledger" aria-label="Theme ledger">
    <thead><tr>${LEDGER_COLUMNS.map(([key, label]) => `
      <th${NUMERIC_KEYS.has(key) && key !== 'models' ? ' class="r"' : ''} data-sort="${key}"
        aria-sort="${state.sortKey === key ? (state.sortDir === 1 ? 'ascending' : 'descending') : 'none'}">
        <button type="button">${label}<span class="arrow">${state.sortKey === key ? (state.sortDir === 1 ? '▴' : '▾') : ''}</span></button>
      </th>`).join('')}</tr></thead>
    <tbody>${list.map(row => `<tr class="lrow" data-theme-id="${esc(row.theme.id)}">
      <td class="lt"><button type="button" class="lt-btn">${esc(row.title)}</button></td>
      <td><span class="lcat"><i style="background:${catColor(row.category)}" aria-hidden="true"></i>${esc(row.category)}</span></td>
      <td>${modelIcons(row.theme)}</td>
      <td><span class="lstage">${esc(row.stage)}</span></td>
      <td class="r lknown">${row.known}</td>
      <td class="r lpriced">${row.priced}</td>
      <td class="r lgap tone-${gapTone(row.gap)}">${fmtGap(row.gap)}</td>
      <td class="lhor">${esc(row.horizon)}</td>
    </tr>`).join('')}</tbody>
  </table>`;

  const renderQualified = list => {
    if (!list.length) return '';
    return `<section class="disqualified-themes qualified-themes" aria-labelledby="qualified-themes-heading">
      <div class="dq-head">
        <h2 id="qualified-themes-heading">Active plays</h2>
        <p>Research graduated into live positions — click a row for the full record.</p>
      </div>
      <div class="dq-wrap">
        <table class="dq-table" aria-label="Active plays">
          <thead><tr><th>Theme</th><th>Position note</th><th>Position</th></tr></thead>
          <tbody>${list.map(row => `<tr class="dq-row" data-theme-id="${esc(row.theme.id)}">
            <td><button type="button" class="lt-btn">${esc(row.title)}</button></td>
            <td>${esc(row.theme.qualified.note)}</td>
            <td class="dq-symbols">${esc(row.theme.qualified.position)} · ${esc(row.theme.qualified.date)}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    </section>`;
  };

  const renderDisqualified = list => {
    if (!list.length) return '';
    return `<section class="disqualified-themes" aria-labelledby="disqualified-themes-heading">
      <div class="dq-head">
        <h2 id="disqualified-themes-heading">Disqualified themes</h2>
        <p>Retained so rejected ideas don't get recreated.</p>
      </div>
      <div class="dq-wrap">
        <table class="dq-table" aria-label="Disqualified themes">
          <thead><tr><th>Theme</th><th>Reason</th><th>Flagged tickers</th></tr></thead>
          <tbody>${list.map(row => `<tr class="dq-row" data-theme-id="${esc(row.theme.id)}">
            <td><button type="button" class="lt-btn">${esc(row.title)}</button></td>
            <td>${esc(row.theme.disqualified.reason)}</td>
            <td class="dq-symbols">${esc(row.theme.disqualified.symbols.join(' · '))}</td>
          </tr>`).join('')}</tbody>
        </table>
      </div>
    </section>`;
  };

  const renderMethodFold = method => `<details class="theme-method ledger-method">
    <summary>How to read these scores</summary>
    <div class="method-body">
      <p><strong>Known</strong> ${esc(method.knowledge_saturation)}</p>
      <p><strong>Priced</strong> ${esc(method.price_saturation)}</p>
      <p><strong>Gap</strong> Known minus priced. A wide gap flags a story the market understands but has not paid for; a narrow or negative gap flags one already discounted.</p>
      <p><strong>Consensus</strong> ${esc(method.consensus)}</p>
      <p class="method-warn"><strong>Important</strong> ${esc(method.warning)}</p>
    </div>
  </details>`;

  const updateViews = () => {
    const list = sortedRows(visibleRows());
    shell.querySelector('[data-ledger]').innerHTML = renderLedger(list);
    shell.querySelector('[data-count]').textContent = `${list.length} of ${rows.length} themes`;
  };

  // ── Record overlay ─────────────────────────────────────────────────
  let overlay = null;
  let openedByPush = false;
  let lastFocus = null;

  const buildOverlay = () => {
    overlay = document.createElement('div');
    overlay.className = 'rec-overlay';
    overlay.hidden = true;
    overlay.innerHTML = `<div class="rec-backdrop" data-rec-close></div>
      <div class="rec-panel" role="dialog" aria-modal="true" aria-label="Theme record">
        <div class="rec-bar">
          <a class="rec-permalink" href="#"></a>
          <button type="button" class="rec-close" data-rec-close>Close ✕</button>
        </div>
        <div class="rec-body"></div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', event => {
      if (event.target.closest('[data-rec-close]')) closeRecord();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !overlay.hidden) closeRecord();
    });
    window.addEventListener('popstate', () => syncFromHash(false));
  };

  const openRecord = (theme, { push = true, section = null } = {}) => {
    lastFocus = document.activeElement;
    overlay.querySelector('.rec-body').innerHTML = renderTheme(theme, methodRef);
    const permalink = overlay.querySelector('.rec-permalink');
    permalink.href = `#${theme.id}`;
    permalink.textContent = `/trading/themes/#${theme.id}`;
    overlay.hidden = false;
    document.body.classList.add('rec-open');
    if (push) {
      history.pushState({ theme: theme.id }, '', `#${section || theme.id}`);
      openedByPush = true;
    }
    const panel = overlay.querySelector('.rec-panel');
    panel.scrollTop = 0;
    if (section) {
      const target = overlay.querySelector(`#${CSS.escape(section)}`);
      if (target) {
        const fold = target.closest('details');
        if (fold) fold.open = true;
        target.scrollIntoView();
      }
    }
    overlay.querySelector('.rec-close').focus();
  };

  const closeRecord = () => {
    if (openedByPush) {
      openedByPush = false;
      history.back(); // popstate → syncFromHash hides the overlay
      return;
    }
    hideOverlay();
    if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  };

  const hideOverlay = () => {
    overlay.hidden = true;
    document.body.classList.remove('rec-open');
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
  };

  // Deep links: #theme-id opens the record, #theme-id-section opens it
  // scrolled to that section — the anchors the long-scroll page used.
  const syncFromHash = (push = false) => {
    const hash = decodeURIComponent(location.hash.slice(1));
    if (!hash) { if (!overlay.hidden) hideOverlay(); return; }
    if (byId.has(hash)) { openRecord(byId.get(hash), { push }); return; }
    const parent = [...byId.keys()].find(id => hash.startsWith(`${id}-`));
    if (parent) { openRecord(byId.get(parent), { push, section: hash }); return; }
    if (!overlay.hidden) hideOverlay();
  };

  const wireShell = () => {
    shell.addEventListener('click', event => {
      const pill = event.target.closest('.fpill');
      if (pill) {
        const category = pill.dataset.cat;
        state.cats.has(category) ? state.cats.delete(category) : state.cats.add(category);
        pill.classList.toggle('on');
        updateViews();
        return;
      }
      const header = event.target.closest('th[data-sort]');
      if (header) {
        const key = header.dataset.sort;
        if (state.sortKey === key) {
          state.sortDir *= -1;
        } else {
          state.sortKey = key;
          state.sortDir = NUMERIC_KEYS.has(key) ? -1 : 1;
        }
        updateViews();
        return;
      }
      const opener = event.target.closest('[data-theme-id]');
      if (opener && byId.has(opener.dataset.themeId)) {
        openRecord(byId.get(opener.dataset.themeId));
      }
    });

    shell.addEventListener('input', event => {
      if (!event.target.matches('[data-gap-range]')) return;
      state.minGap = Number(event.target.value);
      shell.querySelector('[data-gap-value]').textContent = state.minGap;
      updateViews();
    });

  };

  fetch(shell.dataset.url, { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error(`Themes request failed: ${response.status}`);
      return response.json();
    })
    .then(payload => {
      methodRef = payload.method;
      const themes = sortThemesByGapDescending(payload.themes);
      rows = themes.filter(theme => !theme.disqualified && !theme.qualified).map(rowOf);
      qualifiedRows = themes.filter(theme => theme.qualified && !theme.disqualified).map(rowOf);
      disqualifiedRows = themes.filter(theme => theme.disqualified).map(rowOf);
      byId = new Map(themes.map(theme => [theme.id, theme]));
      shell.innerHTML = renderQualified(qualifiedRows)
        + renderControls()
        + `<div class="ledger-wrap" data-ledger></div>
           <p class="ledger-foot">Colored icon sourced the theme · gray icons reviewed it · hover an icon for the model · click any row for the full record.</p>`
        + renderDisqualified(disqualifiedRows)
        + renderMethodFold(payload.method);
      buildOverlay();
      updateViews();
      wireShell();
      shell.dataset.ready = 'true';
      syncFromHash(false);
    })
    .catch(error => {
      // Keep the baked static snapshot readable instead of replacing it.
      shell.insertAdjacentHTML('afterbegin',
        '<p class="theme-error">The interactive ledger could not load; the static snapshot below has every theme.</p>');
      console.error(error);
    });
})();
