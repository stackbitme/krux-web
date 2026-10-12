# Krux Web Simulator - replacement for kruxsim/devices.py (no pygame).
# Same constants; fonts come from .kfnt files (see tools/bdffont.py).
import os

from ..font import Font
from .. import assets

M5STICKV = "maixpy_m5stickv"
AMIGO = "maixpy_amigo"
PC = "maixpy_pc"
DOCK = "maixpy_dock"
YAHBOOM = "maixpy_yahboom"
CUBE = "maixpy_cube"
WONDER_MV = "maixpy_wonder_mv"
WONDER_K = "maixpy_wonder_k"
TZT = "maixpy_tzt"
EMBEDFIRE = "maixpy_embed_fire"

WINDOW_SIZES = {
    M5STICKV: (320, 640),
    AMIGO: (480, 768),
    PC: (480, 640),
    DOCK: (440, 820),
    YAHBOOM: (450, 600),
    CUBE: (484, 612),
    WONDER_MV: (410, 590),
    WONDER_K: (500, 650),
    TZT: (410, 580),
    EMBEDFIRE: (500, 671),
}

FONT_FILES = {
    M5STICKV: ("ter-u14n", "FusionPixel-14"),
    CUBE: ("ter-u14n", "FusionPixel-14"),
    DOCK: ("ter-u16n", "unifont-16"),
    YAHBOOM: ("ter-u16n", "unifont-16"),
    WONDER_MV: ("ter-u16n", "unifont-16"),
    TZT: ("ter-u16n", "unifont-16"),
    WONDER_K: ("ter-u16n", "unifont-16"),
    EMBEDFIRE: ("ter-u16n", "unifont-16"),
}
DEFAULT_FONTS = ("ter-u24b", "NotoSansCJK-24")


def with_prefix(device):
    return device if device.startswith("maixpy_") else "maixpy_" + device


class _LazyFont:
    """Loads the (large) wide-glyph font only when first needed."""

    def __init__(self, name):
        self.name = name
        self.font = None

    def _get(self):
        if self.font is None:
            self.font = Font(assets.font_bytes(self.name))
        return self.font

    def render(self, text, color, bgcolor):
        return self._get().render(text, color, bgcolor)


fonts = {}


def load_font(device):
    device = with_prefix(device)
    if device not in fonts:
        std, wide = FONT_FILES.get(device, DEFAULT_FONTS)
        fonts[device] = [Font(assets.font_bytes(std)), _LazyFont(wide)]
    return fonts[device]


def load_image(device):
    return None
