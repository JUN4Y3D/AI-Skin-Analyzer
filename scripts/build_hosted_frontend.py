"""Generate a cloud-specific static copy without changing the local-first UI."""
from __future__ import annotations
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/public'

def build():
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'app/static', OUT / 'static', dirs_exist_ok=True)
    html = (ROOT/'app/templates/index.html').read_text(encoding='utf-8')
    swaps = {
        '__LOCAL_TOKEN__':'',
        '__MODEL_VERSION__':'hosted-v1',
        'Local experimental insights':'Hosted experimental insights',
        'Experimental local AI':'Experimental AI',
        'Private analysis':'AI analysis',
        'Local processing':'Cloud processing',
        'Processed locally on your device.':'The image is sent to a hosted inference server.',
        'LOCAL ANALYSIS':'AI SKIN ANALYSIS',
        'Your browser sends the selected image to this Mac’s localhost server.':'Your browser sends the photo securely to a hosted Python inference service.',
        'No cloud inference or analytics service is used.':'The application uses cloud inference; do not upload photos without consent.',
        'LOCAL PROCESSING':'ANALYZING PHOTO',
        'running the local models once.':'running the hosted models once.',
        'No photo retention':'In-memory handling',
        "Photos aren't saved by the app.":'The app does not intentionally store uploaded photos.',
    }
    for a,b in swaps.items():
        if a not in html:
            raise ValueError(f'Hosted HTML marker was changed or missing: {a!r}')
        html=html.replace(a,b)
    html=html.replace('<meta name="local-token" content="">','')
    (OUT/'index.html').write_text(html,encoding='utf-8')
    api = '''// Hosted same-origin Vercel API; proxy holds the backend secret server-side.
export async function analyzeImage(blob) {
  const timeout = new AbortController();
  const alarm = setTimeout(() => timeout.abort(), 58000);
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST', headers: {'Content-Type': blob.type}, body: blob,
      credentials: 'same-origin', cache: 'no-store', signal: timeout.signal
    });
    let data;
    try { data = await response.json(); } catch (_) { throw new Error('Inference service returned an unreadable response.'); }
    if (!response.ok) throw new Error(data.error || 'Analysis could not complete.');
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Analysis timed out. Please retry.');
    throw error;
  } finally { clearTimeout(alarm); }
}
'''
    (OUT/'static/js/api.js').write_text(api,encoding='utf-8')
    js = (OUT/'static/js/app.js').read_text(encoding='utf-8')
    # Retain local 10 MB limit while shrinking camera uploads for the hosted proxy.
    js = js.replace("blob.size > 10 * 1024 * 1024", "blob.size > 3_500_000")
    js = js.replace('no larger than 10 MB', 'smaller than 3.5 MB')
    (OUT/'static/js/app.js').write_text(js,encoding='utf-8')
    html = (OUT/'index.html').read_text(encoding='utf-8').replace('Maximum 10 MB','Maximum 3.5 MB')
    (OUT/'index.html').write_text(html,encoding='utf-8')
    results = (OUT/'static/js/results.js').read_text(encoding='utf-8')
    results = results.replace('Local duration','Hosted duration')
    results = results.replace(' ms local',' ms service')
    results = results.replace('A transparent view of what the local models returned', 'A transparent view of what the hosted models returned')
    results = results.replace('Automatically cropped · Processed locally · Image not retained', 'Automatically cropped · Hosted inference · Not saved by app code')
    (OUT/'static/js/results.js').write_text(results,encoding='utf-8')
    print('Hosted UI generated in:',OUT)

if __name__ == '__main__':
    build()
