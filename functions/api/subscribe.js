// Cloudflare Pages Function — POST /api/subscribe
// Accepts { email } JSON, adds the contact to the Resend audience.
//
// Env vars (configure in Cloudflare Pages dashboard → Settings → Environment variables → Production):
//   RESEND_API_KEY       — required (Bearer token). Do NOT commit.
//   RESEND_AUDIENCE_ID   — optional. Falls back to the "General" audience id below.

const FALLBACK_AUDIENCE_ID = '3282e3a7-f68b-45fb-99fa-4f203f203892';
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function onRequestPost(context) {
  const { request, env, waitUntil } = context;
  if (!env.RESEND_API_KEY) {
    // Misconfigured deploy — secret missing.
    return json({ error: 'subscribe service not configured' }, 503);
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: 'invalid payload' }, 400);
  }

  const email = (payload?.email || '').trim().toLowerCase();
  if (!email || email.length > 254 || !EMAIL_RE.test(email)) {
    return json({ error: 'invalid email' }, 400);
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
      return json({ error: 'subscribe failed' }, 502);
    }

    // 2. Fire a short plain-text welcome email. Best-effort — failures here
    //    should NOT fail the subscription itself (the contact is already in
    //    the audience). waitUntil() keeps the promise alive past the response;
    //    without it Cloudflare Workers kill in-flight fetches on response.
    const welcomeWork = sendWelcomeEmail(env.RESEND_API_KEY, email).catch((err) => {
      console.error('Welcome email failed (non-fatal):', err);
    });
    if (typeof waitUntil === 'function') {
      waitUntil(welcomeWork);
    } else if (context.waitUntil) {
      context.waitUntil(welcomeWork);
    }

    return json({ ok: true });
  } catch (err) {
    console.error('Subscribe fetch threw:', err);
    return json({ error: 'network error' }, 502);
  }
}

async function sendWelcomeEmail(apiKey, to) {
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: 'Bernard Huang <bernard@zonted.com>',
      to: [to],
      subject: "You're in.",
      text:
        "Thanks for subscribing to Zonted. I'll email you when the next post ships — " +
        "one email per post, no drips, no welcome series.\n\n" +
        "— Bernard",
    }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Resend emails non-2xx: ${resp.status} ${text.slice(0, 200)}`);
  }
}

// Block other methods explicitly.
export async function onRequest({ request }) {
  if (request.method === 'POST') {
    // Should be handled by onRequestPost above; this is just a defensive fallback.
    return json({ error: 'unexpected route' }, 500);
  }
  return new Response('Method Not Allowed', {
    status: 405,
    headers: { 'Allow': 'POST' },
  });
}
