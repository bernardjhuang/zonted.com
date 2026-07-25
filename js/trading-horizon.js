(() => {
  'use strict';

  const shell = document.querySelector('#horizon-shell');
  if (!shell) return;

  const esc = value => String(value ?? '').replace(/[&<>"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  })[char]);

  const stageTone = stage => ({
    early: 'var(--bl-gain)',
    building: 'var(--bl-vwap)',
    crowded: 'var(--bl-loss)'
  })[stage] || 'var(--bl-faint)';

  const priorityLabel = priority => String(priority || 'P2');

  const formatAsOf = value => {
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return value;
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZone: 'America/Chicago',
      timeZoneName: 'short'
    });
  };

  const tickers = (primary = [], secondary = []) => {
    const primaryHtml = primary.map(symbol => `<code class="brief-ticker">${esc(symbol)}</code>`).join('');
    const secondaryHtml = secondary.length
      ? ` <span class="horizon-secondary">read-through ${secondary.map(symbol => `<code class="brief-ticker">${esc(symbol)}</code>`).join(' ')}</span>`
      : '';
    return primaryHtml + secondaryHtml;
  };

  function renderThesis(thesis) {
    const sources = (thesis.sources || []).map(source => (
      `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.label)}</a>`
    )).join(' · ');
    const chain = (thesis.catalyst_chain || []).map((step, index) => (
      `<li><span class="horizon-step">${index + 1}</span>${esc(step)}</li>`
    )).join('');
    const watch = (thesis.watch || []).map(item => `<li>${esc(item)}</li>`).join('');
    const confidence = Number(thesis.confidence);
    return `<article class="brief-risk-card horizon-thesis-card" data-thesis-id="${esc(thesis.id)}" data-agency="${esc(thesis.agency)}" data-priority="${esc(thesis.priority)}" data-stage="${esc(thesis.narrative_stage)}">
      <div class="brief-card-header">
        <h3 class="brief-risk-title">${esc(thesis.title)}</h3>
        <span class="brief-score-badge" style="background:${stageTone(thesis.narrative_stage)}">${esc(thesis.narrative_stage)} · ${priorityLabel(thesis.priority)}</span>
      </div>
      <small class="brief-score-detail">${esc(thesis.agency)} · ${esc(thesis.niche)} · next: ${esc(thesis.next_decision)} · ~${esc(thesis.weeks_remaining_estimate)} weeks · source ${Math.round(confidence * 100)}%</small>
      <div class="brief-levers">${tickers(thesis.primary_tickers, thesis.secondary_tickers)}</div>
      <p class="brief-para"><strong>What happened:</strong> ${esc(thesis.what_happened)}</p>
      <p class="brief-para"><strong>Transmission:</strong> ${esc(thesis.transmission)}</p>
      <p class="brief-para"><strong>Company exposure:</strong> ${esc(thesis.company_exposure)}</p>
      <p class="brief-para"><strong>Asymmetry:</strong> ${esc(thesis.asymmetry)}</p>
      <div class="horizon-chain"><h4>Catalyst chain</h4><ol class="horizon-chain-list">${chain}</ol></div>
      <p class="brief-para"><strong>Second-order:</strong> ${esc(thesis.second_order)}</p>
      <p class="brief-para"><strong>Invalidation:</strong> ${esc(thesis.invalidation)}</p>
      <p class="brief-para"><strong>Watch next:</strong></p>
      <ul class="brief-bullets">${watch}</ul>
      <p class="brief-para"><strong>Sources:</strong> ${sources}</p>
    </article>`;
  }

  fetch(shell.dataset.url, { credentials: 'same-origin' })
    .then(response => {
      if (!response.ok) throw new Error(`Horizon fetch failed: ${response.status}`);
      return response.json();
    })
    .then(data => {
      const agencies = new Set((data.theses || []).map(thesis => thesis.agency));
      const earlyCount = (data.theses || []).filter(thesis => thesis.narrative_stage === 'early').length;
      shell.innerHTML = `
        <div class="position-head">
          <h2 id="horizon-heading">Horizon Catalyst Research</h2>
          <span>${data.theses.length} theses · ${agencies.size} agencies · ${earlyCount} early · 6:30 AM CT trading days</span>
        </div>
        <p class="trading-takeaway">${esc(data.summary)}</p>
        <p class="scan-intro"><strong>Agencies scanned:</strong> ${(data.agencies_scanned || []).map(esc).join(' · ')}. Prefer announcement-day asymmetry over resolution-day chase. As of ${esc(formatAsOf(data.as_of))}.</p>
        <div class="brief-log" data-horizon-as-of="${esc(data.as_of)}">${data.theses.map(renderThesis).join('')}</div>
        <details class="trading-method"><summary>Context and method</summary><ul class="brief-bullets">${(data.context || []).map(item => `<li>${esc(item)}</li>`).join('')}</ul><p>${esc(data.methodology)}</p></details>
        <p class="trading-note">Research and monitoring only. Not trade recommendations. Confidence scores source quality, not expected return.</p>`;
    })
    .catch(error => {
      shell.innerHTML = `<div class="position-head"><h2>Horizon Catalyst Research</h2></div><p class="trading-note">Horizon unavailable: ${esc(error.message)}</p>`;
      console.error(error);
    });
})();
