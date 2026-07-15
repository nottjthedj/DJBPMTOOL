// {{brand.name}} — upload signer
// Issues a short-lived, presigned S3 PUT URL for the Backblaze B2 "inbox" bucket.
// The browser NEVER sees the secret key — it only gets a one-time URL to PUT one file.
// Zero npm dependencies (uses Node's built-in crypto) so it deploys with a plain drag-and-drop.
//
// Required Netlify environment variables (Site settings > Environment variables):
//   B2_KEY_ID     — Backblaze application keyID           (the "keyID")
//   B2_APP_KEY    — Backblaze applicationKey (the secret)  (the "applicationKey")
//   B2_BUCKET     — bucket name, e.g. {{web.storagePrefix}}-booth-inbox
//   B2_REGION     — from the bucket's S3 endpoint, e.g. us-west-004
//   B2_ENDPOINT   — (optional) full host; defaults to s3.<region>.backblazeb2.com

const crypto = require('crypto');

const hmac = (key, str) => crypto.createHmac('sha256', key).update(str).digest();
const sha256hex = (str) => crypto.createHash('sha256').update(str).digest('hex');
const enc = (s) => encodeURIComponent(s).replace(/[!'()*]/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase());
const encKey = (k) => k.split('/').map(enc).join('/');
const slug = (s, n) => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, n || 40);

exports.handler = async (event) => {
  const CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS'
  };
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: CORS, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: CORS, body: 'Method not allowed' };

  const keyId = process.env.B2_KEY_ID;
  const appKey = process.env.B2_APP_KEY;
  const bucket = process.env.B2_BUCKET;
  const region = process.env.B2_REGION;
  const host = process.env.B2_ENDPOINT || (region ? `s3.${region}.backblazeb2.com` : '');
  if (!keyId || !appKey || !bucket || !region) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'Uploader not configured' }) };
  }

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch (e) {}
  const kind = body.kind === 'video' ? 'video' : 'photo';
  const ext = ((body.ext || (kind === 'video' ? 'mp4' : 'jpg')) + '').replace(/[^a-z0-9]/gi, '').toLowerCase() || 'bin';
  const venue = slug(body.venue) || 'event';
  const contentType = body.contentType || (kind === 'video' ? 'video/mp4' : 'image/jpeg');

  const now = new Date();
  const p2 = (n) => String(n).padStart(2, '0');
  const datestamp = `${now.getUTCFullYear()}${p2(now.getUTCMonth() + 1)}${p2(now.getUTCDate())}`;
  const amzdate = `${datestamp}T${p2(now.getUTCHours())}${p2(now.getUTCMinutes())}${p2(now.getUTCSeconds())}Z`;
  const rand = crypto.randomBytes(6).toString('hex');
  // Folder per day + venue so your NAS stays organized: incoming/2026-07-12_the-vault/photo_...jpg
  const key = `incoming/${datestamp.slice(0,4)}-${datestamp.slice(4,6)}-${datestamp.slice(6,8)}_${venue}/${kind}_${amzdate}_${rand}.${ext}`;

  const service = 's3';
  const algorithm = 'AWS4-HMAC-SHA256';
  const expires = '300'; // 5 minutes
  const signedHeaders = 'host';
  const credentialScope = `${datestamp}/${region}/${service}/aws4_request`;
  const canonicalUri = `/${bucket}/${encKey(key)}`; // path-style addressing

  const q = {
    'X-Amz-Algorithm': algorithm,
    'X-Amz-Credential': `${keyId}/${credentialScope}`,
    'X-Amz-Date': amzdate,
    'X-Amz-Expires': expires,
    'X-Amz-SignedHeaders': signedHeaders
  };
  const canonicalQuery = Object.keys(q).sort().map(k => `${enc(k)}=${enc(q[k])}`).join('&');
  const canonicalRequest = ['PUT', canonicalUri, canonicalQuery, `host:${host}\n`, signedHeaders, 'UNSIGNED-PAYLOAD'].join('\n');
  const stringToSign = [algorithm, amzdate, credentialScope, sha256hex(canonicalRequest)].join('\n');

  const kDate = hmac('AWS4' + appKey, datestamp);
  const kRegion = hmac(kDate, region);
  const kService = hmac(kRegion, service);
  const kSigning = hmac(kService, 'aws4_request');
  const signature = crypto.createHmac('sha256', kSigning).update(stringToSign).digest('hex');

  const uploadUrl = `https://${host}${canonicalUri}?${canonicalQuery}&X-Amz-Signature=${signature}`;
  return {
    statusCode: 200,
    headers: { ...CORS, 'Content-Type': 'application/json' },
    body: JSON.stringify({ uploadUrl, key, contentType, expiresIn: 300 })
  };
};
