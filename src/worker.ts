// Tiny Cloudflare Worker that sits in front of the static assets and handles
// the one dynamic route the site needs right now: POST /api/subscribe.
//
// Static-assets-first routing is the default when both `main` and `assets` are
// set in wrangler.jsonc, so this handler only sees requests that don't match a
// file in dist/ (i.e., the API routes below). For everything else, control
// never reaches here.
//
// Storage: submissions are logged via console.log to Workers Observability
// (the `observability` block in wrangler.jsonc). Tail with `wrangler tail` or
// browse logs in the Cloudflare dashboard. This is intentionally rough — when
// Buttondown lands, the same handler becomes a `fetch(buttondown_api, …)` call
// and the frontend doesn't change.

interface Fetcher {
  fetch(request: Request): Promise<Response>;
}
interface Env {
  ASSETS: Fetcher;
}

const VALID_LANGS = new Set(["en", "zh", "both"]);
// Loose email check — Workers shouldn't do RFC 5322 validation; the email
// provider (Buttondown later) does the real verification on send.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function redirect(request: Request, path: string, status = 303): Response {
  return Response.redirect(new URL(path, request.url).toString(), status);
}

async function handleSubscribe(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return redirect(request, "/subscribe?error=parse");
  }

  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const langRaw = String(form.get("lang") ?? "").trim().toLowerCase();
  const lang = VALID_LANGS.has(langRaw) ? langRaw : "both";
  // Honeypot: if a bot fills this hidden field, silently accept and discard.
  const honeypot = String(form.get("website") ?? "").trim();

  if (!EMAIL_RE.test(email)) {
    return redirect(request, "/subscribe?error=email");
  }
  if (honeypot) {
    // Pretend success so bots don't probe further; nothing recorded.
    return redirect(request, "/subscribe?ok=1");
  }

  const cf = (request as Request & { cf?: { country?: string } }).cf;
  console.log(
    JSON.stringify({
      type: "subscribe",
      email,
      lang,
      ts: new Date().toISOString(),
      country: cf?.country ?? "",
      ua: request.headers.get("user-agent") ?? "",
    }),
  );

  return redirect(request, "/subscribe?ok=1");
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/subscribe") {
      return handleSubscribe(request);
    }
    // Fall through to static assets. Reached only for unmatched-asset routes
    // that aren't /api/subscribe — return whatever the assets binding does
    // (typically the 404 page if the dist build provides one, else a default).
    return env.ASSETS.fetch(request);
  },
};
