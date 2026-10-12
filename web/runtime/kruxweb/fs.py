# Krux Web Simulator - SD card / flash persistence.
#
# The page keeps the simulated SD card and flash in browser storage (and,
# optionally, mirrors the SD card to a real folder). Here we:
#   * report file changes under sd/ and flash/ to the page (periodic scan);
#   * apply file operations the page queues in the shared "inbox"
#     (files added/removed through the UI while Krux is running).
import os
import struct
import time

from . import bridge

ROOTS = ("sd", "flash")
SCAN_INTERVAL = 0.75

_snapshot = {}
_last_scan = 0.0
_inbox = None


def _walk():
    out = {}
    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                p = os.path.join(dirpath, name)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                out[p] = (st.st_mtime_ns, st.st_size)
    return out


def scan(force=False):
    global _snapshot, _last_scan
    now = time.monotonic()
    if not force and now - _last_scan < SCAN_INTERVAL:
        return
    _last_scan = now
    cur = _walk()
    for p, sig in cur.items():
        if _snapshot.get(p) != sig:
            try:
                with open(p, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            bridge.post_file(p, data)
    for p in _snapshot:
        if p not in cur:
            bridge.post("fs-delete", path=p)
    _snapshot = cur


def _apply_inbox():
    seq = bridge.load(bridge.INBOX_SEQ)
    if seq == bridge.load(bridge.INBOX_ACK):
        return
    n = bridge.load(bridge.INBOX_LEN)
    raw = bridge.read_inbox(n)
    # [u8 op][u16 path_len][path][data...]   op: 1=write 2=delete
    op = raw[0]
    plen = struct.unpack_from("<H", raw, 1)[0]
    path = raw[3 : 3 + plen].decode()
    data = raw[3 + plen :]
    path = path.lstrip("/")
    if path.split("/")[0] in ROOTS and ".." not in path.split("/"):
        try:
            if op == 1:
                d = os.path.dirname(path)
                if d:
                    os.makedirs(d, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(data)
            elif op == 2 and os.path.exists(path):
                os.remove(path)
        except OSError as e:
            print("inbox:", e)
    # the page already knows about this change
    global _snapshot
    _snapshot = _walk()
    bridge.store(bridge.INBOX_ACK, seq)
    bridge.add(bridge.WAKE)


def hook():
    _apply_inbox()
    scan()


def install():
    global _snapshot
    for root in ROOTS:
        os.makedirs(root, exist_ok=True)
    _snapshot = _walk()
    bridge.add_hook(hook)
