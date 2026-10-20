# Hosted deployment (Vercel + private Railway inference)

**This is a separate hosted mode.** The original Mac localhost app and its local privacy wording remain unchanged. The hosted website sends photos over HTTPS to Vercel, which forwards them to your Railway Python service. Cloud infrastructure may process and temporarily buffer requests; neither application component intentionally writes submitted images to disk. Do not promise absolute deletion or immunity from cloud logs/crash dumps.

This deployment retains four **experimental** model outputs, not clinical diagnoses, biological age, actual hydration/sebum or yes/no acne detection. The model was not independently validated.

## Architecture

- `scripts/build_hosted_frontend.py` generates `web/public/` at build time, deriving the HTML/CSS/JS from the local UI but replacing local privacy copy.
- Vercel uses `vercel.json` and `api/{analyze,health}.js`. Vercel and Railway share `BACKEND_PROXY_SECRET`; clients never see the secret. The server enforces a 3.5 MB upload cap, MIME checks, in-memory processing and two simultaneous inference slots.
- `scripts/prepare_hosted_backend.py` creates a **new directory outside the Git checkout** containing backend code and exactly the existing inference artifacts. Two dataset-review CSV files are checked locally and replaced by their SHA-256 attestation, rather than shipped.
- `deploy/backend/Dockerfile` pins TensorFlow, Keras and headless OpenCV dependencies. Railway needs enough memory to load TensorFlow/ResNet50 and handle inference.

## 1. Apply and review the patch

From the project directory, unpack the patch into your existing Git checkout **only after reviewing it**. The patch includes a new `.vercelignore`, `vercel.json`, API functions, scripts and deployment backend; it does not include private artifacts. Run:

```sh
source ~/Developer/venvs/ai-skin-analyzer/bin/activate
cd ~/Desktop/AI_Skin_Analyzer
python scripts/apply_hosted_patch.py
python scripts/build_hosted_frontend.py
python -m pytest -q -p no:cacheprovider
python scripts/run_app.py --check
```

The hosted build output `web/public/` is generated and should be excluded from Git. Only push the new source/config/docs, and never stage `reports/`, `train/`, `val/`, `test/`, or `labels/`. Review `git diff --cached --name-only` before committing.

## 2. Package private weights securely on your Mac

```sh
cd ~/Desktop/AI_Skin_Analyzer
python scripts/prepare_hosted_backend.py --output ~/Developer/ai-skin-hosted-private-v1
```

This validates the existing fitted artifacts with their historic SHA-256 provenance checks before packaging. No original face photos, review manifests, training images or original dataset labels are transferred. The resulting **private directory still contains the trained weights and reference embeddings**. Never commit, attach or share it publicly.

## 3. Deploy Railway backend (requires a Railway account and billing/resource review)

Install Railway CLI and authenticate according to https://docs.railway.com/guides/cli. Create a **new private project** with a single service built from the local directory above, using its Dockerfile. Ensure the service has enough RAM and a production domain. Set a randomly generated shared secret in Railway (do not paste it in chats, commands recorded in shell history, or Git), for example using a local `.env` or Railway dashboard. Environment variable: `BACKEND_PROXY_SECRET`. Do not use a public Git repository for this service. Deploy that staged directory with `railway up` from inside it. Check that backend starts and logs only `Hosted model ready`, then verify `/api/health` responds **403 without the secret**. Do not share secret-bearing URLs.

**Before accepting uploads**, configure Railway networking/edge security and service resource limits; Vercel's function limits alone do not constitute a complete abuse or cost-control policy. The backend is reachable from the internet but requires the secret for health and inference routes.

## 4. Deploy the Vercel frontend

Import the **public source-only GitHub repository** into Vercel. Set root directory to repository root, Framework = Other, build command and output directory as provided by `vercel.json`. Configure these two Vercel environment variables in Production and Preview:

- `BACKEND_URL`: the HTTPS Railway domain, no path (e.g. `https://example.up.railway.app`)
- `BACKEND_PROXY_SECRET`: the same long random secret used by Railway

The Vercel frontend should not receive credentials in browser JavaScript. The serverless proxy will pass the secret to the backend. Vercel Functions have request limits; the hosted build explicitly caps images at 3.5 MB. No training artifacts are stored in Vercel or public GitHub.

## 5. Full live verification before CV publication

1. `https://YOUR-VERCEL-URL/api/health` should return `{"status":"ready"}` once all services are configured.
2. Verify camera capture and JPEG/PNG upload on the Vercel HTTPS site, confirm one-face cropping, all four outputs and honest disclosures.
3. Verify invalid images, multi-face and no-face errors, request size, rate limiting and image persistence policy.
4. Verify private model startup and regression in the hosting environment. Confirm no credentials, photos or datasets appear in logs or public URLs.
5. Add the *verified actual* Vercel domain to the GitHub README and CV only after these tests pass.

Until then, a deployed frontend is **not** a live functioning AI analyzer.

## Security and production notes

The public backend is gated with a shared proxy secret, but a shared secret alone does not prevent abuse through the open Vercel frontend. Add provider-level bot protections, request throttling, alerting, spend caps and a content/privacy review before wide public promotion. Investigate server/provider log retention and GDPR/privacy obligations for uploaded face images. This is an experimental portfolio demonstration and not a medical tool. Regularly rotate credentials. Never copy original private CSV manifests into the deployed image.
