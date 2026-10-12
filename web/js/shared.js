// Shared-memory layout between the page and the Krux worker.
// Keep the indices in sync with runtime/kruxweb/bridge.py.
export const C = {
  WAKE: 0, KEYS: 1, EV_ENTER: 2, EV_PAGE: 3, EV_PREV: 4,
  MOUSE_DOWN: 5, MOUSE_X: 6, MOUSE_Y: 7, EV_TOUCH: 8, TOUCH_X: 9, TOUCH_Y: 10,
  FRAME_SEQ: 11, CAM_SEQ: 12, CAM_ON: 13, QR_SEQ: 14, QR_LEN: 15,
  INBOX_SEQ: 16, INBOX_LEN: 17, INBOX_ACK: 18, CAM_W: 19, CAM_H: 20,
  LCD_W: 21, LCD_H: 22, INPUT_POLLS: 23,
};
export const KEY = { ENTER: 1, DOWN: 2, UP: 4 };

export const FB_BYTES = 480 * 480 * 4;
export const CAM_W = 240;
export const CAM_H = 320;
export const QR_BYTES = 64 * 1024;
export const INBOX_BYTES = 16 * 1024 * 1024;

export function createShared() {
  return {
    ctrl: new SharedArrayBuffer(64 * 4),
    fb: new SharedArrayBuffer(FB_BYTES),
    cam: new SharedArrayBuffer(CAM_W * CAM_H * 4),
    qr: new SharedArrayBuffer(QR_BYTES),
    inbox: new SharedArrayBuffer(INBOX_BYTES),
  };
}

// Page-side helpers -------------------------------------------------------

export class Ctrl {
  constructor(shared) {
    this.i32 = new Int32Array(shared.ctrl);
  }
  get(i) { return Atomics.load(this.i32, i); }
  set(i, v) { Atomics.store(this.i32, i, v); }
  add(i, v = 1) { return Atomics.add(this.i32, i, v); }
  wake() {
    Atomics.add(this.i32, C.WAKE, 1);
    Atomics.notify(this.i32, C.WAKE);
  }
}
