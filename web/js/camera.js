// Camera for the simulated device. Sources:
//   webcam  - getUserMedia
//   screen  - getDisplayMedia (a screen, window or tab: e.g. a QR code shown
//             on another site)
//   image   - a file, a pasted image or a dropped image
// An optional region (drawn on the preview) limits what is used.
//
// For Krux, each frame is cropped to 3:4 and scaled to 240x320 exactly like
// the desktop simulator does, and QR codes are decoded with zbar (the same
// library the desktop simulator uses through pyzbar).
import { scanImageData } from "./vendor/zbar/zbar.mjs";
import { C, CAM_W, CAM_H, QR_BYTES } from "./shared.js";

const KRUX_FPS = 15;
const DECODE_INTERVAL = 120; // ms between decode attempts
const DECODE_MAX_SIDE = 1600;

export class CameraFeed {
  constructor({ preview, onChange }) {
    this.views = []; // canvases showing the source, where a region can be drawn
    this.onChange = onChange || (() => {});
    this.kind = null; // "webcam" | "screen" | "image"
    this.stream = null;
    this.video = document.createElement("video");
    this.video.muted = true;
    this.video.playsInline = true;
    this.image = null; // ImageBitmap
    this.region = null; // {x, y, w, h} normalised 0..1
    this.sim = null; // {ctrl, shared}
    this.lastKrux = 0;
    this.lastDecode = 0;
    this.decoding = false;
    this.lastQR = null;
    this.kruxCanvas = new OffscreenCanvas(CAM_W, CAM_H);
    this.kctx = this.kruxCanvas.getContext("2d", { willReadFrequently: true });
    this.decCanvas = new OffscreenCanvas(16, 16);
    this.dctx = this.decCanvas.getContext("2d", { willReadFrequently: true });
    this.addView(preview);
    this._loop = this._loop.bind(this);
    requestAnimationFrame(this._loop);
  }

  attach(sim) {
    this.sim = sim;
  }

  get active() {
    return !!this.kind;
  }

  get kruxWants() {
    return !!(this.sim && this.sim.ctrl.get(C.CAM_ON));
  }

  async useWebcam() {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    await this._useStream(stream, "webcam");
  }

