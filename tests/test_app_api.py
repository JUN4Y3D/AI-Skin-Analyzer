from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from app.config import AppConfig
from app.server import handler_factory


class FakePipeline:
    def __init__(self, fail=False):
        self.fail = fail

    def analyze(self, raw, content_type):
        if self.fail:
            raise RuntimeError("private traceback detail")
        return {"length": len(raw), "content_type": content_type}


@pytest.fixture()
def local_server():
    token = "test-token"
    config = AppConfig(max_image_bytes=128)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(token, FakePipeline(), config))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read()
    returned = response.status, dict(response.getheaders()), payload
    connection.close()
    return returned


def test_page_requires_token_and_has_security_headers(local_server):
    port, token = local_server
    assert request(port, "GET", "/")[0] == 403
    status, headers, body = request(port, "GET", f"/?key={token}")
    assert status == 200 and b"AI Skin Analyzer" in body
    assert headers["Cache-Control"].startswith("no-store")
    assert headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert headers["Permissions-Policy"].startswith("camera=(self)")
    cookie = headers["Set-Cookie"]
    assert "skin_analyzer_session=" in cookie
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert request(port, "GET", "/", headers={"Cookie": cookie.split(";", 1)[0]})[0] == 200


def test_api_rejects_missing_token_and_cross_origin(local_server):
    port, token = local_server
    base = {"Content-Type": "image/png", "Origin": f"http://127.0.0.1:{port}"}
    assert request(port, "POST", "/api/analyze", b"123", base)[0] == 403
    hostile = {**base, "X-Local-Token": token, "Origin": "http://evil.example"}
    assert request(port, "POST", "/api/analyze", b"123", hostile)[0] == 403


def test_api_accepts_one_authorized_crop_only_analysis(local_server):
    port, token = local_server
    headers = {"Content-Type": "image/png", "Origin": f"http://127.0.0.1:{port}", "X-Local-Token": token}
    status, _, body = request(port, "POST", "/api/analyze", b"123", headers)
    assert status == 200 and json.loads(body)["length"] == 3
    status, _, body = request(port, "POST", "/api/analyze", b"4567", headers)
    assert status == 200 and json.loads(body)["length"] == 4
    status, _, body = request(port, "POST", "/api/analyze?mode=compare", b"123", headers)
    assert status == 400 and b"automatic" in body


def test_api_enforces_length_and_rejects_paths(local_server):
    port, token = local_server
    headers = {"Content-Type": "image/png", "Origin": f"http://127.0.0.1:{port}", "X-Local-Token": token}
    assert request(port, "POST", "/api/analyze", b"x" * 129, headers)[0] == 413
    assert request(port, "GET", "/static/../../etc/passwd")[0] == 404
    assert request(port, "POST", "/other", b"x", headers)[0] == 404


def test_server_does_not_leak_exception_text():
    token = "test-token"
    config = AppConfig(max_image_bytes=128)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(token, FakePipeline(fail=True), config))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        headers = {"Content-Type": "image/png", "Origin": f"http://127.0.0.1:{server.server_port}", "X-Local-Token": token}
        status, _, body = request(server.server_port, "POST", "/api/analyze", b"123", headers)
        assert status == 500
        assert b"private traceback detail" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
