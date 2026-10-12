"""Compares web-simulator LCD screenshots with the official simulator's."""
import os
import sys

from PIL import Image, ImageChops


def compare(ref_dir, web_dir, diff_dir=None):
    results = []
    for name in sorted(os.listdir(ref_dir)):
        if not name.endswith(".png"):
            continue
        rp, wp = os.path.join(ref_dir, name), os.path.join(web_dir, name)
        if not os.path.exists(wp):
            results.append((name, "missing", None))
            continue
        a = Image.open(rp).convert("RGB")
        b = Image.open(wp).convert("RGB")
        if a.size != b.size:
            results.append((name, "size %s vs %s" % (a.size, b.size), None))
            continue
        d = ImageChops.difference(a, b)
        bbox = d.getbbox()
        n = sum(1 for px in d.getdata() if px != (0, 0, 0))
        results.append((name, n, bbox))
        if n and diff_dir:
            os.makedirs(diff_dir, exist_ok=True)
            w, h = a.size
            strip = Image.new("RGB", (w * 3 + 20, h), (80, 0, 80))
            strip.paste(a, (0, 0))
            strip.paste(b, (w + 10, 0))
            strip.paste(d.point(lambda v: 255 if v else 0), (2 * w + 20, 0))
            strip.save(os.path.join(diff_dir, name))
    return results


if __name__ == "__main__":
    res = compare(*sys.argv[1:4])
    for name, n, bbox in res:
        print("%-45s %s %s" % (name, "IDENTICAL" if n == 0 else n, bbox or ""))
