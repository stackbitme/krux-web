# Krux Web Simulator - `Maix` (GPIO) and `ucryptolib` mocks.
import sys
from unittest import mock

from kruxsim.mocks.board import BUTTON_A, BUTTON_B, BUTTON_C
from kruxsim.mocks.fpioa_manager import fm_map

from .. import bridge
from .. import aes as AES

PRESSED = 0
RELEASED = 1


class GPIO:
    IN = 0
    OUT = 3
    PULL_NONE = 0
    PULL_UP = 2
    PULL_DOWN = 1
    IRQ_FALLING = 0

    def __init__(self, gpio_num, dir=None, val=None):
        self.key = None
        pin = fm_map[gpio_num]
        if pin == BUTTON_A:
            self.key = bridge.KEY_ENTER
        if pin == BUTTON_B:
            self.key = bridge.KEY_DOWN
        if pin == BUTTON_C:
            self.key = bridge.KEY_UP

    def value(self, val=1):
        if not self.key:
            return RELEASED
        return PRESSED if bridge.key_pressed(self.key) else RELEASED

    def irq(self, pin, mode):
        pass


for _i in range(32):
    setattr(GPIO, "GPIOHS%d" % _i, _i)
for _i in range(8):
    setattr(GPIO, "GPIO%d" % _i, 32 + _i)


if "Maix" not in sys.modules:
    sys.modules["Maix"] = mock.MagicMock(
        GPIO=GPIO,
    )

if "ucryptolib" not in sys.modules:
    sys.modules["ucryptolib"] = mock.MagicMock(
        aes=AES.new,
        MODE_ECB=AES.MODE_ECB,
        MODE_CBC=AES.MODE_CBC,
        MODE_CTR=AES.MODE_CTR,
        MODE_GCM=AES.MODE_GCM,
    )
