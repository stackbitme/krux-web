"""Renders text and shapes with the web simulator's Python renderer and with
pygame (what Krux's desktop simulator uses) and checks they are identical.

Run with the Python of Krux's simulator environment (it has pygame):
    KRUX_DIR=../krux $KRUX_DIR/.venv/bin/python tests/test_render_vs_pygame.py
"""
import glob
import json
import os
import random
import re
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "web", "runtime"))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import pygame as pg  # noqa: E402
import bdffont  # noqa: E402
from kruxweb.fb import Framebuffer  # noqa: E402
from kruxweb.font import Font  # noqa: E402

KRUX = os.environ.get("KRUX_DIR", os.path.join(HERE, "..", "..", "krux"))
pg.init()
pg.freetype.init()
failures = 0

# --- text, every string of every translation
strings = {"₿ 1", "x₿x", "Ơ", "", " ", "Load Mnemonic"}
for f in glob.glob(os.path.join(KRUX, "src", "krux", "translations", "*.py")):
    for m in re.findall(r'"((?:[^"\\]|\\.)*)"', open(f, encoding="utf-8").read()):
        try:
            strings.add(json.loads('"%s"' % m).split("\n")[0][:40])
        except ValueError:
            pass
colors = [((255, 255, 255), (0, 0, 0)), ((0, 0, 0), (255, 255, 255)), ((255, 128, 0), (10, 20, 30))]
tmp = tempfile.mkdtemp()
for name in ["ter-u24b", "ter-u16n", "ter-u14n"]:
    bdf = os.path.join(KRUX, "firmware", "font", name + ".bdf")
    kpath = os.path.join(tmp, name + ".kfnt")
    bdffont.write_kfnt(bdf, kpath)
    pf, kf = pg.freetype.Font(bdf), Font(open(kpath, "rb").read())
    bad = n = 0
    for s in sorted(strings):
        if any(0x3000 <= ord(c) <= 0x9FFF or 0xAC00 <= ord(c) <= 0xD7A3 for c in s):
            continue
        fg, bg = colors[n % 3]
        n += 1
        ps, _ = pf.render(s, fg, bg)
        ks = kf.render(s, fg, bg)
        if ps.get_size() != (ks.width, ks.height) or pg.image.tobytes(ps, "RGBA") != bytes(ks.buf):
            bad += 1
    print("%-10s %d strings, %d different" % (name, n, bad))
    failures += bad

# --- drawing primitives
rnd = random.Random(5)
bad = {}
for trial in range(400):
    surf = pg.Surface((320, 480))
    surf.fill((0, 0, 0))
    fb = Framebuffer(320, 480)
    c = (rnd.randint(1, 255), rnd.randint(0, 255), rnd.randint(0, 255))
    kind = trial % 4
    if kind == 0:
        cx, cy, r = rnd.randint(-20, 340), rnd.randint(-20, 500), rnd.randint(0, 60)
        pg.draw.circle(surf, c, (cx, cy), r)
        fb.draw_circle(c, (cx, cy), r)
    elif kind == 1:
        p1 = (rnd.randint(-300, 650), rnd.randint(-300, 800))
        p2 = (rnd.randint(-300, 650), rnd.randint(-300, 800))
        pg.draw.line(surf, c, p1, p2, 1)
        fb.draw_line(c, p1, p2)
    else:
        x, y, w, h = rnd.randint(-20, 330), rnd.randint(-20, 490), rnd.randint(-5, 200), rnd.randint(-5, 200)
        width = 1 if kind == 2 else 0
        pg.draw.rect(surf, c, (x, y, w, h), width)
        fb.draw_rect(c, x, y, w, h, width)
    mine = bytes(b for i, b in enumerate(fb.buf) if i % 4 != 3)
    if pg.image.tobytes(surf, "RGB") != mine:
        bad[kind] = bad.get(kind, 0) + 1
print("primitives (circle, line, outline, fill): %s" % (bad or "all identical"))
failures += sum(bad.values())
sys.exit(1 if failures else 0)
