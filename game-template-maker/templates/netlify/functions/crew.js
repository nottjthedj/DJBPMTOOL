// Crew presence + night stats for the operator dashboard. Reuses the booth's B2.
//
//   POST /api/crew   body { event, member }   -> mark a made member present (public)
//   GET  /api/crew?event=<e>                   -> { made, polls, votes } for that event
//
// One empty object per member (crew/<event>/<member>) = the made-member count via a
// single list. Poll/vote totals come from one list of the votes/ tree.
const S3 = require('./lib/s3');

const slug = (s, n) => String(s || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, n || 40);

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Not configured' }) };
  const JSON_HDRS = { ...S3.CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  const q = event.queryStringParameters || {};

  if (event.httpMethod === 'POST') {
    let body = {};
    try { body = JSON.parse(event.body || '{}'); } catch (e) {}
    const ev = slug(body.event, 40) || 'main';
    const member = slug(body.member, 40);
    if (!member) return { statusCode: 400, headers: S3.CORS, body: JSON.stringify({ error: 'member required' }) };
    try {
      await S3.putJson(`crew/${ev}/${member}`, { at: new Date().toISOString() });
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ ok: true }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  if (event.httpMethod === 'GET') {
    const ev = slug(q.event, 40) || 'main';
    try {
      const crew = await S3.listObjects(`crew/${ev}/`);
      const made = crew.filter(o => !o.key.endsWith('/')).length;
      const votePrefix = `votes/${ev}/`;
      const voteObjs = await S3.listObjects(votePrefix);
      const polls = {};
      let votes = 0;
      voteObjs.forEach(o => {
        const rest = o.key.slice(votePrefix.length).split('/'); // [poll, option, member]
        if (rest.length >= 3 && rest[2]) { polls[rest[0]] = 1; votes++; }
      });
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ made, polls: Object.keys(polls).length, votes }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  return { statusCode: 405, headers: S3.CORS, body: 'Method not allowed' };
};
