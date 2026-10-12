# Krux Web Simulator - bitmap font renderer (.kfnt, see tools/bdffont.py)
# reproducing pygame.freetype's output for the BDF fonts the desktop
# simulator uses: glyph boxes (BBX) are laid out on a common baseline and the
# rendered surface is the union of all boxes, filled with the background.

import struct
from bisect import bisect_left

from .fb import Surface, _px


class Font:
    def __init__(self, data):
        if data[:4] != b"KFN2":
            raise ValueError("not a KFN2 font")
        self.cell_w, self.cell_h, self.ascent, default, count = struct.unpack_from(
            "<HHHII", data, 4
        )
        self._data = data
        self._base = 4 + struct.calcsize("<HHHII")
        self._rec = struct.Struct("<IBBbbBBI")
        self._count = count
        self._blob = self._base + self._rec.size * count
        # sorted codepoint table for lookups (glyphs are decoded lazily)
        step = self._rec.size
        self._cps = [
            struct.unpack_from("<I", data, self._base + i * step)[0]
            for i in range(count)
        ]
        self._glyphs = {}
        self.default = self._lookup(default)
        self._cache = {}

    def _lookup(self, cp):
        g = self._glyphs.get(cp)
        if g is not None or cp in self._glyphs:
            return g
        i = bisect_left(self._cps, cp)
        if i >= self._count or self._cps[i] != cp:
            self._glyphs[cp] = None
            return None
        _, w, h, xoff, yoff, dw, _, off = self._rec.unpack_from(
            self._data, self._base + i * self._rec.size
        )
        bpr = (w + 7) // 8
        rows = []
        o = self._blob + off
        data = self._data
        for r in range(h):
            rows.append(int.from_bytes(data[o : o + bpr], "big"))
            o += bpr
        g = (w, h, xoff, yoff, dw, bpr * 8, rows)
        self._glyphs[cp] = g
        return g

    def glyph(self, ch):
        g = self._lookup(ord(ch))
        return g if g is not None else self.default

    def render(self, text, color, bgcolor):
        """Equivalent of pygame.freetype.Font.render(text, color, bgcolor)[0]."""
        key = (text, color, bgcolor)
        surf = self._cache.get(key)
        if surf is not None:
            return surf
        surf = self._render(text, color, bgcolor)
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[key] = surf
        return surf

    def _render(self, text, color, bgcolor):
        placed = []
        pen = 0
        min_x = min_y = None
        max_x = max_y = None
        asc = self.ascent
        for ch in text:
            g = self.glyph(ch)
            if g is None:
                continue
            w, h, xoff, yoff, dw, nbits, rows = g
            left = pen + xoff
            top = asc - (yoff + h)
            placed.append((left, top, g))
            if min_x is None:
                min_x, min_y, max_x, max_y = left, top, left + w, top + h
            else:
                min_x = min(min_x, left)
                min_y = min(min_y, top)
                max_x = max(max_x, left + w)
                max_y = max(max_y, top + h)
            pen += dw
        if min_x is None:
            return Surface(0, self.cell_h, fill=bgcolor)
        sw, sh = max_x - min_x, max_y - min_y
        surf = Surface(sw, sh, fill=bgcolor)
        buf = surf.buf
        fg = _px(color)
        stride = sw * 4
        for left, top, (w, h, xoff, yoff, dw, nbits, rows) in placed:
            gx = left - min_x
            gy = top - min_y
            for r in range(h):
                bits = rows[r]
                if not bits:
                    continue
                o = (gy + r) * stride + gx * 4
                for c in range(w):
                    if bits >> (nbits - 1 - c) & 1:
                        p = o + c * 4
                        buf[p : p + 4] = fg
        return surf
