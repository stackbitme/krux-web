# Krux Web Simulator - `lcd` mock.
#
# Same behaviour as kruxsim/mocks/lcd.py from the desktop simulator, but the
# drawing happens synchronously on an RGBA framebuffer (kruxweb.fb) instead of
# being posted as pygame events to a render thread.
import sys
import math
import time
from unittest import mock

from kruxsim.mocks.board import BOARD_CONFIG
from krux.krux_settings import Settings

from .. import bridge
from ..fb import Framebuffer, Surface

COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)

WIDTH = BOARD_CONFIG["lcd"]["width"]
HEIGHT = BOARD_CONFIG["lcd"]["height"]

JAPANESE_CODEPOINT_MIN = 0x3000
JAPANESE_CODEPOINT_MAX = 0x30FF
CHINESE_CODEPOINT_MIN = 0x4E00
CHINESE_CODEPOINT_MAX = 0x9FFF
KOREAN_CODEPOINT_MIN = 0xAC00
KOREAN_CODEPOINT_MAX = 0xD7A3

screen = None
portrait = True
landscape = False

count_call_fill_rectangle = 0


def rgb565torgb888(color):
    """convert from gggbbbbbrrrrrggg to tuple"""
    MASK5 = 0b11111
    MASK3 = 0b111

    red = (color >> 3) & MASK5
    red *= 255
    red //= 31
    green = color >> 13
    green += (color & MASK3) << 3
    green *= 255
    green //= 63
    blue = (color >> 8) & MASK5
    blue *= 255
    blue //= 31
    return (red, green, blue)


def _ensure_screen():
    global screen
    if screen is None:
        screen = Framebuffer(HEIGHT, WIDTH)
        bridge.set_framebuffer(screen)
    return screen


def clear(color):
    color = rgb565torgb888(color)
    if screen:
        screen.fill(color)
    bridge.poll()


def init(*args, **kwargs):
    pass


def register(addr, val):
    pass


def _zoom_out(frame, factor=0.6):
    """Nearest-neighbour equivalent of the desktop zoom_out (M5StickV)."""
    w, h = frame.width, frame.height
    nw, nh = int(w * factor), int(h * factor)
    out = bytearray(w * h * 4)
    for i in range(3, len(out), 4):
        out[i] = 255
    ox, oy = (w - nw) // 2, (h - nh) // 2
    src = frame.buf
    for y in range(nh):
        sy = min(h - 1, int(y / factor))
        for x in range(nw):
            sx = min(w - 1, int(x / factor))
            so = (sy * w + sx) * 4
            do = ((oy + y) * w + ox + x) * 4
            out[do : do + 4] = src[so : so + 4]
    return Surface(w, h, out)


