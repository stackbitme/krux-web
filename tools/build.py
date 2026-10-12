#!/usr/bin/env python3
"""Builds the files the web simulator needs for one Krux version.

    python3 tools/build.py --krux /path/to/krux --tag v26.09.0

<krux> must be a checkout of https://github.com/selfcustody/krux at <tag>,
cloned with --recurse-submodules (embit and the bc-ur sources are submodules).
Nothing in the Krux checkout is modified.

Outputs (under web/):
    runtime.zip                     the simulator runtime (Python mocks, uUR shim)
    versions/<tag>/krux.zip         Krux src/, kruxsim, board configs, embit, pyqrcode
    versions/<tag>/ur.wasm          Krux's bc-ur C library compiled to wasm
    versions/<tag>/fonts/*.kfnt     Krux's BDF fonts converted (+ licenses)
    versions/<tag>/assets/*.png     device frame images from the simulator
    versions/<tag>/manifest.json    devices available in this version
    versions/index.json             list of built versions
"""
import argparse
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")
sys.path.insert(0, HERE)
import bdffont  # noqa: E402

# Devices enabled in the launcher. The simulator already knows all of them;
# start with the Amigo and add more once they are verified.
ENABLED_DEVICES = ["maixpy_amigo"]

DEVICE_INFO = {
    "maixpy_amigo": {"name": "Maix Amigo", "window": [480, 768], "touch": True},
    "maixpy_m5stickv": {"name": "M5StickV", "window": [320, 640], "touch": False},
    "maixpy_dock": {"name": "Maix Dock", "window": [440, 820], "touch": False},
    "maixpy_yahboom": {"name": "Yahboom", "window": [450, 600], "touch": True},
    "maixpy_cube": {"name": "Maix Cube", "window": [484, 612], "touch": False},
    "maixpy_wonder_mv": {"name": "WonderMV", "window": [410, 590], "touch": True},
    "maixpy_tzt": {"name": "TZT", "window": [410, 580], "touch": True},
    "maixpy_embed_fire": {"name": "Embed Fire", "window": [500, 671], "touch": True},
}

FONTS = ["ter-u24b", "ter-u16n", "ter-u14n", "NotoSansCJK-24", "unifont-16", "FusionPixel-14"]
PYQRCODE_VERSION = "1.2.1"

SKIP_DIRS = {"__pycache__", ".git", "tests", "test"}


def add_tree(zf, src_dir, arc_prefix, exts=(".py",)):
    n = 0
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if exts and not name.endswith(exts):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, src_dir)
            zf.write(full, os.path.join(arc_prefix, rel))
            n += 1
    return n


def fetch_pyqrcode(cache_dir):
    """Pure-Python pyqrcode (BSD) from PyPI; Krux's qrcode mock needs it."""
    dest = os.path.join(cache_dir, "pyqrcode-%s" % PYQRCODE_VERSION)
    if os.path.isdir(dest):
        return dest
    os.makedirs(cache_dir, exist_ok=True)
    tmp = tempfile.mkdtemp()
    subprocess.check_call(
        [sys.executable, "-m", "pip", "download", "--no-deps", "--no-binary", ":all:",
         "-d", tmp, "pyqrcode==%s" % PYQRCODE_VERSION],
        stdout=subprocess.DEVNULL,
    )
    archive = glob.glob(os.path.join(tmp, "*"))[0]
    shutil.unpack_archive(archive, tmp)
    src = glob.glob(os.path.join(tmp, "PyQRCode-*", "pyqrcode"))[0]
    shutil.copytree(src, os.path.join(dest, "pyqrcode"))
    lic = glob.glob(os.path.join(tmp, "PyQRCode-*", "LICENSE*"))
    if lic:
        shutil.copy(lic[0], os.path.join(dest, "LICENSE"))
    return dest


