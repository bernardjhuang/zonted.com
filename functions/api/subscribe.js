// Cloudflare Pages Function — POST /api/subscribe
// Accepts { email } JSON, adds the contact to the Resend audience.
//
// Env vars (configure in Cloudflare Pages dashboard → Settings → Environment variables → Production):
//   RESEND_API_KEY       — required (Bearer token). Do NOT commit.
//   RESEND_AUDIENCE_ID   — optional. Falls back to the "General" audience id below.

const FALLBACK_AUDIENCE_ID = '3282e3a7-f68b-45fb-99fa-4f203f203892';
// Email regex — requires a dotted TLD of ≥2 chars. Rejects `a@b.c` style
// addresses that the previous looser regex accepted (Resend would reject
// them downstream and we'd return an ugly 502). Still accepts `name+tag@host`.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;

// Browser origins permitted to POST here. Server-side curl with no Origin
// header is also allowed (Origin only exists on browser-initiated requests),
// so Bernard's scripts and Resend's own dashboard probes are unaffected.
const ALLOWED_ORIGINS = new Set([
  'https://zonted.com',
  'https://www.zonted.com',
]);

function json(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  });
}

function corsHeaders(origin) {
  // Echo only allowed origins; never wildcard for an endpoint that mutates state.
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    return {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
      'Vary': 'Origin',
    };
  }
  return {};
}

// CORS preflight. Browsers send this before any cross-origin JSON POST.
export async function onRequestOptions({ request }) {
  const origin = request.headers.get('Origin');
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }
  // Unknown origin → no CORS allowed, no preflight success.
  return new Response(null, { status: 403 });
}

export async function onRequestPost(context) {
  const { request, env, waitUntil } = context;
  const origin = request.headers.get('Origin');

  // Origin gate: if a browser sent an Origin header, it must be in the
  // allowlist. Server-side / cron calls with no Origin header pass through.
  // This closes the CSRF / audience-flood vector from 3rd-party pages.
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return json({ error: 'forbidden' }, 403);
  }

  if (!env.RESEND_API_KEY) {
    return json({ error: 'subscribe service not configured' }, 503, corsHeaders(origin));
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: 'invalid payload' }, 400, corsHeaders(origin));
  }

  // Type-guard the email field before trimming. Without this, payloads like
  // {"email": 123} or {"email": ["a"]} throw TypeError on .trim() and the
  // Worker returns Cloudflare's generic 500 page instead of our JSON.
  const raw = payload && payload.email;
  if (typeof raw !== 'string') {
    return json({ error: 'invalid email' }, 400, corsHeaders(origin));
  }
  const email = raw.trim().toLowerCase();
  if (!email || email.length > 254 || !EMAIL_RE.test(email)) {
    return json({ error: 'invalid email' }, 400, corsHeaders(origin));
  }

  const audienceId = env.RESEND_AUDIENCE_ID || FALLBACK_AUDIENCE_ID;

  try {
    // 1. Add the contact to the audience.
    const resp = await fetch(
      `https://api.resend.com/audiences/${audienceId}/contacts`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${env.RESEND_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, unsubscribed: false }),
      },
    );

    if (!resp.ok) {
      const text = await resp.text();
      console.error('Resend contacts non-2xx:', resp.status, text);
      return json({ error: 'subscribe failed' }, 502, corsHeaders(origin));
    }

    // 2. Fire a short plain-text welcome email — only on actual first-time
    //    subscribes. Resend's add-contact endpoint is idempotent: re-POSTing
    //    an existing email returns 200 with the same contact_id. Detect that
    //    by comparing the contact's created_at to "now" (within 30s = fresh
    //    add). Skip the welcome for re-subscribers so they don't get
    //    duplicate welcomes if they double-click or resubscribe later.
    let isFresh = true;
    try {
      const data = await resp.json();
      const createdAt = data?.data?.created_at || data?.created_at;
      if (createdAt) {
        const created = Date.parse(createdAt);
        if (!isNaN(created) && (Date.now() - created) > 30_000) {
          isFresh = false;
        }
      }
    } catch {
      // If the response shape changes, default to sending — better to
      // occasionally double-welcome than to silently drop the welcome path.
    }

    if (isFresh) {
      const welcomeWork = sendWelcomeEmail(env.RESEND_API_KEY, email, env.SLACK_WELCOME_BCC).catch((err) => {
        console.error('Welcome email failed (non-fatal):', err);
      });
      if (typeof waitUntil === 'function') {
        waitUntil(welcomeWork);
      } else if (context.waitUntil) {
        context.waitUntil(welcomeWork);
      }
    }

    return json({ ok: true }, 200, corsHeaders(origin));
  } catch (err) {
    console.error('Subscribe fetch threw:', err);
    return json({ error: 'network error' }, 502, corsHeaders(origin));
  }
}

async function sendWelcomeEmail(apiKey, to, slackBcc) {
  // BCC to the Slack email-into-channel address (env: SLACK_WELCOME_BCC) so
  // each welcome becomes a Slack post in #zonted. Cheaper than a webhook.
  // When the env var is unset, the email goes out without the BCC.
  const body = {
    from: 'Bernard Huang <bernard@zonted.com>',
    to: [to],
    subject: "You're subscribed to the zonted newsletter",
    text:
      "Thanks for subscribing to Zonted. I'll email you when the next post ships — " +
      "one email per post, no drips, no welcome series.\n\n" +
      "— Bernard",
  };
  // Only attach BCC if env var is a real-looking string (defends against
  // an empty string or non-string sneaking through).
  if (typeof slackBcc === 'string' && slackBcc.includes('@')) {
    body.bcc = [slackBcc];
  }
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Resend emails non-2xx: ${resp.status} ${text.slice(0, 200)}`);
  }
}

// 405 for non-POST, non-OPTIONS methods.
export async function onRequest({ request }) {
  // onRequestPost + onRequestOptions handle their own methods; this is the
  // catch-all for GET/PUT/DELETE/PATCH/HEAD/etc.
  return new Response('Method Not Allowed', {
    status: 405,
    headers: { 'Allow': 'POST, OPTIONS' },
  });
}
