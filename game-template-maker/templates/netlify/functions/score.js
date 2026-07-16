// Points + leaderboard for the crew, built on the live votes. Reuses the booth's
// Backblaze B2 — no new service. Points are earned from polls: everyone who votes
// gets participation points; whoever backed the winning option gets the win bonus.
//
//   POST /api/score  body { event, poll, winner }   -> award points for a closed poll (operator token)
//   GET  /api/score?event=<e>                        -> leaderboard { board:[{member,points}], members }
//
// A points entry is a single empty object whose KEY holds the value:
//   points/<event>/<poll>/<member>__<pts>
// so the whole leaderboard tallies with one list call — no per-entry reads.
const S3 = require('./lib/s3');

const slug = (s, n) => String(s || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, n || 40);
const WIN_PTS = 10, PART_PTS = 3;

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Not configured' }) };
  const JSON_HDRS = { ...S3.CORS, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  const q = event.queryStringParameters || {};

  if (event.httpMethod === 'GET') {
    const ev = slug(q.event, 40) || 'main';
    try {
      const prefix = `points/${ev}/`;
      const items = await S3.listObjects(prefix);
      const totals = {};
      items.forEach(o => {
        // key: points/<ev>/<poll>/<member>__<pts>
        const rest = o.key.slice(prefix.length).split('/');
        if (rest.length >= 2) {
          const mp = rest[1].split('__');
          const member = mp[0], pts = parseInt(mp[1], 10) || 0;
          if (member) totals[member] = (totals[member] || 0) + pts;
        }
      });
      const board = Object.keys(totals).map(m => ({ member: m, points: totals[m] }))
        .sort((a, b) => b.points - a.points).slice(0, 50);
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ board, members: Object.keys(totals).length }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  if (event.httpMethod === 'POST') {
    if (!S3.authOK(event)) return { statusCode: 401, headers: S3.CORS, body: JSON.stringify({ error: 'Bad or missing passcode' }) };
    let body = {};
    try { body = JSON.parse(event.body || '{}'); } catch (e) {}
    const ev = slug(body.event, 40) || 'main';
    const poll = slug(body.poll, 40);
    const winner = slug(body.winner, 24);
    if (!poll) return { statusCode: 400, headers: S3.CORS, body: JSON.stringify({ error: 'poll required' }) };
    try {
      const votePrefix = `votes/${ev}/${poll}/`;
      const votes = await S3.listObjects(votePrefix);
      // recompute cleanly: clear any prior award for this poll, then re-award
      const pointPrefix = `points/${ev}/${poll}/`;
      const prior = await S3.listObjects(pointPrefix);
      await Promise.all(prior.map(o => S3.deleteObject(o.key)));
      let awarded = 0;
      await Promise.all(votes.map(o => {
        const rest = o.key.slice(votePrefix.length).split('/'); // [option, member]
        if (rest.length < 2 || !rest[1]) return Promise.resolve();
        const pts = rest[0] === winner ? WIN_PTS : PART_PTS;
        awarded++;
        return S3.putJson(`points/${ev}/${poll}/${rest[1]}__${pts}`, {});
      }));
      return { statusCode: 200, headers: JSON_HDRS, body: JSON.stringify({ ok: true, awarded }) };
    } catch (e) {
      return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
    }
  }

  return { statusCode: 405, headers: S3.CORS, body: 'Method not allowed' };
};