def build_runtime():
    out = os.path.join(WEB, "runtime.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        n = add_tree(zf, os.path.join(WEB, "runtime"), "")
    print("runtime.zip: %d files" % n)


def build_version(krux, tag):
    out = os.path.join(WEB, "versions", tag)
    os.makedirs(out, exist_ok=True)

    # --- Krux python sources and simulator mocks
    cache = os.path.join(ROOT, ".cache")
    pyq = fetch_pyqrcode(cache)
    zpath = os.path.join(out, "krux.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(krux, "src", "boot.py"), "src/boot.py")
        n = add_tree(zf, os.path.join(krux, "src", "krux"), "src/krux")
        n += add_tree(zf, os.path.join(krux, "simulator", "kruxsim"), "simulator/kruxsim")
        for board in glob.glob(os.path.join(krux, "firmware", "MaixPy", "projects", "*", "builtin_py", "board.py")):
            rel = os.path.relpath(board, krux)
            zf.write(board, rel)
            n += 1
        n += add_tree(zf, os.path.join(krux, "vendor", "embit", "src", "embit"), "vendor/embit",
                      exts=(".py", ".txt", ".json"))
        n += add_tree(zf, os.path.join(pyq, "pyqrcode"), "vendor/pyqrcode")
        zf.write(os.path.join(krux, "LICENSE.md"), "LICENSE-krux.md")
    print("krux.zip: %d files, %d KB" % (n, os.path.getsize(zpath) // 1024))

    # --- bc-ur -> wasm
    subprocess.check_call(
        [os.path.join(ROOT, "native", "urwasm", "build.sh"), krux, os.path.join(out, "ur.wasm")],
        stderr=subprocess.DEVNULL,
    )

    # --- fonts
    fdir = os.path.join(out, "fonts")
    os.makedirs(fdir, exist_ok=True)
    fsrc = os.path.join(krux, "firmware", "font")
    for name in FONTS:
        bdffont.write_kfnt(os.path.join(fsrc, name + ".bdf"), os.path.join(fdir, name + ".kfnt"))
    for lic in glob.glob(os.path.join(fsrc, "*OFL*")) + glob.glob(os.path.join(fsrc, "README.md")):
        shutil.copy(lic, fdir)
    print("fonts: %d" % len(FONTS))

    # --- device images and manifest
    adir = os.path.join(out, "assets")
    os.makedirs(adir, exist_ok=True)
    devices = []
    for dev in ENABLED_DEVICES:
        img = os.path.join(krux, "simulator", "assets", dev + ".png")
        if os.path.exists(img):
            shutil.copy(img, adir)
        board_py = os.path.join(krux, "firmware", "MaixPy", "projects", dev, "builtin_py", "board.py")
        if not os.path.exists(board_py):
            continue
        info = dict(DEVICE_INFO[dev])
        info["id"] = dev
        info["image"] = "assets/%s.png" % dev if os.path.exists(img) else None
        devices.append(info)
    langs = ["en-US"]
    tr = os.path.join(krux, "src", "krux", "translations", "__init__.py")
    if os.path.exists(tr):
        import re

        m = re.search(r"available_languages\s*=\s*\[(.*?)\]", open(tr, encoding="utf-8").read(), re.S)
        if m:
            langs += re.findall(r'"([a-z]{2}-[A-Z]{2})"', m.group(1))
    manifest = {"version": tag, "devices": devices, "default_device": devices[0]["id"],
                "languages": langs}
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # --- versions index
    idx_path = os.path.join(WEB, "versions", "index.json")
    idx = {"versions": []}
    if os.path.exists(idx_path):
        with open(idx_path) as f:
            idx = json.load(f)
    idx["versions"] = [v for v in idx["versions"] if v["tag"] != tag]
    idx["versions"].append({"tag": tag, "devices": [d["id"] for d in devices]})
    idx["versions"].sort(key=lambda v: [int(x) if x.isdigit() else x
                                        for x in v["tag"].lstrip("v").split(".")], reverse=True)
    idx["default"] = idx["versions"][0]["tag"]
    with open(idx_path, "w") as f:
        json.dump(idx, f, indent=2)
    print("versions:", [v["tag"] for v in idx["versions"]])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--krux", help="path to the Krux checkout (at --tag)")
    ap.add_argument("--tag", help="Krux version tag, e.g. v26.09.0")
    ap.add_argument("--runtime-only", action="store_true")
    args = ap.parse_args()
    build_runtime()
    if args.runtime_only:
        return
    if not args.krux or not args.tag:
        ap.error("--krux and --tag are required")
    build_version(os.path.abspath(args.krux), args.tag)


if __name__ == "__main__":
    main()
