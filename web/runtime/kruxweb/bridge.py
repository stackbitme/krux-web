# Krux Web Simulator - bridge between the Python side (Pyodide, running in a
# Web Worker) and the page (main thread).
#
# Krux runs as a blocking program, so the worker never returns to its event
# loop while Krux is running. All page -> worker communication therefore goes
# through SharedArrayBuffers (read here by polling), and sleeps use
# Atomics.wait so they wake up early when the page signals new input.
# worker -> page messages use postMessage (delivered even while blocked).

import time as _time

import _kxio as _io
from js import Object as _Object
from pyodide.ffi import to_js as _to_js

# Indices into the shared Int32Array `ctrl` (keep in sync with js/shared.js)
WAKE = 0
KEYS = 1
EV_ENTER = 2
EV_PAGE = 3
EV_PREV = 4
MOUSE_DOWN = 5
MOUSE_X = 6
MOUSE_Y = 7
EV_TOUCH = 8
TOUCH_X = 9
TOUCH_Y = 10
FRAME_SEQ = 11
CAM_SEQ = 12
CAM_ON = 13
QR_SEQ = 14
QR_LEN = 15
INBOX_SEQ = 16
INBOX_LEN = 17
INBOX_ACK = 18
CAM_W = 19
CAM_H = 20
LCD_W = 21
LCD_H = 22
INPUT_POLLS = 23  # incremented whenever Krux polls for input

KEY_ENTER = 1
KEY_DOWN = 2
KEY_UP = 4

_ctrl = _io.ctrl
_atomics_load = _io.load
_atomics_store = _io.store
_atomics_add = _io.add

FLUSH_INTERVAL = 1.0 / 60

_fb = None  # kruxweb.fb.Framebuffer, set by lcd mock
_fb_js = None  # matching view into the shared framebuffer
_last_flush = 0.0
_inbox_seen = 0
_hooks = []  # callables run at every poll point (inbox, fs sync...)


def load(i):
    return _atomics_load(i)


def store(i, v):
    _atomics_store(i, v)


def add(i, v=1):
    return _atomics_add(i, v)


def post(kind, **data):
    """Sends a message to the page (non-blocking)."""
    data["kind"] = kind
    _io.post(_to_js(data, dict_converter=_Object.fromEntries))


def set_framebuffer(fb):
    global _fb, _fb_js
    _fb = fb
    _fb_js = _io.fb.subarray(0, len(fb.buf))
    store(LCD_W, fb.width)
    store(LCD_H, fb.height)
    post("lcd", width=fb.width, height=fb.height)


def flush(force=False):
    """Publishes the framebuffer to the page if it changed (rate limited)."""
    global _last_flush
    fb = _fb
    if fb is None or not fb.dirty:
        return
    now = _time.monotonic()
    if not force and now - _last_flush < FLUSH_INTERVAL:
        return
    _last_flush = now
    fb.dirty = False
    _fb_js.assign(fb.buf)
    add(FRAME_SEQ)


def poll():
    """Called at every point where Krux polls input or sleeps."""
    flush()
    for h in _hooks:
        h()


def sleep_ms(ms):
    """Sleeps for `ms` milliseconds, waking up early on page input."""
    flush(force=True)
    for h in _hooks:
        h()
    if ms <= 0:
        return
    deadline = _time.monotonic() + ms / 1000.0
    while True:
        remaining = deadline - _time.monotonic()
        if remaining <= 0:
            return
        seen = load(WAKE)
        _io.wait(seen, min(remaining * 1000.0, 50.0))
        flush()


def sleep(seconds):
    sleep_ms(seconds * 1000.0)


class EventCounter:
    """Turns a page-side counter into consumable events."""

    def __init__(self, index):
        self.index = index
        self.seen = load(index)

    def take(self):
        poll()
        _atomics_add(INPUT_POLLS, 1)
        v = load(self.index)
        if v != self.seen:
            self.seen = v
            return True
        return False

    def clear(self):
        self.seen = load(self.index)


def key_pressed(mask):
    poll()
    return bool(load(KEYS) & mask)


def mouse():
    """Returns (x, y) in LCD coordinates if the pointer is pressed, else None."""
    poll()
    if not load(MOUSE_DOWN):
        return None
    return load(MOUSE_X), load(MOUSE_Y)


def touch_point():
    return load(TOUCH_X), load(TOUCH_Y)


def read_qr():
    """Returns the last decoded QR payload bytes and its sequence number."""
    seq = load(QR_SEQ)
    n = load(QR_LEN)
    data = _io.qr.subarray(0, n).to_bytes() if n else b""
    return seq, data


def read_camera():
    """Returns (seq, width, height, rgba bytes) of the latest camera frame."""
    seq = load(CAM_SEQ)
    w = load(CAM_W)
    h = load(CAM_H)
    if not w or not h:
        return seq, 0, 0, b""
    return seq, w, h, _io.cam.subarray(0, w * h * 4).to_bytes()


def post_file(path, data):
    _io.postFile(path, _to_js(data))


def read_inbox(n):
    return _io.inbox.subarray(0, n).to_bytes()


def camera(on):
    store(CAM_ON, 1 if on else 0)
    post("camera", on=bool(on))


def add_hook(fn):
    _hooks.append(fn)
