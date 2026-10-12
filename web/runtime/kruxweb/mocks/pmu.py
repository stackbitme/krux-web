# Krux Web Simulator - `pmu` mock (power button = UP key, like the desktop sim).
import sys
from unittest import mock

from kruxsim.mocks.board import BOARD_CONFIG

from .. import bridge

PRESSED = 0
RELEASED = 1

sequence_executor = None


def register_sequence_executor(s):
    global sequence_executor
    sequence_executor = s


class PMU_Button:
    def __init__(self):
        self.key = bridge.KEY_UP
        self.state = RELEASED

    def value(self):
        return PRESSED if bridge.key_pressed(self.key) else RELEASED

    def event(self):
        if self.state == RELEASED:
            if self.value() == PRESSED:
                self.state = PRESSED
                return True
        self.state = self.value()
        return False


class PMUController:
    def __init__(self, i2c_bus):
        pass

    def get_battery_voltage(self):
        if BOARD_CONFIG["type"] in ("amigo", "m5stickv", "cube"):
            return 3820
        return 0

    def get_usb_voltage(self):
        return 0

    def enable_pek_button_monitor(self):
        pass

    def enter_sleep_mode(self):
        from . import machine

        machine.shutdown_requested = True

    def enable_adcs(self, on_off):
        pass

    def set_screen_brightness(self, level):
        pass

    def charging(self):
        return True

    def usb_connected(self):
        return True


if "pmu" not in sys.modules:
    sys.modules["pmu"] = mock.MagicMock(
        PMU_Button=PMU_Button,
        PMUController=PMUController,
    )
