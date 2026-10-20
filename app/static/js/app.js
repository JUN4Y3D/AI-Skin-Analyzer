import { analyzeImage } from './api.js';
import { CameraController } from './camera.js';
import { renderResults } from './results.js';

const $ = (id) => document.getElementById(id);
const screens = [...document.querySelectorAll('[data-screen]')];
const state = { busy: false, analysisId: 0 };
const camera = new CameraController($('cameraVideo'), $('cameraDevice'), $('cameraStatus'));

function setScreen(name) {
  screens.forEach((screen) => {
    const active = screen.dataset.screen === name;
    screen.hidden = !active;
    screen.classList.toggle('is-active', active);
  });
  if (name !== 'capture') camera.stop();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function setProcessing(active) {
  state.busy = active;
  $('processingOverlay').hidden = !active;
}

function toast(message) {
  const node = $('toast');
  node.textContent = message;
  node.hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => { node.hidden = true; }, 4200);
}

function clearSelected() {
  state.analysisId += 1;
  $('photoFile').value = '';
  $('selectionMessage').textContent = '';
  $('recoveryActions').hidden = true;
}

function selectBlob(blob) {
  if (!blob) return false;
  const validType = ['image/jpeg', 'image/png'].includes(blob.type);
  if (!validType || blob.size === 0 || blob.size > 10 * 1024 * 1024) {
    $('selectionMessage').textContent = 'Choose a non-empty JPEG or PNG no larger than 10 MB.';
    $('recoveryActions').hidden = false;
    return false;
  }
  $('selectionMessage').textContent = '';
  $('recoveryActions').hidden = true;
  return true;
}

async function processPhoto(blob) {
  if (state.busy || !selectBlob(blob)) return;
  const analysisId = ++state.analysisId;
  camera.stop();
  setProcessing(true);
  try {
    const result = await analyzeImage(blob);
    if (analysisId !== state.analysisId) return;
    renderResults($('resultsMount'), result, resetAnalysis);
    setScreen('results');
  } catch (error) {
    if (analysisId !== state.analysisId) return;
    $('selectionMessage').textContent = error.message;
    $('recoveryActions').hidden = false;
    toast('Analysis was not completed. Retake the photo or choose another image.');
  } finally {
    if (analysisId === state.analysisId) setProcessing(false);
  }
}

async function openCamera() {
  if (state.busy) return;
  setScreen('capture');
  selectSource('camera');
  $('selectionMessage').textContent = '';
  $('recoveryActions').hidden = true;
  $('cameraPlaceholder').hidden = false;
  $('cameraPlaceholder').querySelector('.spinner').hidden = false;
  $('cameraPlaceholder').querySelector('p').textContent = 'Waiting for camera permission…';
  $('capturePhoto').disabled = true;
  $('retryCamera').hidden = true;
  $('cameraStatus').textContent = 'Allow camera access when your browser asks.';
  try {
    await camera.start();
    $('cameraPlaceholder').hidden = true;
    $('capturePhoto').disabled = false;
    $('cameraStatus').textContent = 'Center one face inside the guide. Analysis starts immediately after capture.';
  } catch (error) {
    $('cameraPlaceholder').hidden = false;
    $('cameraPlaceholder').querySelector('p').textContent = error.message;
    $('cameraPlaceholder').querySelector('.spinner').hidden = true;
    $('retryCamera').hidden = false;
    $('cameraStatus').textContent = error.message;
  }
}

function selectSource(source) {
  const isCamera = source === 'camera';
  $('cameraTab').setAttribute('aria-selected', String(isCamera));
  $('uploadTab').setAttribute('aria-selected', String(!isCamera));
  $('cameraPanel').hidden = !isCamera;
  $('uploadPanel').hidden = isCamera;
  if (!isCamera) camera.stop();
}

async function switchToCamera() {
  selectSource('camera');
  if (!camera.stream) await openCamera();
}

function switchToUpload(openPicker = false) {
  if (state.busy) return;
  setScreen('capture');
  selectSource('upload');
  $('selectionMessage').textContent = '';
  $('recoveryActions').hidden = true;
  if (openPicker) window.setTimeout(() => $('photoFile').click(), 80);
}

function resetAnalysis() {
  clearSelected();
  $('resultsMount').replaceChildren();
  setScreen('welcome');
}

$('startCamera').addEventListener('click', openCamera);
$('startUpload').addEventListener('click', () => switchToUpload(true));
$('cameraTab').addEventListener('click', switchToCamera);
$('uploadTab').addEventListener('click', () => switchToUpload(false));
$('retryCamera').addEventListener('click', openCamera);
$('cameraDevice').addEventListener('change', async () => {
  try {
    await camera.start($('cameraDevice').value);
    $('cameraPlaceholder').hidden = true;
    $('capturePhoto').disabled = false;
  } catch (error) {
    $('cameraStatus').textContent = error.message;
  }
});
$('capturePhoto').addEventListener('click', async () => {
  if (state.busy) return;
  try {
    const blob = await camera.capture($('cameraCanvas'));
    camera.stop();
    await processPhoto(blob);
  } catch (error) {
    camera.stop();
    $('selectionMessage').textContent = error.message;
    $('recoveryActions').hidden = false;
  }
});
$('retakePhoto').addEventListener('click', openCamera);
$('uploadAnother').addEventListener('click', () => switchToUpload(true));
$('photoFile').addEventListener('change', async () => {
  const file = $('photoFile').files[0];
  $('photoFile').value = '';
  await processPhoto(file);
});

const uploadZone = $('uploadZone');
['dragenter', 'dragover'].forEach((eventName) => uploadZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  uploadZone.classList.add('is-dragging');
}));
['dragleave', 'drop'].forEach((eventName) => uploadZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  uploadZone.classList.remove('is-dragging');
}));
uploadZone.addEventListener('drop', async (event) => processPhoto(event.dataTransfer.files[0]));

$('captureBack').addEventListener('click', () => {
  camera.stop();
  clearSelected();
  setScreen('welcome');
});
$('brandHome').addEventListener('click', (event) => {
  event.preventDefault();
  if (!state.busy) resetAnalysis();
});

const dialog = $('howDialog');
$('openHow').addEventListener('click', () => dialog.showModal());
$('closeHow').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });

window.addEventListener('beforeunload', () => {
  state.analysisId += 1;
  camera.stop();
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) camera.stop();
});
