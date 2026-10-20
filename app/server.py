"""Hardened localhost HTTP server for AI Skin Analyzer 2.0."""
from __future__ import annotations

import argparse
import html
import json
import secrets
import sys
import threading
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app.config import AppConfig
from app.imaging.face_detection import FaceDetector
from app.inference.artifacts import load_artifacts
from app.inference.models import Predictor, component_outputs
from app.inference.pipeline import AnalysisPipeline


STATIC_FILES = {
    "/static/css/styles.css": ("static/css/styles.css", "text/css; charset=utf-8"),
    "/static/js/api.js": ("static/js/api.js", "text/javascript; charset=utf-8"),
    "/static/js/camera.js": ("static/js/camera.js", "text/javascript; charset=utf-8"),
    "/static/js/results.js": ("static/js/results.js", "text/javascript; charset=utf-8"),
    "/static/js/app.js": ("static/js/app.js", "text/javascript; charset=utf-8"),
}


def _read_asset(relative: str) -> bytes:
    app_root = Path(__file__).resolve().parent
    target = (app_root / relative).resolve(strict=True)
    if app_root.resolve() not in target.parents or not target.is_file() or target.is_symlink():
        raise ValueError("Unsafe application asset")
    return target.read_bytes()


def handler_factory(token: str, pipeline: AnalysisPipeline, config: AppConfig):
    expected_origin = None

    class Handler(BaseHTTPRequestHandler):
        server_version = "SkinAnalyzerLocal/2.0"
        sys_version = ""

        def log_message(self, *_):
            # Suppress URLs, query tokens, filenames, and image metadata.
            return

        @property
        def origin(self) -> str:
            return expected_origin or f"http://{config.host}:{self.server.server_port}"

        def _headers(self, code: int, kind: str, length: int, *, page: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
            self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive")
            if page:
                self.send_header(
                    "Set-Cookie",
                    f"skin_analyzer_session={token}; HttpOnly; SameSite=Strict; Path=/",
                )
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; img-src 'self' blob: data:; media-src 'self' blob:; "
                    "connect-src 'self'; script-src 'self'; style-src 'self'; "
                    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'",
                )
            self.end_headers()

        def _send(self, code: int, body: bytes, kind: str, *, page: bool = False) -> None:
            self._headers(code, kind, len(body), page=page)
            self.wfile.write(body)

        def _json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def _host_valid(self) -> bool:
            return self.headers.get("Host") == f"{config.host}:{self.server.server_port}"

        def _api_authorized(self) -> bool:
            if not self._host_valid():
                return False
            if not secrets.compare_digest(self.headers.get("X-Local-Token", ""), token):
                return False
            if self.command == "POST" and self.headers.get("Origin") != self.origin:
                return False
            fetch_site = self.headers.get("Sec-Fetch-Site")
            return fetch_site in (None, "same-origin")

        def _read_image(self) -> tuple[bytes, str] | None:
            if self.headers.get("Transfer-Encoding"):
                self._json(400, {"error": "Unsupported upload encoding"})
                return None
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0:
                self._json(400, {"error": "Choose a non-empty image"})
                return None
            if length > config.max_image_bytes:
                self._json(413, {"error": "Image must be 10 MB or smaller"})
                return None
            return self.rfile.read(length), self.headers.get("Content-Type", "")

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in STATIC_FILES:
                relative, kind = STATIC_FILES[path]
                try:
                    body = _read_asset(relative)
                except (OSError, ValueError):
                    self._send(404, b"Not found", "text/plain; charset=utf-8")
                    return
                self._send(200, body, kind)
                return
            if path == "/api/health":
                if not self._api_authorized():
                    self._json(403, {"error": "Forbidden"})
                    return
                self._json(200, {"status": "ready", "model_version": config.model_version})
                return
            if path != "/" or not self._host_valid():
                self._send(404, b"Not found", "text/plain; charset=utf-8")
                return
            supplied = parse_qs(urlsplit(self.path).query).get("key", [""])[0]
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
            except Exception:
                cookie.clear()
            session = cookie.get("skin_analyzer_session")
            cookie_token = session.value if session is not None else ""
            if not (
                secrets.compare_digest(supplied, token)
                or secrets.compare_digest(cookie_token, token)
            ):
                self._send(403, b"Forbidden", "text/plain; charset=utf-8")
                return
            template = _read_asset("templates/index.html").decode("utf-8")
            page = template.replace("__LOCAL_TOKEN__", html.escape(token, quote=True)).replace(
                "__MODEL_VERSION__", html.escape(config.model_version, quote=True)
            )
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8", page=True)

        def do_POST(self):
            path = urlsplit(self.path).path
            if path != "/api/analyze":
                self._json(404, {"error": "Not found"})
                return
            if not self._api_authorized():
                self._json(403, {"error": "Forbidden"})
                return
            upload = self._read_image()
            if upload is None:
                return
            raw, content_type = upload
            try:
                if urlsplit(self.path).query:
                    raise ValueError("Image-processing options are not supported; face cropping is automatic")
                result = pipeline.analyze(raw, content_type)
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            except Exception:
                print("Local request failed; no image content or request metadata logged", file=sys.stderr)
                self._json(500, {"error": "Local processing failed. You can retry or choose another image."})
                return
            finally:
                del raw
            self._json(200, result)

        def do_OPTIONS(self):
            self._json(405, {"error": "Method not allowed"})

    return Handler