  async useScreen() {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: { ideal: 15 } },
      audio: false,
    });
    await this._useStream(stream, "screen");
  }

  async useImage(blob) {
    const bmp = await createImageBitmap(blob);
    this.stop();
    this.image = bmp;
    this.kind = "image";
    this.region = null;
    this.onChange();
  }

  async _useStream(stream, kind) {
    this.stop();
    this.stream = stream;
    this.kind = kind;
    this.region = null;
    this.video.srcObject = stream;
    await this.video.play().catch(() => {});
    for (const t of stream.getVideoTracks()) {
      t.addEventListener("ended", () => {
        if (this.stream === stream) this.stop();
      });
    }
    this.onChange();
  }

  stop() {
    if (this.stream) for (const t of this.stream.getTracks()) t.stop();
    this.stream = null;
    this.video.srcObject = null;
    this.image = null;
    this.kind = null;
    this.region = null;
    this.onChange();
  }

  clearRegion() {
    this.region = null;
    this.onChange();
  }

  _source() {
    if (this.kind === "image" && this.image) return [this.image, this.image.width, this.image.height];
    if (this.stream && this.video.videoWidth) return [this.video, this.video.videoWidth, this.video.videoHeight];
    return null;
  }

  // Source rectangle in source pixels (region or whole frame)
  _rect(sw, sh) {
    const r = this.region;
    if (!r) return [0, 0, sw, sh];
    return [r.x * sw, r.y * sh, Math.max(1, r.w * sw), Math.max(1, r.h * sh)];
  }

  _loop(now) {
    requestAnimationFrame(this._loop);
    const src = this._source();
    this._drawPreview(src);
    if (!src || !this.kruxWants) return;
    const [el, sw, sh] = src;
    const [rx, ry, rw, rh] = this._rect(sw, sh);
    if (now - this.lastKrux >= 1000 / KRUX_FPS) {
      this.lastKrux = now;
      this._sendFrame(el, rx, ry, rw, rh);
    }
    if (!this.decoding && now - this.lastDecode >= DECODE_INTERVAL) {
      this.lastDecode = now;
      this._decode(el, rx, ry, rw, rh);
    }
  }

  _sendFrame(el, rx, ry, rw, rh) {
    // Crop to 3:4 (portrait) around the centre, like the desktop simulator,
    // then scale to 240x320.
    const target = CAM_W / CAM_H;
    let cx = rx, cy = ry, cw = rw, ch = rh;
    if (cw / ch > target) {
      cw = ch * target;
      cx = rx + (rw - cw) / 2;
    } else {
      ch = cw / target;
      cy = ry + (rh - ch) / 2;
    }
    this.kctx.imageSmoothingQuality = "high";
    this.kctx.drawImage(el, cx, cy, cw, ch, 0, 0, CAM_W, CAM_H);
    const data = this.kctx.getImageData(0, 0, CAM_W, CAM_H).data;
    const { ctrl, shared } = this.sim;
    new Uint8Array(shared.cam).set(data);
    ctrl.set(C.CAM_W, CAM_W);
    ctrl.set(C.CAM_H, CAM_H);
    ctrl.add(C.CAM_SEQ);
  }

  async _decode(el, rx, ry, rw, rh) {
    this.decoding = true;
    try {
      const scale = Math.min(1, DECODE_MAX_SIDE / Math.max(rw, rh));
      const w = Math.max(1, Math.round(rw * scale));
      const h = Math.max(1, Math.round(rh * scale));
      if (this.decCanvas.width !== w || this.decCanvas.height !== h) {
        this.decCanvas.width = w;
        this.decCanvas.height = h;
      }
      this.dctx.drawImage(el, rx, ry, rw, rh, 0, 0, w, h);
      const symbols = await scanImageData(this.dctx.getImageData(0, 0, w, h));
      const qr = symbols.find((s) => s.typeName === "ZBAR_QRCODE") || symbols[0];
      if (qr && this.kruxWants) this._sendQR(new Uint8Array(qr.data));
    } catch (e) {
      console.warn("QR decode failed", e);
    } finally {
      this.decoding = false;
    }
  }

  _sendQR(bytes) {
    const { ctrl, shared } = this.sim;
    const n = Math.min(bytes.length, QR_BYTES);
    new Uint8Array(shared.qr).set(bytes.subarray(0, n));
    ctrl.set(C.QR_LEN, n);
    ctrl.add(C.QR_SEQ);
    ctrl.wake();
    this.lastQR = { size: n, at: Date.now() };
    this.onChange();
  }

  // ---------------------------------------------------------- previews

  // Any canvas can show the source and let the user draw the region on it
  // (the small preview in the panel and the large region picker).
  addView(canvas) {
    const view = { canvas, ctx: canvas.getContext("2d"), fit: null, drag: null };
    this.views.push(view);
    this._bindRegion(view);
    return view;
  }

  removeView(canvas) {
    this.views = this.views.filter((v) => v.canvas !== canvas);
  }

  _drawPreview(src) {
    for (const view of this.views) this._drawView(view, src);
  }

  _drawView(view, src) {
    const c = view.canvas;
    if (!c.isConnected || !c.clientWidth) return;
    const dpr = window.devicePixelRatio || 1;
    const bw = Math.round(c.clientWidth * dpr), bh = Math.round(c.clientHeight * dpr);
    if (bw && bh && (c.width !== bw || c.height !== bh)) {
      c.width = bw;
      c.height = bh;
    }
    const g = view.ctx;
    g.clearRect(0, 0, c.width, c.height);
    if (!src) return;
    const [el, sw, sh] = src;
    const s = Math.min(c.width / sw, c.height / sh);
    const f = { w: sw * s, h: sh * s };
    f.x = (c.width - f.w) / 2;
    f.y = (c.height - f.h) / 2;
    view.fit = f;
    g.drawImage(el, f.x, f.y, f.w, f.h);
    const r = view.drag || this.region;
    if (r) {
      const x = f.x + r.x * f.w, y = f.y + r.y * f.h, w = r.w * f.w, h = r.h * f.h;
      g.save();
      g.fillStyle = "rgba(10, 24, 20, 0.62)";
      g.beginPath();
      g.rect(f.x, f.y, f.w, f.h);
      g.rect(x, y, w, h);
      g.fill("evenodd");
      g.strokeStyle = "#f2b33d";
      g.lineWidth = 2 * dpr;
      g.strokeRect(x, y, w, h);
      g.restore();
    }
  }

  _bindRegion(view) {
    const c = view.canvas;
    let start = null;
    const toNorm = (e) => {
      const f = view.fit;
      if (!f) return null;
      const rect = c.getBoundingClientRect();
      const k = c.width / rect.width;
      const px = (e.clientX - rect.left) * k, py = (e.clientY - rect.top) * k;
      return {
        x: Math.min(1, Math.max(0, (px - f.x) / f.w)),
        y: Math.min(1, Math.max(0, (py - f.y) / f.h)),
      };
    };
    c.addEventListener("pointerdown", (e) => {
      if (!this.active) return;
      start = toNorm(e);
      if (!start) return;
      e.preventDefault();
      c.setPointerCapture(e.pointerId);
      view.drag = null;
    });
    c.addEventListener("pointermove", (e) => {
      if (!start) return;
      const p = toNorm(e);
      view.drag = {
        x: Math.min(start.x, p.x), y: Math.min(start.y, p.y),
        w: Math.abs(p.x - start.x), h: Math.abs(p.y - start.y),
      };
    });
    const end = () => {
      if (!start) return;
      start = null;
      const r = view.drag;
      view.drag = null;
      if (r && r.w > 0.01 && r.h > 0.01) {
        this.region = r;
        this.onChange("region");
      }
    };
    c.addEventListener("pointerup", end);
    c.addEventListener("pointercancel", end);
  }
}
