#!/usr/bin/env node
/*
 * Fetch GA4 portfolio metrics for zonted.com/metrics/.
 * Uses the existing GA4 service account config from the OpenClaw GA4 skill.
 */
const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const GA4_SKILL_DIR = '/Users/psy/.openclaw/workspace/skills/ga4-analytics/scripts';
const skillRequire = createRequire(path.join(GA4_SKILL_DIR, 'package.json'));
const dotenv = skillRequire('dotenv');
const { BetaAnalyticsDataClient } = skillRequire('@google-analytics/data');
const { google } = skillRequire('googleapis');

dotenv.config({ path: path.join(GA4_SKILL_DIR, '..', '.env') });

const PROPERTIES = [
  { key: 'tabiji', name: 'Tabiji', domain: 'tabiji.ai', id: '524076952', color: '#2a7a2a' },
  { key: 'veracityapi', name: 'VeracityAPI', domain: 'veracityapi.com', id: '537020430', color: '#336699' },
  { key: 'palmaura', name: 'Palmaura', domain: 'palmaura.app', id: '538073800', color: '#8a5a20' },
  { key: 'zonted', name: 'Zonted', domain: 'zonted.com', id: '532496138', color: '#6f4aa8' },
];

function fmtDate(d) {
  return d.toISOString().slice(0, 10).replace(/-/g, '');
}

