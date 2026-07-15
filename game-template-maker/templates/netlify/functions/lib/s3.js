// Shared Backblaze B2 (S3-compatible) helpers for the gallery functions.
// Full SigV4 request signing + presigned GET, dependency-free (Node crypto only).
// Files under lib/ are NOT treated as their own Netlify functions.

const crypto = require('crypto');

const hmac = (key, str) => crypto.createHmac('sha256', key).update(str).digest();
const sha256hex = (str) => crypto.createHash('sha256').update(str).digest('hex');
const enc = (s) => encodeURIComponent(s).replace(/[!'()*]/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase());
const encKey = (k) => k.split('/').map(enc).join('/');

function cfg() {
  const region = process.env.B2_REGION;
  return {
    keyId: process.env.B2_KEY_ID,
    appKey: process.env.B2_APP_KEY,
    bucket: process.env.B2_BUCKET,
    region,
    host: process.env.B2_ENDPOINT || (region ? `s3.${region}.backblazeb2.com` : ''),
    galleryToken: process.env.GALLERY_TOKEN || ''
  };
}
function configured(c) { return c.keyId && c.appKey && c.bucket && c.region && c.host; }

function stamps() {
  const now = new Date();
  const p2 = n => String(n).padStart(2, '0');
  const datestamp = `${now.getUTCFullYear()}${p2(now.getUTCMonth() + 1)}${p2(now.getUTCDate())}`;
  const amzdate = `${datestamp}T${p2(now.getUTCHours())}${p2(now.getUTCMinutes())}${p2(now.getUTCSeconds())}Z`;
  return { datestamp, amzdate };
}
function signingKey(appKey, datestamp, region) {
  return hmac(hmac(hmac(hmac('AWS4' + appKey, datestamp), region), 's3'), 'aws4_request');
}

// Presigned GET URL for viewing an object in an <img>/<video> tag.
function presignGet(key, expires) {
  const c = cfg();
  const { datestamp, amzdate } = stamps();
  const credentialScope = `${datestamp}/${c.region}/s3/aws4_request`;
  const canonicalUri = `/${c.bucket}/${encKey(key)}`;
  const q = {
    'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
    'X-Amz-Credential': `${c.keyId}/${credentialScope}`,
    'X-Amz-Date': amzdate,
    'X-Amz-Expires': String(expires || 3600),
    'X-Amz-SignedHeaders': 'host'
  };
  const canonicalQuery = Object.keys(q).sort().map(k => `${enc(k)}=${enc(q[k])}`).join('&');
  const canonicalRequest = ['GET', canonicalUri, canonicalQuery, `host:${c.host}\n`, 'host', 'UNSIGNED-PAYLOAD'].join('\n');
  const stringToSign = ['AWS4-HMAC-SHA256', amzdate, credentialScope, sha256hex(canonicalRequest)].join('\n');
  const sig = crypto.createHmac('sha256', signingKey(c.appKey, datestamp, c.region)).update(stringToSign).digest('hex');
  return `https://${c.host}${canonicalUri}?${canonicalQuery}&X-Amz-Signature=${sig}`;
}

// Signed server-side request (Authorization-header flavor). Returns fetch Response.
async function s3Request(method, key, query, extraHeaders) {
  const c = cfg();
  const { datestamp, amzdate } = stamps();
  const canonicalUri = key ? `/${c.bucket}/${encKey(key)}` : `/${c.bucket}`;
  const payloadHash = sha256hex('');
  const h = { host: c.host, 'x-amz-content-sha256': payloadHash, 'x-amz-date': amzdate };
  if (extraHeaders) Object.keys(extraHeaders).forEach(k => { h[k.toLowerCase()] = extraHeaders[k]; });
  const names = Object.keys(h).sort();
  const canonicalHeaders = names.map(n => `${n}:${String(h[n]).trim()}\n`).join('');
  const signedHeaders = names.join(';');
  const canonicalQuery = Object.keys(query || {}).sort().map(k => `${enc(k)}=${enc(query[k])}`).join('&');
  const canonicalRequest = [method, canonicalUri, canonicalQuery, canonicalHeaders, signedHeaders, payloadHash].join('\n');
  const credentialScope = `${datestamp}/${c.region}/s3/aws4_request`;
  const stringToSign = ['AWS4-HMAC-SHA256', amzdate, credentialScope, sha256hex(canonicalRequest)].join('\n');
  const sig = crypto.createHmac('sha256', signingKey(c.appKey, datestamp, c.region)).update(stringToSign).digest('hex');
  const authorization = `AWS4-HMAC-SHA256 Credential=${c.keyId}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${sig}`;
  const url = `https://${c.host}${canonicalUri}` + (canonicalQuery ? `?${canonicalQuery}` : '');
  // Host is a forbidden fetch header (set automatically); send everything else + Authorization.
  const fetchHeaders = { Authorization: authorization };
  names.forEach(n => { if (n !== 'host') fetchHeaders[n] = h[n]; });
  return fetch(url, { method, headers: fetchHeaders });
}

async function listObjects(prefix) {
  const res = await s3Request('GET', '', { 'list-type': '2', prefix: prefix || '', 'max-keys': '1000' });
  const xml = await res.text();
  if (!res.ok) throw new Error('list ' + res.status + ' ' + xml.slice(0, 300));
  const items = [];
  const blocks = xml.match(/<Contents>[\s\S]*?<\/Contents>/g) || [];
  blocks.forEach(b => {
    const key = (b.match(/<Key>([\s\S]*?)<\/Key>/) || [])[1];
    const size = (b.match(/<Size>(\d+)<\/Size>/) || [])[1];
    const mod = (b.match(/<LastModified>([\s\S]*?)<\/LastModified>/) || [])[1];
    if (key) items.push({ key, size: +size || 0, lastModified: mod || '' });
  });
  return items;
}
async function copyObject(srcKey, destKey) {
  const c = cfg();
  const res = await s3Request('PUT', destKey, null, { 'x-amz-copy-source': `/${c.bucket}/${encKey(srcKey)}` });
  const t = await res.text();
  if (!res.ok) throw new Error('copy ' + res.status + ' ' + t.slice(0, 300));
  return true;
}
async function deleteObject(key) {
  const res = await s3Request('DELETE', key, null, null);
  if (!res.ok && res.status !== 204) { const t = await res.text(); throw new Error('delete ' + res.status + ' ' + t.slice(0, 300)); }
  return true;
}

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type, x-gallery-token',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
};
function authOK(event) {
  const c = cfg();
  if (!c.galleryToken) return false; // require a token to be set
  const t = (event.headers['x-gallery-token'] || event.headers['X-Gallery-Token'] || '');
  return t === c.galleryToken;
}

module.exports = { cfg, configured, presignGet, listObjects, copyObject, deleteObject, CORS, authOK };
