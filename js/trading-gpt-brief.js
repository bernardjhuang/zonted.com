(() => {
  'use strict';

  const shell = document.querySelector('#gpt-brief-shell');
  if (!shell) return;

  const esc = value => String(value ?? '').replace(/[&<>"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  })[char]);

  const formatDate = value => {
    const date = new Date(`${value}T12:00:00Z`);
    return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  };
  const formatMarketCap = value => {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return String(value);
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(amount >= 10e9 ? 1 : 2)}B`;
    return `$${(amount / 1e6).toFixed(0)}M`;
  };

  function renderEvent(event, index) {
    const sources = event.sources.map(source => `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.label)}</a>`).join(' · ');
    const confidence = Math.round(Number(event.confidence) * 100);
    return `<details class="brief-risk-card gpt-catalyst-card" data-event-id="${esc(event.id)}" data-tier="${esc(event.tier)}" data-primary-ticker="${esc(event.primary_ticker)}">
      <summary class="gpt-card-summary">
        <span class="gpt-event-number">${index + 1}</span>
        <span class="gpt-summary-copy">
          <span class="gpt-summary-topline"><code class="brief-ticker">${esc(event.primary_ticker)}</code><strong>${esc(event.date)}</strong></span>
          <span class="gpt-plain-summary">${esc(event.plain_summary)}</span>
          <small>${esc(event.sector)} · ${esc(event.category)}</small>
        </span>
        <span class="gpt-risk-badge" data-grade="${esc(event.binary_grade.toLowerCase())}">${esc(event.binary_grade)} move risk</span>
      </summary>
      <div class="gpt-card-body">
        <div class="gpt-plain-grid" aria-label="Quick read">
          <section class="gpt-plain-outcome gpt-plain-good"><h4>Good news</h4><p>${esc(event.plain_good)}</p></section>
          <section class="gpt-plain-outcome gpt-plain-bad"><h4>Bad news</h4><p>${esc(event.plain_bad)}</p></section>
          <section class="gpt-plain-outcome gpt-plain-watch"><h4>What to watch</h4><p>${esc(event.plain_watch)}</p></section>
        </div>
        <details class="gpt-full-research">
          <summary>Full research and sources</summary>
          <div class="gpt-research-body">
            <p class="brief-para"><strong>${esc(event.primary_ticker)} snapshot:</strong> ${formatMarketCap(event.market_cap_usd)} market cap · $${Number(event.reference_price).toFixed(2)} reference · ${esc(event.binary_grade)} binary grade · source/date confidence ${confidence}%</p>
            <p class="brief-para"><strong>Exact trigger:</strong> ${esc(event.trigger)}</p>
            <p class="brief-para"><strong>Why it matters:</strong> ${esc(event.implication)}</p>
            <ul class="brief-bullets"><li><strong>White swan:</strong> ${esc(event.white_swan)}</li><li><strong>Base case:</strong> ${esc(event.base_case)}</li><li><strong>Black swan:</strong> ${esc(event.black_swan)}</li></ul>
            <p class="brief-para"><strong>Why it may be mispriced:</strong> ${esc(event.why_mispriced)}</p>
            <p class="brief-para"><strong>Expected move:</strong> ${esc(event.magnitude)}</p>
            <p class="brief-para"><strong>Research plan:</strong> ${esc(event.action)}</p>
            <p class="brief-para"><strong>What would prove this wrong:</strong> ${esc(event.invalidation)}</p>
            <p class="brief-para"><strong>Sources:</strong> ${sources}</p>
          </div>
        </details>
      </div>
    </details>`;
  }

  fetch(shell.dataset.url, { credentials: 'same-origin' })
    .then(response => {
      if (!response.ok) throw new Error(`GPT brief fetch failed: ${response.status}`);
      return response.json();
    })
    .then(data => {
      const sectorCount = new Set(data.events.map(event => event.sector)).size;
      shell.innerHTML = `
        <div class="position-head"><h2 id="gpt-brief-heading">Events that could move a stock</h2><span>${data.events.length} events · ${sectorCount} sectors · ${formatDate(data.window_start)} → ${formatDate(data.window_end)} · 6:30 AM CT cadence</span></div>
        <p class="trading-takeaway">${esc(data.summary)}</p>
        <p class="gpt-quick-read"><strong>Quick read:</strong> Open any row for the upside, downside, and next thing to watch. Full research stays folded.</p>
        <div class="brief-log gpt-brief-list" data-gpt-brief-as-of="${esc(data.as_of)}">${data.events.map(renderEvent).join('')}</div>
        <details class="trading-method"><summary>How this list was picked</summary><ul class="brief-bullets">${data.context.map(item => `<li>${esc(item)}</li>`).join('')}</ul><p>${esc(data.methodology)}</p></details>
        <p class="trading-note">Research and monitoring only. Option-implied ranges are rough market estimates, not executable prices or recommendations.</p>`;
    })
    .catch(error => {
      shell.innerHTML = `<div class="position-head"><h2>Events that could move a stock</h2></div><p class="trading-note">Brief unavailable: ${esc(error.message)}</p>`;
      console.error(error);
    });
})();
