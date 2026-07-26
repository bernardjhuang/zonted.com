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

  const score = (label, value, tone = '') => {
    const missing = value === null || value === undefined || value === '';
    const numeric = missing ? Number.NaN : Number(value);
    return `<div class="theme-score ${tone}">
      <span>${esc(label)}</span>
      <strong>${Number.isFinite(numeric) ? `${numeric}/100` : 'Not scored'}</strong>
      ${Number.isFinite(numeric) ? `<i aria-hidden="true"><b style="width:${Math.max(0, Math.min(100, numeric))}%"></b></i>` : ''}
    </div>`;
  };

  const bullets = items => `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;

  const renderModels = models => `<div class="theme-model-grid">${models.map(model => `
    <article class="theme-model">
      <div class="theme-model-head"><div><span>${esc(model.role)}</span><h3>${esc(model.model)}</h3></div></div>
      <div class="theme-mini-scores">
        ${score('Knowledge', model.knowledge_saturation)}
        ${score('Price', model.price_saturation)}
      </div>
      <p>${esc(model.verdict)}</p>
    </article>`).join('')}</div>`;

  const renderLayers = rows => `<div class="theme-table-wrap"><table class="theme-table">
    <thead><tr><th>Layer</th><th>Public names</th><th class="num">Known</th><th class="num">Priced</th><th>Read</th></tr></thead>
    <tbody>${rows.map(row => `<tr>
      <td><strong>${esc(row.layer)}</strong></td>
      <td class="mono">${esc(row.symbols)}</td>
      <td class="num"><span class="theme-score-pill">${esc(row.knowledge_saturation)}</span></td>
      <td class="num"><span class="theme-score-pill">${esc(row.price_saturation)}</span></td>
      <td>${esc(row.read)}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;

  const renderBuckets = rows => `<div class="theme-bucket-grid">${rows.map(row => `
    <article class="theme-bucket">
      <span>${esc(row.bucket)}</span>
      <h3>${esc(row.symbols)}</h3>
      <p>${esc(row.why)}</p>
    </article>`).join('')}</div>`;

  const renderValuation = snapshot => `<div class="theme-table-wrap"><table class="theme-table theme-valuation">
    <thead><tr><th>Symbol</th><th class="num">Price</th><th class="num">Trailing P/E</th><th class="num">Off 52-week high</th></tr></thead>
    <tbody>${snapshot.rows.map(row => `<tr><td class="mono"><strong>${esc(row.symbol)}</strong></td><td class="num mono">${esc(row.price)}</td><td class="num mono">${esc(row.pe)}</td><td class="num mono">${esc(row.off_high)}</td></tr>`).join('')}</tbody>
  </table><p class="theme-table-note">${esc(snapshot.source)} · ${esc(snapshot.date)} · ${esc(snapshot.note)}</p></div>`;

  const renderTheme = (theme, method) => `<article class="theme-record" id="${esc(theme.id)}">
    <header class="theme-hero">
      <div class="theme-kicker"><span>${esc(theme.category)}</span><span>${esc(theme.horizon)}</span><span>${esc(theme.status)}</span></div>
      <h2>${esc(theme.title)}</h2>
      <p class="theme-belief">${esc(theme.owner_belief)}</p>
      <p class="theme-conviction">${esc(theme.conviction)}</p>
      <div class="theme-consensus" aria-label="Consensus saturation scores">
        ${score('Knowledge saturation', theme.consensus_scores.knowledge_saturation, 'knowledge')}
        ${score('Price saturation', theme.consensus_scores.price_saturation, 'price')}
      </div>
      <p class="theme-verdict"><strong>Final verdict</strong>${esc(theme.final_verdict)}</p>
    </header>

    <details class="theme-method">
      <summary>How the scores work</summary>
      <p><strong>Knowledge:</strong> ${esc(method.knowledge_saturation)}</p>
      <p><strong>Price:</strong> ${esc(method.price_saturation)}</p>
      <p><strong>Consensus:</strong> ${esc(method.consensus)}</p>
      <p><strong>Important:</strong> ${esc(method.warning)}</p>
    </details>

    <section class="theme-section" aria-labelledby="model-reviews-heading">
      <div class="theme-section-head"><span>01</span><div><h2 id="model-reviews-heading">Model reviews</h2><p>The disagreement is the useful part.</p></div></div>
      ${renderModels(theme.model_reviews)}
    </section>

    <section class="theme-section" aria-labelledby="layer-scorecard-heading">
      <div class="theme-section-head"><span>02</span><div><h2 id="layer-scorecard-heading">Saturation by layer</h2><p>One theme, radically different prices and economics.</p></div></div>
      ${renderLayers(theme.layer_scorecard)}
    </section>

    <section class="theme-section" aria-labelledby="adversarial-heading">
      <div class="theme-section-head"><span>03</span><div><h2 id="adversarial-heading">Adversarial review</h2><p>Both source theses get punched in the face.</p></div></div>
      <div class="theme-dual-review">
        <article><h3>Where Grok breaks</h3>${bullets(theme.adversarial_review.grok)}</article>
        <article><h3>Where Fable breaks</h3>${bullets(theme.adversarial_review.fable)}</article>
      </div>
    </section>

    <section class="theme-section" aria-labelledby="survived-heading">
      <div class="theme-section-head"><span>04</span><div><h2 id="survived-heading">What survives the attack</h2><p>The parts strong enough to keep.</p></div></div>
      <div class="theme-copy-card">${bullets(theme.what_survived)}</div>
    </section>

    <section class="theme-section" aria-labelledby="edge-heading">
      <div class="theme-section-head"><span>05</span><div><h2 id="edge-heading">Where edge may remain</h2><p>Contracts and constraints, not the headline.</p></div></div>
      <div class="theme-copy-card theme-edge">${bullets(theme.residual_edge)}</div>
    </section>

    <section class="theme-section" aria-labelledby="priority-heading">
      <div class="theme-section-head"><span>06</span><div><h2 id="priority-heading">Research priority</h2><p>This is a diligence queue, not a buy list.</p></div></div>
      ${renderBuckets(theme.research_priority)}
    </section>

    <section class="theme-section" aria-labelledby="valuation-heading">
      <div class="theme-section-head"><span>07</span><div><h2 id="valuation-heading">Valuation snapshot</h2><p>Friday close context for the market’s current grading.</p></div></div>
      ${renderValuation(theme.valuation_snapshot)}
    </section>

    <section class="theme-section theme-two-up" aria-label="Falsifiers and monitoring">
      <article><div class="theme-section-head compact"><span>08</span><div><h2>Falsifiers</h2><p>Evidence that kills or weakens the thesis.</p></div></div>${bullets(theme.falsifiers)}</article>
      <article><div class="theme-section-head compact"><span>09</span><div><h2>Watch next</h2><p>Evidence that updates the score.</p></div></div>${bullets(theme.watch_next)}</article>
    </section>

    <footer class="theme-sources">
      <h2>Sources</h2>
      <div>${theme.sources.map(source => `<a href="${esc(source.url)}" rel="noopener noreferrer">${esc(source.label)}</a>`).join('')}</div>
      <p>Thematic research, not investment advice. Scores are judgments, not forecasts.</p>
    </footer>
  </article>`;

  fetch(shell.dataset.url, { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error(`Themes request failed: ${response.status}`);
      return response.json();
    })
    .then(payload => {
      shell.innerHTML = payload.themes.map(theme => renderTheme(theme, payload.method)).join('');
      shell.dataset.ready = 'true';
    })
    .catch(error => {
      shell.innerHTML = '<p class="theme-error">Themes could not be loaded. The previous research remains in the JSON source.</p>';
      console.error(error);
    });
})();