def display(img, oft=(0, 0), roi=None):
    image_width = 240
    image_height = 320

    # Swap and adjust oft axis
    if portrait:
        oft = (oft[1], oft[0])

    if screen is None:
        return
    try:
        frame = img.get_frame()
        if isinstance(frame, mock.MagicMock) or frame is None:
            return
        # Camera frames already arrive cropped to 3:4 and sized 240x320
        if frame.width != image_width or frame.height != image_height:
            return
        if roi and roi[2] < 240:
            frame = _zoom_out(frame, 0.6)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Cut image according to region of interest (on the x/y swapped array,
    # so roi = (x, y, w, h) selects surface columns x..x+w and rows y..y+h)
    sx, sy, sw, sh = 0, 0, frame.width, frame.height
    if roi:
        x, y, w, h = roi
        sx, sy = x, y
        sw = max(0, min(frame.width, x + w) - x)
        sh = max(0, min(frame.height, y + h) - y)
    if sw <= 0 or sh <= 0:
        return
    if (sx, sy, sw, sh) != (0, 0, frame.width, frame.height):
        rows = []
        stride = frame.width * 4
        for yy in range(sy, sy + sh):
            o = yy * stride + sx * 4
            rows.append(frame.buf[o : o + sw * 4])
        frame = Surface(sw, sh, bytearray(b"".join(rows)))
    screen.blit(frame, oft[0], oft[1])
    bridge.poll()


def rotation(r):
    global portrait
    global landscape
    if screen is None:
        portrait = True
        _ensure_screen()
    if r == 2 and BOARD_CONFIG["type"] != "cube":
        landscape = True
    else:
        landscape = False


def width():
    return HEIGHT if portrait else WIDTH


def height():
    return WIDTH if portrait else HEIGHT


def _is_x_flipped():
    flipped_x = False
    if BOARD_CONFIG["type"] == "amigo":
        flipped_x = Settings().hardware.display.flipped_x_coordinates
    return flipped_x


def _is_wide_cp(o):
    return (
        JAPANESE_CODEPOINT_MIN <= o <= JAPANESE_CODEPOINT_MAX
        or CHINESE_CODEPOINT_MIN <= o <= CHINESE_CODEPOINT_MAX
        or KOREAN_CODEPOINT_MIN <= o <= KOREAN_CODEPOINT_MAX
    )


def string_width_px(string):
    standard_width = BOARD_CONFIG["krux"]["display"]["font"][0]
    wide_width = BOARD_CONFIG["krux"]["display"]["font_wide"][0]
    string_width = 0
    for c in string:
        string_width += wide_width if _is_wide_cp(ord(c)) else standard_width
    return string_width


def string_has_wide_glyph(string):
    for c in string:
        if _is_wide_cp(ord(c)):
            return True
    return False


def is_wide(c):
    return _is_wide_cp(ord(c))


def char_width(c):
    if _is_wide_cp(ord(c)):
        return BOARD_CONFIG["krux"]["display"]["font_wide"][0]
    return BOARD_CONFIG["krux"]["display"]["font"][0]


def _blit_text(text, x_val, y, x_position):
    if landscape:
        text = text.rotate90()
        screen.blit(text, height() - text.width - y, x_position)
    else:
        screen.blit(text, x_val, y)


def draw_string(x, y, s, color, bgcolor=COLOR_BLACK):
    from kruxsim import devices

    color = rgb565torgb888(color)
    bgcolor = rgb565torgb888(bgcolor)
    if screen is None:
        return
    fonts = devices.load_font(BOARD_CONFIG["type"])
    amigo = BOARD_CONFIG["type"] == "amigo"
    x_position = x
    if not string_has_wide_glyph(s):
        text = fonts[0].render(s, color, bgcolor)
        x_val = x_position if not amigo else width() - text.width - x_position
        _blit_text(text, x_val, y, x_position)
    else:
        # draw wide text char by char
        total_with = string_width_px(s)
        for c in s:
            x_val = x_position if not amigo else width() - x_position - total_with
            font = fonts[1] if is_wide(c) else fonts[0]
            text = font.render(c, color, bgcolor)
            _blit_text(text, x_val, y, x_position)
            x_position += char_width(c) if not amigo else -char_width(c)
    bridge.poll()


def draw_qr_code_binary(
    offset_x, offset_y, code_bin, max_width, dark_color, light_color, background
):
    dark_color = rgb565torgb888(dark_color)
    light_color = rgb565torgb888(light_color)
    if screen is None:
        return
    starting_size = int(math.sqrt(len(code_bin) * 8))
    block_size_divisor = starting_size + 2
    # adds 2 to create room for a 1 block border
    scale = max_width // block_size_divisor
    width_ = starting_size * scale
    border_size = (max_width - width_) // 2
    opposite_border_offset = border_size + width_ - 1
    fr = screen.fill_rect
    # Top border
    fr(offset_x, offset_y, max_width, border_size, light_color)
    # Bottom border
    fr(
        offset_x,
        offset_y + opposite_border_offset,
        max_width,
        max_width - opposite_border_offset,
        light_color,
    )
    # Left border
    fr(
        offset_x,
        offset_y + border_size,
        border_size,
        opposite_border_offset - border_size,
        light_color,
    )
    # Right border
    fr(
        offset_x + opposite_border_offset,
        offset_y + border_size,
        max_width - opposite_border_offset,
        opposite_border_offset - border_size,
        light_color,
    )
    # QR code rendering
    for og_y in range(starting_size):
        y = border_size + og_y * scale + offset_y
        run_start = 0
        run_color = None
        for og_x in range(starting_size + 1):
            if og_x < starting_size:
                idx = og_y * starting_size + og_x
                color = dark_color if code_bin[idx >> 3] & (1 << (idx % 8)) else light_color
            else:
                color = None
            if color != run_color:
                if run_color is not None:
                    fr(
                        border_size + run_start * scale + offset_x,
                        y,
                        (og_x - run_start) * scale,
                        scale,
                        run_color,
                    )
                run_color = color
                run_start = og_x
    bridge.poll()


def fill_rectangle(x, y, w, h, color, radius=0):
    color = rgb565torgb888(color)
    if _is_x_flipped():
        x = width() - w - x
    radius = min(radius, min(w, h) // 2)
    if screen is not None:
        if radius == 0:
            screen.draw_rect(color, x, y, w, h)
        else:
            dr = screen.draw_rect
            dc = screen.draw_circle
            dr(color, x + radius, y, w - 2 * radius, h)
            dr(color, x, y + radius, radius, h - 2 * radius)
            dr(color, x + w - radius, y + radius, radius, h - 2 * radius)
            dc(color, (x + radius, y + radius), radius)
            dc(color, (x + w - radius, y + radius), radius)
            dc(color, (x + radius, y + h - radius), radius)
            dc(color, (x + w - radius, y + h - radius), radius)

    global count_call_fill_rectangle
    count_call_fill_rectangle += 1
    if count_call_fill_rectangle > 9:
        bridge.poll()
        count_call_fill_rectangle = 0


def draw_circle(x, y, radious, quadrant, color):
    color = rgb565torgb888(color)
    if _is_x_flipped():
        x = width() - x - 1
    if screen is not None and quadrant == 0:
        screen.draw_circle(color, (x, y), radious)


def draw_line(x_0, y_0, x_1, y_1, color):
    color = rgb565torgb888(color)
    if screen is None:
        return
    start_pos = (x_0, y_0)
    end_pos = (x_1, y_1)
    if _is_x_flipped():
        start_pos = (width() - x_1 - 1, y_0)
        end_pos = (width() - x_0 - 1, y_1)
    screen.draw_line(color, start_pos, end_pos)


def draw_outline(x, y, w, h, color):
    color = rgb565torgb888(color)
    if screen is None:
        return
    screen.draw_rect(
        color,
        (width() - w - x - 1 if _is_x_flipped() else x),
        y,
        w + 1,
        h + 1,
        1,
    )


if "lcd" not in sys.modules:
    sys.modules["lcd"] = mock.MagicMock(
        init=init,
        register=register,
        display=display,
        clear=clear,
        rotation=rotation,
        width=width,
        height=height,
        string_width_px=string_width_px,
        draw_string=draw_string,
        draw_qr_code_binary=draw_qr_code_binary,
        fill_rectangle=fill_rectangle,
        draw_circle=draw_circle,
        draw_line=draw_line,
        draw_outline=draw_outline,
        string_has_wide_glyph=string_has_wide_glyph,
        BLACK=COLOR_BLACK,
        WHITE=COLOR_WHITE,
    )
