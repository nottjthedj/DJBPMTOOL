// One-shot admin function: enable CORS on the B2 bucket so browsers can upload.
// Uses the B2 native API with the keys already in the environment. Guarded by GALLERY_TOKEN.
// Invoke once (POST with x-gallery-token). Safe to re-run (idempotent).
const S3 = require('./lib/s3');

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: S3.CORS, body: '' };
  if (!S3.authOK(event)) return { statusCode: 401, headers: S3.CORS, body: JSON.stringify({ error: 'Bad or missing token' }) };
  const c = S3.cfg();
  if (!c.keyId || !c.appKey || !c.bucket) return { statusCode: 500, headers: S3.CORS, body: JSON.stringify({ error: 'Not configured' }) };

  try {
    // 1) authorize
    const authRes = await fetch('https://api.backblazeb2.com/b2api/v3/b2_authorize_account', {
      headers: { Authorization: 'Basic ' + Buffer.from(c.keyId + ':' + c.appKey).toString('base64') }
    });
    const auth = await authRes.json();
    if (!authRes.ok) return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ step: 'authorize', auth }) };
    const apiUrl = auth.apiInfo.storageApi.apiUrl;
    const token = auth.authorizationToken;
    const accountId = auth.accountId;

    // 2) find the bucket id
    const lbRes = await fetch(apiUrl + '/b2api/v3/b2_list_buckets', {
      method: 'POST', headers: { Authorization: token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ accountId, bucketName: c.bucket })
    });
    const lb = await lbRes.json();
    const bucket = (lb.buckets || [])[0];
    if (!bucket) return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ step: 'list', lb }) };

    // 3) set CORS rules (allow browser uploads/downloads from the booth origins)
    const corsRules = [{
      corsRuleName: '{{web.corsRuleName}}',
      allowedOrigins: {{web.corsOriginsJs}},
      allowedOperations: ['s3_put', 's3_get', 's3_head', 's3_post'],
      allowedHeaders: ['*'],
      exposeHeaders: ['etag', 'x-amz-request-id'],
      maxAgeSeconds: 3600
    }];
    const upRes = await fetch(apiUrl + '/b2api/v3/b2_update_bucket', {
      method: 'POST', headers: { Authorization: token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ accountId, bucketId: bucket.bucketId, corsRules })
    });
    const up = await upRes.json();
    return { statusCode: upRes.ok ? 200 : 502, headers: { ...S3.CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ok: upRes.ok, corsRules: up.corsRules || up }) };
  } catch (e) {
    return { statusCode: 502, headers: S3.CORS, body: JSON.stringify({ error: String(e.message || e) }) };
  }
};
