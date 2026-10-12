# Krux Web Simulator - touchscreen base (replaces the pygame mouse version).
# Pointer coordinates arrive from the page already in LCD pixels.
from .. import bridge
from . import lcd

sequence_executor = None


def register_sequence_executor(s):
    global sequence_executor
    sequence_executor = s


def _inside(pos):
    if pos is None or lcd.screen is None:
        return None
    x, y = pos
    if 0 <= x < lcd.screen.width and 0 <= y < lcd.screen.height:
        return (x, y)
    return None


class TCOMMON:
    def __init__(self):
        self.events = bridge.EventCounter(bridge.EV_TOUCH)
        self.irq_point = None

    def current_point(self):
        return _inside(bridge.mouse())

    def trigger_event(self):
        self.irq_point = _inside(bridge.touch_point())

    def event(self):
        if self.events.take():
            # Like the desktop simulator: the irq point is where the pointer
            # went down.
            self.trigger_event()
            return True
        return False

    def threshold(self, value):
        pass
