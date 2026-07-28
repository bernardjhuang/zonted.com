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
      <strong>${gap > 0 ? '+' : ''}${gap}</strong>
      <span>${esc(phrase)}</span>
    </p>`;
  };

  const gapBadge = (known, priced) => {
    const gap = gapOf(known, priced);
    if (gap === null) return '';
    return `<span class="layer-gap tone-${gapTone(gap)}" title="Knowledge saturation minus price saturation">
      ${gap > 0 ? '+' : ''}${gap}<i>gap</i></span>`;
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

  const renderNav = themes => `<nav class="theme-switch" aria-label="Jump to theme">
    ${themes.map((theme, index) => {
      const gap = gapOf(theme.consensus_scores.knowledge_saturation, theme.consensus_scores.price_saturation);
      return `<a class="theme-pill${index === 0 ? ' is-current' : ''}" href="#${esc(theme.id)}" data-theme="${esc(theme.id)}">
        <span class="pill-cat">${esc(theme.category)}</span>
        <span class="pill-title">${esc(theme.title)}</span>
        ${renderProvenance(theme)}
        <span class="pill-scores">
          <b>${esc(theme.consensus_scores.knowledge_saturation)}</b> known
          <b>${esc(theme.consensus_scores.price_saturation)}</b> priced
          ${gap === null ? '' : `<em class="tone-${gapTone(gap)}">${gap > 0 ? '+' : ''}${gap} gap</em>`}
        </span>
      </a>`;
    }).join('')}
  </nav>`;

  // Keep the sticky theme switcher docked under the variable-height status bar.
  const statusBar = document.querySelector('.status');
  const syncStickyOffset = () => {
    if (!statusBar) return;
    document.documentElement.style.setProperty('--desk-top', `${statusBar.offsetHeight}px`);
  };

  const trackCurrentTheme = () => {
    const pills = [...shell.querySelectorAll('.theme-pill')];
    const records = [...shell.querySelectorAll('.theme-record')];
    if (!pills.length || !records.length || !('IntersectionObserver' in window)) return;

    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        pills.forEach(pill => pill.classList.toggle('is-current', pill.dataset.theme === entry.target.id));
      });
    }, { rootMargin: '-45% 0px -50% 0px' });

    records.forEach(record => observer.observe(record));
  };

  fetch(shell.dataset.url, { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error(`Themes request failed: ${response.status}`);
      return response.json();
    })
    .then(payload => {
      const themes = sortThemesByGapDescending(payload.themes);
      shell.innerHTML = renderNav(themes)
        + themes.map(theme => renderTheme(theme, payload.method)).join('');
      shell.dataset.ready = 'true';
      syncStickyOffset();
      if (window.ResizeObserver && statusBar) new ResizeObserver(syncStickyOffset).observe(statusBar);
      window.addEventListener('resize', syncStickyOffset);
      trackCurrentTheme();
    })
    .catch(error => {
      shell.innerHTML = '<p class="theme-error">Themes could not be loaded. The previous research remains in the JSON source.</p>';
      console.error(error);
    });
})();
