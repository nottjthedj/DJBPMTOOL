// Approve (copy to approved/) or delete a capture. Requires the gallery token.
const S3 = require('./lib/s3');

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: S3.CORS, body: 'Method not allowed' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Uploader not configured' }) };
  if (!S3.authOK(event)) return { statusCode: 401, headers: S3.CORS, body: JSON.stringify({ error: 'Bad or missing passcode' }) };

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch (e) {}
  const action = body.action;
  const key = body.key;
  if (!key || key.indexOf('..') !== -1) return { statusCode: 400, headers: S3.CORS, body: JSON.stringify({ error: 'Bad key' }) };

  try {
    if (action === 'approve') {
      // copy incoming/<path> -> approved/<path>, leaving the original intact
      const dest = key.startsWith('incoming/') ? key.replace(/^incoming\//, 'approved/') : 'approved/' + key;
      await S3.copyObject(key, dest);
      return { statusCode: 200, headers: { ...S3.CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ ok: true, approvedKey: dest }) };
    }
    if (action === 'delete') {
      await S3.deleteObject(key);
      return { statusCode: 200, headers: { ...S3.CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ ok: true }) };
    }
    return { statusCode: 400, headers: S3.CORS, body: JSON.stringify({ error: 'Unknown action' }) };
  } catch (e) {
    return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
  }
};
