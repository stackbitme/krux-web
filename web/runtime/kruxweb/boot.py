# Krux Web Simulator - startup, mirroring simulator/simulator.py from Krux
# but with the browser-backed mocks (kruxweb.mocks) in place of the pygame /
# OpenCV / pyzbar ones. Krux's own code (src/) is not modified.
import builtins
import hashlib
import os
import sys
import time
import traceback
import _thread

import _kxio
from pyodide.ffi import to_js

from . import bridge


def _pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
    if isinstance(password, str):
        password = password.encode()
    if isinstance(salt, str):
        salt = salt.encode()
    out = _kxio.pbkdf2(
        str(hash_name).lower(),
        to_js(bytes(password)),
        to_js(bytes(salt)),
        int(iterations),
        int(dklen or 0),
    )
    return out.to_bytes()


def _start_new_thread(fn, args, kwargs=None):
    # No threads in the browser: Krux only uses this to draw the battery
    # indicator, so run it right away.
    try:
        fn(*args, **(kwargs or {}))
    except Exception:
        traceback.print_exc()
    return 1


def _alias(name, module):
    sys.modules[name] = module
    pkg, _, attr = name.rpartition(".")
    if pkg in sys.modules:
        setattr(sys.modules[pkg], attr, module)


def start(device="maixpy_amigo", sd=True):
    os.chdir("/krux/simulator")
    for p in ("/krux/vendor", "/krux/simulator", "/krux/src"):
        if p not in sys.path:
            sys.path.insert(0, p)

    # Platform shims (hashlib without OpenSSL, no threads, cooperative sleep)
    hashlib.pbkdf2_hmac = _pbkdf2_hmac
    _thread.start_new_thread = _start_new_thread
    time.sleep = bridge.sleep
    time.sleep_ms = bridge.sleep_ms

    import kruxsim
    import kruxsim.mocks
    from .mocks import devices, events

    _alias("kruxsim.devices", devices)
    _alias("kruxsim.events", events)

    from kruxsim.mocks import board

    board.register_device(device)

    if sd:
        from kruxsim.mocks import uopen
        from kruxsim.mocks import uos

    from kruxsim.mocks import uos_functions
    from kruxsim.mocks import ujson
    from kruxsim.mocks import urandom
    from kruxsim.mocks import usys
    from kruxsim.mocks import utime
    from kruxsim.mocks import fpioa_manager

    from .mocks import Maix

    _alias("kruxsim.mocks.Maix", Maix)
    from kruxsim.mocks import flash
    from .mocks import lcd

    _alias("kruxsim.mocks.lcd", lcd)
    from .mocks import machine

    _alias("kruxsim.mocks.machine", machine)
    from kruxsim.mocks import image
    from .mocks import pmu

    _alias("kruxsim.mocks.pmu", pmu)
    from kruxsim.mocks import deflate
    from kruxsim.mocks import secp256k1
    from kruxsim.mocks import qrcode
    from .mocks import sensor

    _alias("kruxsim.mocks.sensor", sensor)
    from kruxsim.mocks import shannon
    from .mocks import touchscreen_common

    _alias("kruxsim.mocks.touchscreen_common", touchscreen_common)
    from kruxsim.mocks import ft6x36
    from kruxsim.mocks import gt911
    from kruxsim.mocks import cst816
    from .mocks import buttons

    _alias("kruxsim.mocks.buttons", buttons)
    from kruxsim.mocks import rotary
    from kruxsim.mocks import uhashlib_hw
    from kruxsim.mocks import baseconv

    from . import fs

    if sd:
        from krux.settings import SD_PATH

        os.makedirs(SD_PATH, exist_ok=True)
        from kruxsim.mocks import sd_card
    fs.install()

    if device == devices.PC:
        board.BOARD_CONFIG["type"] = "amigo"

    bridge.post("booting", device=device)
    status = "exit"
    try:
        with open("../src/boot.py", "r", encoding="utf-8") as boot_file:
            code = compile(boot_file.read(), "/krux/src/boot.py", "exec")
        exec(code, {"__name__": "__main__", "__file__": "/krux/src/boot.py"})
    except SystemExit:
        status = "exit"
    except BaseException:
        status = "crash"
        tb = traceback.format_exc()
        print(tb)
        bridge.post("crash", traceback=tb)
    finally:
        try:
            fs.scan(force=True)
        except Exception:
            traceback.print_exc()
        bridge.flush(force=True)
    return status
