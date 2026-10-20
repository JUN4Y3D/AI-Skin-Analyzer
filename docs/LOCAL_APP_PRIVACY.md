# Local application privacy and security model

## Data flow

When a user captures or selects a photograph, the browser holds it in a temporary object URL and immediately sends the bytes to a Python server at `127.0.0.1`. The server validates, detects one face, crops, and analyzes it in memory. The application does not write uploads, captures, or generated crops to disk.

No external inference API, CDN, font service, telemetry client, or analytics SDK is used. “Processed locally” means the photograph leaves browser memory for the local Python process; it does not mean the browser alone performs inference.

## Implemented protections

- Loopback-only server binding.
- Random per-process access token and constant-time token comparison.
- Host, Origin, and same-origin fetch checks for API writes.
- Allowlisted static paths; browser input cannot select a server filesystem path.
- JPEG/PNG type, signature, byte, pixel-count, and decode validation.
- EXIF orientation handling and maximum 20-megapixel input.
- No request logging of tokens, filenames, or image metadata.
- Generic error responses without internal paths or tracebacks.
- `no-store` responses and restrictive browser security headers.
- In-memory crops and result serialization.
- Object-URL revocation and camera-track shutdown.
- Multiple-face ambiguity blocks cropping instead of selecting a person.

## Residual risks

- Any process running as the local user may potentially inspect local process memory.
- The browser and operating system enforce camera permission; the app cannot guarantee their behavior.
- A crash dump, external screen recorder, browser extension, or separately configured system backup could capture sensitive content outside the app's control.
- De-identified or cropped face images can still be sensitive and potentially identifiable.
- Localhost tokens protect against casual cross-origin requests but do not replace operating-system account security.

## User guidance

- Analyze only images you have permission to use.
- Avoid shared or untrusted computers.
- Close the local server after use.
- Do not share the tokenized URL or screenshots containing it.
- Do not publish result screenshots containing a person's face without permission.
- Use **Analyze another photo** or close the page to release browser object URLs; stop the Python process with `Ctrl+C` when finished.

## Development and publication

Never log or commit uploads, captures, private filenames, models, embeddings, datasets, manifests, or session URLs. Tests must use synthetic or explicitly permitted fixtures. Public releases require a reviewed source-only manifest; `.gitignore` is a safeguard, not proof that a file was never tracked or published.
