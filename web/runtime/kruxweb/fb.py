# Krux Web Simulator - RGBA framebuffer with the drawing primitives the
# desktop simulator gets from pygame, reproduced pixel for pixel
# (pygame 2.6 draw.c: draw_line, draw_circle_filled, draw_rect, FillRect).


def _px(color):
    r, g, b = color[0], color[1], color[2]
    return bytes((r, g, b, 255))


class Framebuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.stride = width * 4
        self.buf = bytearray(b"\x00\x00\x00\xff" * (width * height))
        self.dirty = True

    # ------------------------------------------------------------ basics

    def fill(self, color):
        self.buf[:] = _px(color) * (self.width * self.height)
        self.dirty = True

    def fill_rect(self, x, y, w, h, color):
        """SDL_FillRect clipped to the surface (pygame.draw.rect width=0)."""
        if w <= 0 or h <= 0:
            return
        x0 = max(x, 0)
        y0 = max(y, 0)
        x1 = min(x + w, self.width)
        y1 = min(y + h, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        row = _px(color) * (x1 - x0)
        buf = self.buf
        stride = self.stride
        start = y0 * stride + x0 * 4
        n = (x1 - x0) * 4
        for yy in range(y1 - y0):
            o = start + yy * stride
            buf[o : o + n] = row
        self.dirty = True

    def set_pixel(self, x, y, px):
        if 0 <= x < self.width and 0 <= y < self.height:
            o = y * self.stride + x * 4
            self.buf[o : o + 4] = px
            self.dirty = True

    def hline(self, x1, y, x2, px):
        """drawhorzlineclip: inclusive x range, clipped."""
        if y < 0 or y >= self.height:
            return
        if x1 > x2:
            x1, x2 = x2, x1
        x1 = max(x1, 0)
        x2 = min(x2, self.width - 1)
        if x1 > x2:
            return
        o = y * self.stride + x1 * 4
        self.buf[o : o + (x2 - x1 + 1) * 4] = px * (x2 - x1 + 1)
        self.dirty = True

    # ------------------------------------------------------- pygame draw

    def draw_rect(self, color, x, y, w, h, width=0):
        """pygame.draw.rect(surface, color, (x, y, w, h), width)."""
        # SDL_IntersectRect with the surface clip rect
        cx0, cy0 = max(x, 0), max(y, 0)
        cx1, cy1 = min(x + w, self.width), min(y + h, self.height)
        if w <= 0 or h <= 0 or cx0 >= cx1 or cy0 >= cy1:
            return
        cw, ch = cx1 - cx0, cy1 - cy0
        if width > 0 and width * 2 < cw and width * 2 < ch:
            px = _px(color)
            x1, y1, x2, y2 = x, y, x + w - 1, y + h - 1
            for i in range(width):
                self.hline(x1, y1 + i, x2, px)
                self.hline(x1, y2 - i, x2, px)
            for i in range((y2 - y1) - 2 * width + 1):
                self.hline(x1, y1 + width + i, x1 + width - 1, px)
                self.hline(x2 - width + 1, y1 + width + i, x2, px)
        else:
            self.fill_rect(cx0, cy0, cw, ch, color)

    def draw_circle(self, color, center, radius):
        """pygame.draw.circle filled (draw_circle_filled)."""
        x0, y0 = int(center[0]), int(center[1])
        radius = int(radius)
        if radius < 1:
            return
        if (
            x0 > self.width + radius
            or x0 < -radius
            or y0 > self.height + radius
            or y0 < -radius
        ):
            return
        px = _px(color)
        f = 1 - radius
        ddf_x = 0
        ddf_y = -2 * radius
        x = 0
        y = radius
        hline = self.hline
        while x < y:
            if f >= 0:
                y -= 1
                ddf_y += 2
                f += ddf_y
            x += 1
            ddf_x += 2
            f += ddf_x + 1
            if f >= 0:
                hline(x0 - x, y0 + y - 1, x0 + x - 1, px)
                hline(x0 - x, y0 - y, x0 + x - 1, px)
            hline(x0 - y, y0 + x - 1, x0 + y - 1, px)
            hline(x0 - y, y0 - x, x0 + y - 1, px)

    def draw_line(self, color, start, end):
        """pygame.draw.line width=1 (draw_line, per-pixel clipped)."""
        x1, y1 = int(start[0]), int(start[1])
        x2, y2 = int(end[0]), int(end[1])
        clipped = self._clip_line(x1, y1, x2, y2)
        if clipped is None:
            return
        x1, y1, x2, y2 = clipped
        px = _px(color)
        sp = self.set_pixel
        if x1 == x2 and y1 == y2:
            sp(x1, y1, px)
            return
        if y1 == y2:
            self.hline(x1, y1, x2, px)
            return
        if x1 == x2:
            step = 1 if y1 < y2 else -1
            for yy in range(y1, y2 + step, step):
                sp(x1, yy, px)
            return
        dx, sx = abs(x2 - x1), (1 if x1 < x2 else -1)
        dy, sy = abs(y2 - y1), (1 if y1 < y2 else -1)
        err = int((dx if dx > dy else -dy) / 2)
        while x1 != x2 or y1 != y2:
            sp(x1, y1, px)
            e2 = err
            if e2 > -dx:
                err -= dy
                x1 += sx
            if e2 < dy:
                err += dx
                y1 += sy
        sp(x2, y2, px)

    def _clip_line(self, x1, y1, x2, y2):
        """pygame clip_line (Liang-Barsky with pygame's rounding)."""
        p1 = x1 - x2
        p2 = -p1
        p3 = y1 - y2
        p4 = -p3
        q1 = x1
        q2 = self.width - x1
        q3 = y1
        q4 = self.height - y1
        if (p1 == 0 and q1 < 0) or (p2 == 0 and q2 < 0) or (p3 == 0 and q3 < 0) or (
            p4 == 0 and q4 < 0
        ):
            return None
        nmax = 0.0
        pmin = 1.0
        if p1:
            r1 = q1 / p1
            r2 = q2 / p2
            if p1 < 0:
                nmax = max(nmax, r1)
                pmin = min(pmin, r2)
            else:
                nmax = max(nmax, r2)
                pmin = min(pmin, r1)
        if p3:
            r1 = q3 / p3
            r2 = q4 / p4
            if p3 < 0:
                nmax = max(nmax, r1)
                pmin = min(pmin, r2)
            else:
                nmax = max(nmax, r2)
                pmin = min(pmin, r1)
        if nmax > pmin:
            return None

        def rnd(v):
            return int(v - 0.5) if v < 0 else int(v + 0.5)

        return (
            x1 + rnd(p2 * nmax),
            y1 + rnd(p4 * nmax),
            x1 + rnd(p2 * pmin),
            y1 + rnd(p4 * pmin),
        )

    # ------------------------------------------------------------ blits

    def blit(self, surf, x, y):
        """Blits a Surface (rgba bytes, w, h) at (x, y), clipped."""
        sw, sh, sbuf = surf.width, surf.height, surf.buf
        x0 = max(x, 0)
        y0 = max(y, 0)
        x1 = min(x + sw, self.width)
        y1 = min(y + sh, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        n = (x1 - x0) * 4
        sstride = sw * 4
        buf = self.buf
        stride = self.stride
        for yy in range(y0, y1):
            so = (yy - y) * sstride + (x0 - x) * 4
            do = yy * stride + x0 * 4
            buf[do : do + n] = sbuf[so : so + n]
        self.dirty = True


class Surface:
    """Small off-screen RGBA surface (text renders, camera frames)."""

    __slots__ = ("width", "height", "buf")

    def __init__(self, width, height, buf=None, fill=None):
        self.width = width
        self.height = height
        if buf is not None:
            self.buf = buf
        else:
            self.buf = bytearray((_px(fill) if fill else b"\x00\x00\x00\xff") * (width * height))

    def rotate90(self):
        """pygame.transform.rotate(surface, 90): counter-clockwise."""
        w, h = self.width, self.height
        src = self.buf
        out = bytearray(w * h * 4)
        # new (nx, ny) = old (w - 1 - ny, nx); new size (h, w)
        for ny in range(w):
            ox = w - 1 - ny
            for nx in range(h):
                so = (nx * w + ox) * 4
                do = (ny * h + nx) * 4
                out[do : do + 4] = src[so : so + 4]
        return Surface(h, w, out)
