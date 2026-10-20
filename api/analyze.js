export const config = { api: { bodyParser: false }, maxDuration: 60 };
const maxBytes = 3500000;
const json = (res, code, message) => res.status(code).setHeader('Cache-Control', 'no-store').json({error:message});
export default async function handler(req, res) {
  res.setHeader('Cache-Control','no-store, max-age=0');
  res.setHeader('X-Content-Type-Options','nosniff');
  if (req.method !== 'POST') return json(res,405,'Method not allowed');
  const origin = req.headers.origin;
  // Browser uploads must originate from the public page, not arbitrary websites.
  if (!origin || origin !== `https://${req.headers.host}`) return json(res,403,'Invalid origin');
  const kind = (req.headers['content-type']||'').split(';')[0].toLowerCase();
  if (!['image/jpeg','image/png'].includes(kind)) return json(res,415,'Choose a JPEG or PNG photo');
  const n = Number(req.headers['content-length']);
  if (!Number.isSafeInteger(n) || n < 1 || n > maxBytes) return json(res,413,'Photo must be under 3.5 MB');
  const url = process.env.BACKEND_URL;
  const secret = process.env.BACKEND_PROXY_SECRET;
  if (!/^https:\/\/[^/]+\/?$/.test(url||'') || !secret || secret.length < 32) {
    return json(res,503,'Analyzer is not available yet');
  }
  const chunks=[]; let received=0;
  try {
    for await (const chunk of req) {
      received += chunk.length;
      if (received > maxBytes) return json(res,413,'Photo must be under 3.5 MB');
      chunks.push(chunk);
    }
    if (received !== n) return json(res,400,'Incomplete photo upload');
    const response = await fetch(`${url.replace(/\/$/,'')}/api/analyze`,{
      method:'POST',
      headers:{'Content-Type':kind,'X-Backend-Proxy-Secret':secret},
      body:Buffer.concat(chunks),
      signal:AbortSignal.timeout(55000)
    });
    const payload = await response.text();
    res.status(response.status).setHeader('Content-Type','application/json; charset=utf-8').send(payload);
  } catch (_) { return json(res,502,'Inference service could not be reached. Please retry.'); }
}