def build_pipeline(config: AppConfig) -> tuple[AnalysisPipeline, dict]:
    artifacts = load_artifacts(config.project_root, config.skin_run, config.components_run)
    predictor = Predictor(artifacts, config.model_version)
    return AnalysisPipeline(config, predictor, FaceDetector()), {
        "development_accuracy": artifacts.skin_metrics["development_accuracy"],
        "age_mae": artifacts.component_metrics["age_regression"]["dev_mae_provisional_numeric_target"],
    }


def _synthetic_self_test() -> None:
    import io

    import numpy as np
    from PIL import Image

    vector = np.ones(2048, dtype="float32")
    unit = vector / np.linalg.norm(vector)
    age = {"support": np.stack([unit, -unit]), "dual": np.array([5, -2]), "intercept": np.array(20.0)}
    refs = {
        "acne": {
            "positive_reference_embeddings": np.stack([unit, unit, -unit]),
            "top_k": np.array(2),
            "similarity_threshold_positive_p10": np.array(0.5),
        }
    }
    target, similarity = component_outputs(vector, age, refs)
    assert target == 27 and float(similarity["acne"]["similarity"]) > 0.99
    image = Image.new("RGB", (640, 640), (90, 130, 160))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    assert buffer.getvalue().startswith(b"\x89PNG")
    print("AI Skin Analyzer 2.0 synthetic self-test PASSED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Validate artifacts without loading TensorFlow")
    action.add_argument("--self-test", action="store_true", help="Run dependency-light synthetic checks")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skin-run", default=AppConfig.skin_run)
    parser.add_argument("--components-run", default=AppConfig.components_run)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            _synthetic_self_test()
            return 0
        config = AppConfig(
            project_root=args.project_root.expanduser().resolve(strict=True),
            port=args.port,
            skin_run=args.skin_run,
            components_run=args.components_run,
        )
        if args.check:
            artifacts = load_artifacts(config.project_root, config.skin_run, config.components_run)
            print("Private artifact integrity check PASSED")
            print("Class order:", ", ".join(artifacts.skin_metrics["training_classes_order"]))
            print("Model version:", config.model_version)
            print("No TensorFlow model or user image was loaded")
            return 0

        print("Validating private artifacts and loading the local model once…", flush=True)
        pipeline, metrics = build_pipeline(config)
        token = secrets.token_urlsafe(32)
        server = ThreadingHTTPServer((config.host, config.port), handler_factory(token, pipeline, config))
        server.daemon_threads = True
        address = f"http://{config.host}:{server.server_port}/?key={token}"
        print("AI SKIN ANALYZER 2.0 READY", flush=True)
        print(f"Exploratory development accuracy: {100 * metrics['development_accuracy']:.2f}% (not independent)", flush=True)
        print(f"Age-like development MAE: {metrics['age_mae']:.3f} provisional label units", flush=True)
        print("Acne and dark-circle outputs remain positive-reference similarities, not detection.", flush=True)
        print("Open this private local URL:", address, flush=True)
        print("Photos are processed in memory by this local process and are not saved by the app.", flush=True)
        if not args.no_open:
            webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        print("Local server stopped; camera/upload images were not persisted.")
        return 0
    except (AssertionError, ImportError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"AI SKIN ANALYZER STOPPED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
