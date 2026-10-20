const tokenNode = document.querySelector('meta[name="local-token"]');
const LOCAL_TOKEN = tokenNode?.content || '';

if (window.location.search) {
  history.replaceState(null, '', window.location.pathname + window.location.hash);
}

async function localRequest(path, blob, timeoutMs) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      method: 'POST',
      headers: {
        'Content-Type': blob.type,
        'X-Local-Token': LOCAL_TOKEN,
      },
      body: blob,
      cache: 'no-store',
      credentials: 'same-origin',
      signal: controller.signal,
    });
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new Error('The local server returned an unreadable response.');
    }
    if (!response.ok) {
      throw new Error(payload.error || 'The local request could not be completed.');
    }
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Local processing took too long. The selected photo is still available; please retry.');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export function analyzeImage(blob) {
  return localRequest('/api/analyze', blob, 150_000);
}