function labelFromYmd(s) {
  const d = new Date(`${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}T12:00:00`);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function dashedYmd(s) {
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
}

function weightedPosition(rows) {
  const impressions = rows.reduce((sum, row) => sum + row.impressions, 0);
  if (!impressions) return 0;
  return rows.reduce((sum, row) => sum + row.position * row.impressions, 0) / impressions;
}

async function run() {
  const keyPath = path.join(process.env.HOME || '/Users/psy', '.secrets', 'ga4-private-key.pem');
  const key = fs.existsSync(keyPath)
    ? fs.readFileSync(keyPath, 'utf8').trim()
    : (process.env.GA4_PRIVATE_KEY || '').replace(/\\n/g, '\n');

  if (!process.env.GA4_CLIENT_EMAIL || !key) {
    throw new Error('Missing GA4_CLIENT_EMAIL or private key');
  }

  const client = new BetaAnalyticsDataClient({
    credentials: { client_email: process.env.GA4_CLIENT_EMAIL, private_key: key },
  });
  const auth = new google.auth.JWT({
    email: process.env.GA4_CLIENT_EMAIL,
    key,
    scopes: ['https://www.googleapis.com/auth/webmasters.readonly'],
  });
  const searchConsole = google.searchconsole({ version: 'v1', auth });

  const end = new Date();
  end.setHours(12, 0, 0, 0);
  const start = new Date(end);
  start.setDate(start.getDate() - 89);
  const ymds = [];
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) ymds.push(fmtDate(d));

  // Search Console data usually lags by ~48h. Ending two days ago avoids an
  // artificial cliff to zero at the right edge of the chart.
  const gscEnd = new Date(end);
  gscEnd.setDate(gscEnd.getDate() - 2);
  const gscStart = new Date(gscEnd);
  gscStart.setDate(gscStart.getDate() - 89);
  const gscYmds = [];
  for (let d = new Date(gscStart); d <= gscEnd; d.setDate(d.getDate() + 1)) gscYmds.push(fmtDate(d));

  const output = {
    updatedIso: new Date().toISOString(),
    updatedLabel: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
    rangeLabel: 'Last 90 days',
    labels: ymds.map(labelFromYmd),
    gscLabels: gscYmds.map(labelFromYmd),
    properties: [],
    searchConsoleProperties: [],
  };

  for (const property of PROPERTIES) {
    const [daily] = await client.runReport({
      property: `properties/${property.id}`,
      dateRanges: [{ startDate: '89daysAgo', endDate: 'today' }],
      dimensions: [{ name: 'date' }],
      metrics: [{ name: 'sessions' }],
      orderBys: [{ dimension: { dimensionName: 'date' } }],
    });

    const byDate = Object.fromEntries(ymds.map((d) => [d, 0]));
    for (const row of daily.rows || []) {
      byDate[row.dimensionValues[0].value] = Number(row.metricValues[0].value || 0);
    }

    const [aggregate] = await client.runReport({
      property: `properties/${property.id}`,
      dateRanges: [{ startDate: '89daysAgo', endDate: 'today' }],
      metrics: [
        { name: 'sessions' },
        { name: 'activeUsers' },
        { name: 'screenPageViews' },
        { name: 'averageSessionDuration' },
        { name: 'engagementRate' },
      ],
    });
    const totals = aggregate.rows?.[0]?.metricValues?.map((v) => Number(v.value || 0)) || [0, 0, 0, 0, 0];

    const [sources] = await client.runReport({
      property: `properties/${property.id}`,
      dateRanges: [{ startDate: '89daysAgo', endDate: 'today' }],
      dimensions: [{ name: 'sessionSourceMedium' }],
      metrics: [{ name: 'sessions' }],
      orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
      limit: 5,
    });

    output.properties.push({
      ...property,
      totals: {
        sessions: totals[0],
        users: totals[1],
        views: totals[2],
        avgDuration: totals[3],
        engagementRate: totals[4],
      },
      series: ymds.map((d) => byDate[d]),
      sources: (sources.rows || []).map((row) => ({
        sourceMedium: row.dimensionValues[0].value || '(not set)',
        sessions: Number(row.metricValues[0].value || 0),
      })),
    });

    const startDate = dashedYmd(gscYmds[0]);
    const endDate = dashedYmd(gscYmds[gscYmds.length - 1]);
    const siteUrl = `sc-domain:${property.domain}`;

    const dailySc = await searchConsole.searchanalytics.query({
      siteUrl,
      requestBody: {
        startDate,
        endDate,
        dimensions: ['date'],
        rowLimit: 250,
      },
    });
    const scByDate = Object.fromEntries(gscYmds.map((d) => [dashedYmd(d), { clicks: 0, impressions: 0, ctr: 0, position: 0 }]));
    for (const row of dailySc.data.rows || []) {
      const date = row.keys?.[0];
      if (!date) continue;
      scByDate[date] = {
        clicks: Number(row.clicks || 0),
        impressions: Number(row.impressions || 0),
        ctr: Number(row.ctr || 0),
        position: Number(row.position || 0),
      };
    }
    const scRows = Object.values(scByDate);
    const scTotals = {
      clicks: scRows.reduce((sum, row) => sum + row.clicks, 0),
      impressions: scRows.reduce((sum, row) => sum + row.impressions, 0),
      ctr: 0,
      position: weightedPosition(scRows),
    };
    scTotals.ctr = scTotals.impressions ? scTotals.clicks / scTotals.impressions : 0;

    const topQueries = await searchConsole.searchanalytics.query({
      siteUrl,
      requestBody: {
        startDate,
        endDate,
        dimensions: ['query'],
        rowLimit: 5,
      },
    });
    const topPages = await searchConsole.searchanalytics.query({
      siteUrl,
      requestBody: {
        startDate,
        endDate,
        dimensions: ['page'],
        rowLimit: 5,
      },
    });

    output.searchConsoleProperties.push({
      key: property.key,
      name: property.name,
      domain: property.domain,
      siteUrl,
      color: property.color,
      totals: scTotals,
      clicks: gscYmds.map((d) => scByDate[dashedYmd(d)]?.clicks || 0),
      impressions: gscYmds.map((d) => scByDate[dashedYmd(d)]?.impressions || 0),
      topQueries: (topQueries.data.rows || []).map((row) => ({
        query: row.keys?.[0] || '(not set)',
        clicks: Number(row.clicks || 0),
        impressions: Number(row.impressions || 0),
        ctr: Number(row.ctr || 0),
        position: Number(row.position || 0),
      })),
      topPages: (topPages.data.rows || []).map((row) => ({
        page: row.keys?.[0] || '',
        clicks: Number(row.clicks || 0),
        impressions: Number(row.impressions || 0),
        ctr: Number(row.ctr || 0),
        position: Number(row.position || 0),
      })),
    });
  }

  output.properties.sort((a, b) => b.totals.sessions - a.totals.sessions);
  output.searchConsoleProperties.sort((a, b) => b.totals.clicks - a.totals.clicks || b.totals.impressions - a.totals.impressions);
  process.stdout.write(JSON.stringify(output, null, 2));
}

run().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
