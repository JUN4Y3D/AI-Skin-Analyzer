from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
APP_JS = (ROOT / "app/static/js/app.js").read_text(encoding="utf-8")
CAMERA_JS = (ROOT / "app/static/js/camera.js").read_text(encoding="utf-8")
RESULTS_JS = (ROOT / "app/static/js/results.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/css/styles.css").read_text(encoding="utf-8")


def test_frontend_has_semantic_flow_and_accessible_statuses():
    for marker in ('data-screen="welcome"', 'data-screen="capture"', 'data-screen="results"'):
        assert marker in HTML
    assert 'data-screen="review"' not in HTML
    assert 'aria-live="assertive"' in HTML
    assert 'role="alert"' in HTML
    assert 'Skip to main content' in HTML
    assert '<dialog' in HTML


def test_camera_is_user_initiated_and_tracks_are_cleaned_up():
    assert "navigator.mediaDevices.getUserMedia" in CAMERA_JS
    assert "getTracks().forEach((track) => track.stop())" in CAMERA_JS
    assert "startCamera').addEventListener('click', openCamera)" in APP_JS
    assert "beforeunload" in APP_JS
    assert "capture(canvas)" in CAMERA_JS
    assert "await processPhoto(blob)" in APP_JS


def test_frontend_avoids_object_urls_and_prevents_duplicate_actions():
    assert "URL.createObjectURL" not in APP_JS
    assert "state.busy" in APP_JS
    assert "analysisId !== state.analysisId" in APP_JS


def test_upload_and_camera_automatically_start_one_analysis():
    assert "await processPhoto(file)" in APP_JS
    assert "analyzeImage(blob)" in APP_JS
    assert "reviewImage" not in APP_JS
    assert "?mode=" not in APP_JS


def test_obsolete_review_and_processing_modes_are_removed():
    combined = HTML + APP_JS + RESULTS_JS
    for obsolete in (
        'Review Photo',
        'Run Local Analysis',
        'name="mode"',
        'Compare both',
        'Framing comparison',
        'Original photograph analyzed',
    ):
        assert obsolete not in combined
    assert "Analyzed facial region" in RESULTS_JS


def test_dynamic_results_use_text_content_not_html_injection():
    assert ".innerHTML" not in APP_JS
    assert ".innerHTML" not in RESULTS_JS
    assert "textContent" in RESULTS_JS


def test_responsive_and_reduced_motion_styles_exist():
    assert "@media (max-width: 960px)" in CSS
    assert "@media (max-width: 700px)" in CSS
    assert "prefers-reduced-motion" in CSS
    assert "focus-visible" in CSS


def test_frontend_has_no_external_runtime_dependencies():
    combined = HTML + APP_JS + CAMERA_JS + RESULTS_JS + CSS
    assert "https://" not in combined
    assert "http://" not in combined
