// Lists booth captures and returns short-lived view URLs. Requires the gallery token.
const S3 = require('./lib/s3');

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  const c = S3.cfg();
  if (!S3.configured(c)) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Uploader not configured' }) };
  if (!S3.authOK(event)) return { statusCode: 401, headers: S3.CORS, body: JSON.stringify({ error: 'Bad or missing passcode' }) };

  const params = event.queryStringParameters || {};
  const tab = params.tab === 'approved' ? 'approved/' : 'incoming/';
  try {
    const items = (await S3.listObjects(tab))
      .filter(o => !o.key.endsWith('/'))
      .sort((a, b) => (b.lastModified || '').localeCompare(a.lastModified || ''))
      .map(o => ({
        key: o.key,
        size: o.size,
        lastModified: o.lastModified,
        kind: /\.(mp4|webm|mov)$/i.test(o.key) ? 'video' : 'photo',
        url: S3.presignGet(o.key, 3600)
      }));
    return { statusCode: 200, headers: { ...S3.CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) };
  } catch (e) {
    return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
  }
};
