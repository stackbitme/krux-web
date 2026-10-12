# Krux Web Simulator - `sensor` (camera) mock.
#
# The page captures the webcam (or a shared screen/window/tab, or a pasted
# image), crops it to 3:4 and scales it to 240x320 exactly like the desktop
# simulator does with OpenCV, and decodes QR codes with zbar (wasm). Frames
# and decoded payloads arrive through shared memory (see kruxweb.bridge).
import sys
import math
from unittest import mock

from .. import bridge
from ..fb import Surface

THREAD_DROP_PERIOD = 0.01

sequence_executor = None
_last_qr_seq = None
_last_cam_seq = None
_last_frame = None


def register_sequence_executor(s):
    global sequence_executor
    sequence_executor = s


def _srgb_to_lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


_LIN = [_srgb_to_lin(i) for i in range(256)]


def _f(t):
    return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0


def _std(values):
    n = len(values)
    if not n:
        return 0.0
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / n)


class MockStatistics:
    """openMV statistics over the frame in 8-bit LAB (like cv2.COLOR_BGR2LAB),
    computed on a subsample of the pixels."""

    def __init__(self, frame):
        L, A, B = [], [], []
        buf = frame.buf
        w, h = frame.width, frame.height
        lin = _LIN
        for y in range(0, h, 4):
            row = y * w * 4
            for x in range(0, w, 4):
                o = row + x * 4
                r, g, b = lin[buf[o]], lin[buf[o + 1]], lin[buf[o + 2]]
                X = (0.412453 * r + 0.357580 * g + 0.180423 * b) / 0.950456
                Y = 0.212671 * r + 0.715160 * g + 0.072169 * b
                Z = (0.019334 * r + 0.119193 * g + 0.950227 * b) / 1.088754
                fy = _f(Y)
                l_ = 116.0 * fy - 16.0 if Y > 0.008856 else 903.3 * Y
                L.append(l_ * 255.0 / 100.0)
                A.append(500.0 * (_f(X) - fy) + 128.0)
                B.append(200.0 * (fy - _f(Z)) + 128.0)
        self.std_L = _std(L)
        self.std_a = _std(A)
        self.std_b = _std(B)

    def l_stdev(self):
        return self.std_L

    def a_stdev(self):
        return self.std_a

    def b_stdev(self):
        return self.std_b

    def median(self):
        return 10


class Mockqrcode:
    def __init__(self, data):
        self.data = data

    def payload(self):
        return self.data


def _payload_text(data):
    # pyzbar returns the bytes zbar produced and the desktop simulator calls
    # .decode() on them; zbar turns binary (non UTF-8) QR data into text by
    # mapping each byte to a Latin-1 character, which Krux then reverses in
    # qr_str_to_bytes().
    try:
        return data.decode()
    except UnicodeDecodeError:
        return data.decode("latin-1")


def reset(freq=None, dual_buff=False):
    pass


def run(on):
    global _last_qr_seq
    if on:
        # Only QR codes decoded from now on count
        _last_qr_seq = bridge.load(bridge.QR_SEQ)
    bridge.camera(on)


def _frame():
    """Latest camera frame as a 240x320 Surface (black until one arrives)."""
    global _last_cam_seq, _last_frame
    seq = bridge.load(bridge.CAM_SEQ)
    if seq != _last_cam_seq or _last_frame is None:
        _, w, h, data = bridge.read_camera()
        if w and h:
            _last_frame = Surface(w, h, bytearray(data))
        else:
            _last_frame = Surface(240, 320)
        _last_cam_seq = seq
    return _last_frame


def find_qrcodes(img=None):
    global _last_qr_seq
    seq, data = bridge.read_qr()
    if _last_qr_seq is None:
        _last_qr_seq = seq
        return []
    if seq != _last_qr_seq:
        _last_qr_seq = seq
        if data:
            return [Mockqrcode(_payload_text(data))]
    return []


def snapshot():
    # Wait a little for the next frame (like the desktop THREAD_DROP_PERIOD)
    bridge.sleep(THREAD_DROP_PERIOD)

    frame = _frame()
    m = mock.MagicMock()
    m.get_frame.return_value = frame
    m.find_qrcodes.return_value = find_qrcodes()

    def to_bytes():
        buf = frame.buf
        out = bytearray(frame.width * frame.height * 3)
        out[0::3] = buf[2::4]  # BGR, like the OpenCV frame
        out[1::3] = buf[1::4]
        out[2::3] = buf[0::4]
        return bytes(out)

    m.to_bytes.side_effect = to_bytes
    m.get_statistics.side_effect = lambda *a, **k: MockStatistics(frame)
    m.width.return_value = frame.width
    m.height.return_value = frame.height
    m.lens_corr.return_value = m
    return m


if "sensor" not in sys.modules:
    sys.modules["sensor"] = mock.MagicMock(
        reset=reset,
        run=run,
        snapshot=snapshot,
    )
