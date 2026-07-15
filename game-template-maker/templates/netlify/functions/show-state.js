// Live show state for the crew card <-> handler console.
// Stored as a single small JSON object in the same Backblaze B2 bucket (no extra
// service, no extra config — reuses the booth's keys via lib/s3).
//
//   GET  /api/show-state           -> current { chapter, heat, missions, live, updatedAt }
//                                     Public read so every crew phone can poll it.
//   POST /api/show-state           -> write it. Requires the GALLERY_TOKEN (operator only).
//                                     Body: { chapter:Number, heat:1..5, missions:[Number], live:Bool }
const S3 = require('./lib/s3');

const STATE_KEY = 'state/live.json';

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Not configured' }) };
  const JSON_HDRS = { ...S3.CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };

  if (event.httpMethod === 'GET') {
    try {
      const state = (await S3.getJson(STATE_KEY)) || { live: false };
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
    const state = { chapter, heat, missions, live: body.live !== false, updatedAt: new Date().toISOString() };
    try {
      await S3.putJson(STATE_KEY, state);
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ ok: true, state }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  return { statusCode: 405, headers: S3.CORS, body: 'Method not allowed' };
};
