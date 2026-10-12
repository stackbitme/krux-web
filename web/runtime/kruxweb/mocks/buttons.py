# Krux Web Simulator - `krux.buttons` mock: key presses come from the page
# (keyboard or on-screen buttons) through shared counters.
import sys
from unittest import mock

from Maix import GPIO
from fpioa_manager import fm

from .. import bridge

PRESSED = 0
RELEASED = 1


class TactileButtons:
    """Interface with Buttons"""

    def __init__(self):
        self.enter = None
        self.page = None
        self.page_prev = None
        self.enter_events = bridge.EventCounter(bridge.EV_ENTER)
        self.page_events = bridge.EventCounter(bridge.EV_PAGE)
        self.page_prev_events = bridge.EventCounter(bridge.EV_PREV)

    def init_enter(self, pin):
        fm.register(pin, fm.fpioa.GPIOHS21)
        self.enter = GPIO(GPIO.GPIOHS21, GPIO.IN, GPIO.PULL_UP)

    def init_page(self, pin):
        fm.register(pin, fm.fpioa.GPIOHS22)
        self.page = GPIO(GPIO.GPIOHS22, GPIO.IN, GPIO.PULL_UP)

    def init_page_prev(self, pin):
        fm.register(pin, fm.fpioa.GPIOHS0)
        self.page_prev = GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_UP)


buttons_control = TactileButtons()  # Singleton

sequence_executor = None


def register_sequence_executor(s):
    global sequence_executor
    sequence_executor = s


class Button:
    def __init__(self) -> None:
        pass

    def value(self):
        return RELEASED

    def event(self):
        return False


class ButtonEnter:
    def __init__(self, pin) -> None:
        buttons_control.init_enter(pin)

    def value(self):
        if buttons_control.enter is not None:
            return buttons_control.enter.value()
        return RELEASED

    def event(self):
        if buttons_control.enter is not None:
            return buttons_control.enter_events.take()
        return False


class ButtonPage:
    def __init__(self, pin) -> None:
        buttons_control.init_page(pin)

    def value(self):
        if buttons_control.page is not None:
            return buttons_control.page.value()
        return RELEASED

    def event(self):
        if buttons_control.page is not None:
            return buttons_control.page_events.take()
        return False


class ButtonPagePrev:
    def __init__(self, pin) -> None:
        buttons_control.init_page_prev(pin)

    def value(self):
        if buttons_control.page_prev is not None:
            return buttons_control.page_prev.value()
        return RELEASED

    def event(self):
        if buttons_control.page_prev is not None:
            return buttons_control.page_prev_events.take()
        return False


if "krux.buttons" not in sys.modules:
    sys.modules["krux.buttons"] = mock.MagicMock(
        TactileButtons=TactileButtons,
        ButtonEnter=ButtonEnter,
        ButtonPage=ButtonPage,
        ButtonPagePrev=ButtonPagePrev,
        PRESSED=PRESSED,
        RELEASED=RELEASED,
    )
