from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def test_hosted_source_privacy_boundary():
    assert 'host: str = "127.0.0.1"' in (ROOT/'app/config.py').read_text()
    server=(ROOT/'deploy/backend/server.py').read_text()
    assert 'BACKEND_PROXY_SECRET' in server
    assert 'processed_locally' in server and 'False' in server
    assert 'secrets.compare_digest' in server
    assert 'COPY train' not in (ROOT/'deploy/backend/Dockerfile').read_text()

def test_hosted_ui_copy_is_not_local_ui():
    subprocess.run([sys.executable,str(ROOT/'scripts/build_hosted_frontend.py')],check=True)
    hosted=(ROOT/'web/public/index.html').read_text()
    original=(ROOT/'app/templates/index.html').read_text()
    assert 'Processed locally on your device' in original
    assert 'Processed locally on your device' not in hosted
    assert 'hosted inference server' in hosted
    assert '__LOCAL_TOKEN__' not in hosted
    assert 'BACKEND_PROXY_SECRET' in (ROOT/'api/analyze.js').read_text()
