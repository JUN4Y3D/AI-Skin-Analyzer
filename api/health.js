export const config = { maxDuration: 20 };
export default async function handler(req,res) {
  res.setHeader('Cache-Control','no-store');
  if(req.method!=='GET') return res.status(405).json({error:'Method not allowed'});
  const url=process.env.BACKEND_URL, secret=process.env.BACKEND_PROXY_SECRET;
  if(!/^https:\/\/[^/]+\/?$/.test(url||'') || !secret || secret.length<32)
    return res.status(503).json({status:'not_configured'});
  try {
    const upstream=await fetch(`${url.replace(/\/$/,'')}/api/health`,{
      headers:{'X-Backend-Proxy-Secret':secret},signal:AbortSignal.timeout(12000)});
    if(!upstream.ok) return res.status(503).json({status:'unavailable'});
    return res.status(200).json({status:'ready'});
  }catch(_){return res.status(503).json({status:'unavailable'});}
}
