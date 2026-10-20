export class CameraController {
  constructor(video, deviceSelect, statusElement) {
    this.video = video;
    this.deviceSelect = deviceSelect;
    this.statusElement = statusElement;
    this.stream = null;
    this.facingMode = 'user';
    this.onDevicesChanged = this.refreshDevices.bind(this);
  }

  get supported() {
    return Boolean(navigator.mediaDevices?.getUserMedia);
  }

  async start(deviceId = null) {
    this.stop();
    if (!this.supported) {
      throw new Error('This browser does not expose camera access. Use Upload Photo instead.');
    }
    const video = deviceId
      ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 960 } }
      : { facingMode: { ideal: 'user' }, width: { ideal: 1280 }, height: { ideal: 960 } };
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ video, audio: false });
      this.video.srcObject = this.stream;
      await this.video.play();
      const settings = this.stream.getVideoTracks()[0]?.getSettings?.() || {};
      this.facingMode = settings.facingMode || 'user';
      this.video.classList.toggle('mirrored', this.facingMode === 'user');
      await this.refreshDevices(settings.deviceId || deviceId);
      navigator.mediaDevices.addEventListener?.('devicechange', this.onDevicesChanged);
      return settings;
    } catch (error) {
      this.stop();
      if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
        throw new Error('Camera permission was denied. Allow access in browser settings, or upload a photo.');
      }
      if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        throw new Error('No camera is available. Connect a camera or use Upload Photo.');
      }
      if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        throw new Error('The camera is busy or unavailable. Close other camera apps and try again.');
      }
      throw new Error('The camera could not start. Use Upload Photo or try again.');
    }
  }

  async refreshDevices(selectedId = null) {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === 'videoinput');
    const current = selectedId || this.deviceSelect.value;
    this.deviceSelect.replaceChildren();
    devices.forEach((device, index) => {
      const option = document.createElement('option');
      option.value = device.deviceId;
      option.textContent = device.label || `Camera ${index + 1}`;
      option.selected = device.deviceId === current;
      this.deviceSelect.append(option);
    });
    this.deviceSelect.disabled = devices.length < 2;
  }

  async capture(canvas) {
    if (!this.stream || this.video.readyState < 2) {
      throw new Error('The camera is not ready yet.');
    }
    const width = this.video.videoWidth;
    const height = this.video.videoHeight;
    if (!width || !height) throw new Error('The camera did not provide a video frame.');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d', { alpha: false });
    if (this.facingMode === 'user') {
      context.translate(width, 0);
      context.scale(-1, 1);
    }
    context.drawImage(this.video, 0, 0, width, height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
    if (!blob) throw new Error('The captured frame could not be prepared.');
    return blob;
  }

  stop() {
    navigator.mediaDevices?.removeEventListener?.('devicechange', this.onDevicesChanged);
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    this.video.pause();
    this.video.srcObject = null;
    this.video.classList.remove('mirrored');
  }
}
