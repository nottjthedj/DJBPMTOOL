// Live crowd voting for the crew card <-> handler console.
// Reuses the booth's Backblaze B2. A vote is one tiny object whose KEY carries the
// option, so the handler can tally an entire room with a single list (no per-vote
// content reads). One object per member per poll = one vote each.
//
//   POST /api/vote   body { event, poll, option, member }   -> record a vote (public)
//   GET  /api/vote?event=<e>&poll=<p>                        -> { counts:{opt:n}, total }
const S3 = require('./lib/s3');

const slug = (s, n) => String(s || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, n || 40);

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Not configured' }) };
  const JSON_HDRS = { ...S3.CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };

  const q = event.queryStringParameters || {};
  const ev = slug(q.event, 40) || 'main';

  if (event.httpMethod === 'GET') {
    const poll = slug(q.poll, 40);
    if (!poll) return { statusCode: 400, headers: S3.CORS, body: JSON.stringify({ error: 'poll required' }) };
    try {
      const prefix = `votes/${ev}/${poll}/`;
      const items = await S3.listObjects(prefix);
      const counts = {};
      let total = 0;
      items.forEach(o => {
        // key: votes/<ev>/<poll>/<option>/<member>
        const rest = o.key.slice(prefix.length).split('/');
        if (rest.length >= 2 && rest[1]) { counts[rest[0]] = (counts[rest[0]] || 0) + 1; total++; }
      });
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ poll, counts, total }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  if (event.httpMethod === 'POST') {
    let body = {};
    try { body = JSON.parse(event.body || '{}'); } catch (e) {}
    const evp = slug(body.event, 40) || 'main';
    const poll = slug(body.poll, 40);
    const option = slug(body.option, 24);
    const member = slug(body.member, 40) || 'anon';
    if (!poll || !option) return { statusCode: 400, headers: S3.CORS, body: JSON.stringify({ error: 'poll and option required' }) };
    try {
      // one object per (poll, member); option lives in the key so tallies stay list-only.
      // last tap wins: remove this member's prior option(s) for this poll, then record.
      const prefix = `votes/${evp}/${poll}/`;
      const mine = (await S3.listObjects(prefix)).filter(o => o.key.endsWith('/' + member));
      await Promise.all(mine.filter(o => o.key !== `${prefix}${option}/${member}`).map(o => S3.deleteObject(o.key)));
      await S3.putJson(`${prefix}${option}/${member}`, { at: new Date().toISOString() });
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ ok: true }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  return { statusCode: 405, headers: S3.CORS, body: 'Method not allowed' };
};
