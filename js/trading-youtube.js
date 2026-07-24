/* Lazy rendering for the /trading/#youtube research snapshot. */
(() => {
  'use strict';

  const panel = document.getElementById('youtube-panel');
  if (!panel) return;

  const safe = value => String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
  const signed = value => `${Number(value) >= 0 ? '+' : '−'}${Math.abs(Number(value)).toFixed(2)}`;
  const toneClass = tone => tone === 'bullish' ? 'scan-z-pos' : tone === 'bearish' ? 'scan-z-neg' : 'scan-sec';
  const toneLabel = tone => tone === 'mixed/neutral' ? 'Mixed' : `${tone.charAt(0).toUpperCase()}${tone.slice(1)}`;
  const shortDate = value => {
    const match = /^(\d{4})(\d{2})(\d{2})$/.exec(value || '');
    if (!match) return 'Date unavailable';
    return new Date(`${match[1]}-${match[2]}-${match[3]}T12:00:00Z`).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
    });
  };

  let loadPromise = null;

  function renderTickers(rows) {
    const body = rows.map(row => `
      <tr>
        <td class="scan-sym">${safe(row.ticker)}</td>
        <td class="scan-num">${Number(row.mentions).toLocaleString()}</td>
        <td class="scan-num">${row.videos}</td>
        <td class="scan-num">${row.creators}</td>
        <td class="scan-num">${row.bullish_creators}/${row.neutral_creators}/${row.bearish_creators}</td>
        <td><span class="${toneClass(row.sentiment)}">${safe(toneLabel(row.sentiment))}</span></td>
        <td class="scan-num"><span class="${row.creator_consensus_net >= 0 ? 'scan-z-pos' : 'scan-z-neg'}">${signed(row.creator_consensus_net)}</span></td>
      </tr>`).join('');
    document.getElementById('youtube-tickers-shell').innerHTML = `
      <table class="scan-table youtube-table" aria-label="YouTube ticker and asset sentiment">
        <thead><tr><th>Ticker / asset</th><th class="scan-num">Mentions</th><th class="scan-num">Videos</th><th class="scan-num">Creators</th><th class="scan-num">B/N/R</th><th>Consensus</th><th class="scan-num">Score</th></tr></thead>
        <tbody>${body}</tbody>
      </table>`;
  }

  function renderCreators(rows) {
    const body = rows.map(row => `
      <tr>
        <td>${safe(row.creator)}</td>
        <td class="scan-num">${row.videos_with_transcripts}/5</td>
        <td class="scan-num">${Number(row.mentions).toLocaleString()}</td>
        <td><span class="${toneClass(row.sentiment)}">${safe(toneLabel(row.sentiment))}</span></td>
        <td class="scan-num"><span class="${row.net >= 0 ? 'scan-z-pos' : 'scan-z-neg'}">${signed(row.net)}</span></td>
        <td class="youtube-wide-cell">${safe(row.top_tickers)}</td>
      </tr>`).join('');
    document.getElementById('youtube-creators-shell').innerHTML = `
      <table class="scan-table youtube-table" aria-label="YouTube creator sentiment summary">
        <thead><tr><th>Creator</th><th class="scan-num">Transcripts</th><th class="scan-num">Mentions</th><th>Tone</th><th class="scan-num">Score</th><th>Most mentioned</th></tr></thead>
        <tbody>${body}</tbody>
      </table>`;
  }

  function renderVideos(rows) {
    const body = rows.map(row => `
      <tr>
        <td>${safe(row.channel)}</td>
        <td class="scan-num">${safe(shortDate(row.upload_date))}</td>
        <td class="youtube-title-cell"><a href="${safe(row.url)}" rel="noopener noreferrer" target="_blank">${safe(row.title)}</a></td>
        <td><span class="${row.transcript_available ? 'scan-z-pos' : 'scan-z-neg'}">${row.transcript_available ? 'Available' : 'Unavailable'}</span></td>
      </tr>`).join('');
    document.getElementById('youtube-videos-shell').innerHTML = `
      <table class="scan-table youtube-table" aria-label="YouTube source videos">
        <thead><tr><th>Creator</th><th class="scan-num">Published</th><th>Video</th><th>Transcript</th></tr></thead>
        <tbody>${body}</tbody>
      </table>`;
  }

  function render(payload) {
    const summary = payload.summary;
    document.getElementById('youtube-takeaway').textContent = `${payload.headline}. ${payload.takeaway}`;
    document.getElementById('youtube-channels').textContent = summary.channels.toLocaleString();
    document.getElementById('youtube-videos').textContent = summary.videos_targeted.toLocaleString();
    document.getElementById('youtube-transcripts').textContent = `${summary.videos_with_transcripts}/${summary.videos_targeted}`;
    document.getElementById('youtube-mentions').textContent = summary.organic_mentions.toLocaleString();
    renderTickers(payload.tickers);
    renderCreators(payload.creators);
    renderVideos(payload.videos);
  }

  function load() {
    if (panel.dataset.loaded === 'true') return Promise.resolve();
    if (loadPromise) return loadPromise;
    panel.setAttribute('aria-busy', 'true');
    loadPromise = fetch(panel.dataset.url, { credentials: 'same-origin' })
      .then(response => {
        if (!response.ok) throw new Error(`YouTube data HTTP ${response.status}`);
        return response.json();
      })
      .then(payload => {
        render(payload);
        panel.dataset.loaded = 'true';
      })
      .catch(error => {
        console.error('Unable to load YouTube sentiment data', error);
        panel.querySelectorAll('.youtube-data-shell').forEach(shell => {
          shell.innerHTML = '<p class="bl-empty">YouTube research data failed to load. Use the JSON download below.</p>';
        });
        loadPromise = null;
      })
      .finally(() => panel.removeAttribute('aria-busy'));
    return loadPromise;
  }

  panel.addEventListener('panelactivate', load);
  if (!panel.hidden) load();
})();
