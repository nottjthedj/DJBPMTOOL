// Live show state for the crew card <-> handler console.
// Stored as small JSON objects in the same Backblaze B2 bucket (no extra service,
// no extra config — reuses the booth's keys via lib/s3). One object PER EVENT, so
// multiple rooms/cities can run simultaneously without colliding.
//
//   GET  /api/show-state?event=<key>   -> that event's { chapter, heat, missions, live, updatedAt }
//                                         Public read so every crew phone can poll it.
//   POST /api/show-state               -> write it. Requires the GALLERY_TOKEN (operator only).
//                                         Body: { event, chapter, heat:1..5, missions:[Number], live:Bool }
//
// `event` is slugified and defaults to "main" (a bare crew.html with no ?e follows "main").
const S3 = require('./lib/s3');

function eventKey(raw) {
  const slug = String(raw || 'main').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
  return 'state/' + (slug || 'main') + '.json';
}

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Not configured' }) };
  const JSON_HDRS = { ...S3.CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };

  if (event.httpMethod === 'GET') {
    const key = eventKey((event.queryStringParameters || {}).event);
    try {
      const state = (await S3.getJson(key)) || { live: false };
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify(state) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  if (event.httpMethod === 'POST') {
    if (!S3.authOK(event)) return { statusCode: 401, headers: S3.CORS, body: JSON.stringify({ error: 'Bad or missing passcode' }) };
    let body = {};
    try { body = JSON.parse(event.body || '{}'); } catch (e) {}
    const chapter = Math.max(1, parseInt(body.chapter, 10) || 1);
    const heat = Math.max(1, Math.min(5, parseInt(body.heat, 10) || 1));
    const missions = Array.isArray(body.missions)
      ? body.missions.map(n => parseInt(n, 10)).filter(n => !isNaN(n)).slice(0, 6)
      : [];
    const key = eventKey(body.event);
    // Optional live poll: { id, q, options:[{id,label}], open:Bool, winner:id|null }
    let poll = null;
    if (body.poll && typeof body.poll === 'object') {
      const p = body.poll;
      const opts = Array.isArray(p.options) ? p.options.slice(0, 8).map(o => ({
        id: String(o.id || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').slice(0, 24),
        label: String(o.label || o.id || '').slice(0, 60),
      })).filter(o => o.id) : [];
      poll = {
        id: String(p.id || '').replace(/[^a-z0-9-]+/gi, '-').slice(0, 40),
        q: String(p.q || '').slice(0, 120),
        options: opts,
        open: p.open !== false,
        winner: p.winner ? String(p.winner).toLowerCase().replace(/[^a-z0-9-]+/g, '-').slice(0, 24) : null,
      };
      if (!poll.id || !opts.length) poll = null;
    }
    const state = { event: key.slice(6, -5), chapter, heat, missions, poll, live: body.live !== false, updatedAt: new Date().toISOString() };
    try {
      await S3.putJson(key, state);
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ ok: true, state }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  return { statusCode: 405, headers: S3.CORS, body: 'Method not allowed' };
};
