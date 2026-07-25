(() => {
  'use strict';

  const shell = document.querySelector('#gpt-brief-shell');
  if (!shell) return;

  const esc = value => String(value ?? '').replace(/[&<>"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
  })[char]);

  const confidenceColor = value => value >= .8 ? 'var(--bl-gain)' : value >= .6 ? 'var(--bl-vwap)' : 'var(--bl-faint)';
  const formatDate = value => {
    const date = new Date(`${value}T12:00:00Z`);
    return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  };

  function renderEvent(event) {
    const tickers = event.tickers.map(symbol => `<code class="brief-ticker">${esc(symbol)}</code>`).join('');
    const sources = event.sources.map(source => `<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.label)}</a>`).join(' · ');
    const confidence = Number(event.confidence);
    return `<article class="brief-risk-card gpt-catalyst-card" data-event-id="${esc(event.id)}" data-tier="${esc(event.tier)}">
      <div class="brief-card-header"><h3 class="brief-risk-title">${esc(event.date)} · ${esc(event.title)}</h3><span class="brief-score-badge" style="background:${confidenceColor(confidence)}">${Math.round(confidence * 100)}%</span></div>
      <small class="brief-score-detail">${esc(event.tier)} · ${esc(event.category)} · ${esc(event.date_status)} · ${esc(event.horizon)}</small>
      <div class="brief-levers">${tickers}</div>
      <p class="brief-para"><strong>Implication:</strong> ${esc(event.implication)}</p>
      <p class="brief-para"><strong>Direction:</strong> ${esc(event.direction)}</p>
      <p class="brief-para"><strong>Expected move:</strong> ${esc(event.magnitude)}</p>
      <p class="brief-para"><strong>Action:</strong> ${esc(event.action)}</p>
      <p class="brief-para"><strong>What would prove this wrong:</strong> ${esc(event.invalidation)}</p>
      <p class="brief-para"><strong>Watch next:</strong> ${esc(event.watch)}</p>
      <p class="brief-para"><strong>Sources:</strong> ${sources}</p>
    </article>`;
  }

  fetch(shell.dataset.url, { credentials: 'same-origin' })
    .then(response => {
      if (!response.ok) throw new Error(`GPT brief fetch failed: ${response.status}`);
      return response.json();
    })
    .then(data => {
      shell.innerHTML = `
        <div class="position-head"><h2 id="gpt-brief-heading">GPT Market Catalyst Brief</h2><span>${data.events.length} material events · ${formatDate(data.window_start)} → ${formatDate(data.window_end)} · 6:30 AM CT cadence</span></div>
        <p class="trading-takeaway">${esc(data.summary)}</p>
        <p class="scan-intro"><strong>Market-wide focus:</strong> ${data.universe.map(esc).join(' · ')}. Events are ranked by index, sector, and cross-company impact—not by current holdings.</p>
        <div class="brief-log" data-gpt-brief-as-of="${esc(data.as_of)}">${data.events.map(renderEvent).join('')}</div>
        <details class="trading-method"><summary>Context and method</summary><ul class="brief-bullets">${data.context.map(item => `<li>${esc(item)}</li>`).join('')}</ul><p>${esc(data.methodology)}</p></details>
        <p class="trading-note">Research and monitoring only. Option-implied ranges are indicative marks, not executable fills or recommendations.</p>`;
    })
    .catch(error => {
      shell.innerHTML = `<div class="position-head"><h2>GPT Event Catalyst Brief</h2></div><p class="trading-note">Brief unavailable: ${esc(error.message)}</p>`;
      console.error(error);
    });
})();
