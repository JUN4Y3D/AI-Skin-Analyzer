"""Hosted inference service; access via Vercel proxy only."""
from __future__ import annotations
import json
import os
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from app.config import AppConfig
from app.server import build_pipeline

MAX_IMAGE = 3_500_000  # Vercel Functions request limit is 4.5 MB
SLOTS = threading.BoundedSemaphore(2)

def create_handler(pipeline, version, secret):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'SkinAnalyzerHosted/2.0'
        sys_version = ''
        def log_message(self, *_args):
            pass
        def send_json(self, code, value):
            body = json.dumps(value, allow_nan=False).encode('utf-8')
            self.send_response(code)
            for key, val in (
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Content-Length', str(len(body))),
                ('Cache-Control', 'no-store, max-age=0'),
                ('X-Content-Type-Options', 'nosniff'),
                ('X-Robots-Tag', 'noindex, nofollow, noarchive'),
            ):
                self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)
        def authorized(self):
            return secrets.compare_digest(self.headers.get('X-Backend-Proxy-Secret', ''), secret)
        def do_GET(self):
            if self.path != '/api/health':
                return self.send_json(404, {'error': 'Not found'})
            if not self.authorized():
                return self.send_json(403, {'error': 'Forbidden'})
            return self.send_json(200, {'status': 'ready', 'model_version': version})
        def do_POST(self):
            if self.path != '/api/analyze':
                return self.send_json(404, {'error': 'Not found'})
            if not self.authorized():
                return self.send_json(403, {'error': 'Forbidden'})
            if self.headers.get('Transfer-Encoding'):
                return self.send_json(400, {'error': 'Unsupported upload encoding'})
            kind = self.headers.get('Content-Type', '').split(';')[0].lower().strip()
            if kind not in ('image/jpeg', 'image/png'):
                return self.send_json(415, {'error': 'Choose a JPEG or PNG photo'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                size = 0
            if not 0 < size <= MAX_IMAGE:
                return self.send_json(413, {'error': 'Photo must be under 3.5 MB'})
            if not SLOTS.acquire(blocking=False):
                return self.send_json(429, {'error': 'Analyzer is busy. Please retry shortly.'})
            try:
                self.connection.settimeout(55)
                image = self.rfile.read(size)
                if len(image) != size:
                    return self.send_json(400, {'error': 'Incomplete upload'})
                result = pipeline.analyze(image, kind)
                result['privacy'] = {'processed_locally': False, 'image_persisted': False,
                                     'processing_location': 'hosted_server'}
                self.send_json(200, result)
            except ValueError as e:
                self.send_json(400, {'error': str(e)})
            except Exception:
                print('Hosted inference request failed (details withheld)', file=sys.stderr)
                try:
                    self.send_json(500, {'error': 'Analysis failed. Try another image.'})
                except (OSError, BrokenPipeError):
                    pass
            finally:
                SLOTS.release()
        def do_OPTIONS(self):
            self.send_json(405, {'error': 'Method not allowed'})
    return Handler

def main():
    secret = os.environ.get('BACKEND_PROXY_SECRET', '')
    if len(secret) < 32:
        raise RuntimeError('BACKEND_PROXY_SECRET must be at least 32 random characters')
    os.environ['AI_SKIN_HOSTED_INFERENCE'] = '1'
    config = AppConfig(project_root=Path(__file__).resolve().parent, max_image_bytes=MAX_IMAGE)
    pipeline, _ = build_pipeline(config)
    server = ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))),
                                 create_handler(pipeline, config.model_version, secret))
    server.daemon_threads = True
    print('Hosted model ready', flush=True)
    server.serve_forever()
if __name__ == '__main__':
    main()
