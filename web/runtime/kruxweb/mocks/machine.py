# Krux Web Simulator - `machine` mock.
import sys
from unittest import mock

from krux.krux_settings import Settings, THERMAL_ADAFRUIT_TXT, CNC_FILE_DRIVER
from krux.printers import create_printer
import krux

from .. import bridge

old_create_printer = create_printer


def new_create_printer():
    printer = old_create_printer()
    if printer:

        def new_print_qr_code(qr_code):
            print("QR Code sent to printer:", qr_code)
            return old_print_qr_code(qr_code)

        old_print_qr_code = printer.print_qr_code
        printer.print_qr_code = new_print_qr_code
    return printer


setattr(krux.printers, "create_printer", new_create_printer)

simulating_printer = False
shutdown_requested = False


def simulate_printer():
    global simulating_printer
    simulating_printer = True
    Settings().hardware.printer.driver = THERMAL_ADAFRUIT_TXT


def reset():
    bridge.flush(force=True)
    bridge.post("reset", shutdown=shutdown_requested)


class UART:
    UART1 = 0
    UART2 = 1
    UART3 = 2
    UART4 = 3
    UARTHS = 4

    def __init__(self, pin, baudrate):
        pass

    def read(self):
        if simulating_printer or Settings().hardware.printer.driver != THERMAL_ADAFRUIT_TXT:
            return chr(0b00000000)
        return None

    def readline(self):
        if simulating_printer and Settings().hardware.printer.driver == CNC_FILE_DRIVER:
            return "ok\n".encode()
        return None

    def write(self, data):
        if type(data) == str:
            print("String sent to printer:", data)


class SDCard:
    def remount():
        pass


def unique_id():
    return b"\xbc\x8d{%\x8e^\xc5Q\xb3N\x07f\x9f\xde\xbbG7\xddFK^\xdc\xdb\xbc\xb4E\x14A~3\x91\x12"


if "machine" not in sys.modules:
    sys.modules["machine"] = mock.MagicMock(
        reset=reset, UART=mock.MagicMock(wraps=UART), SDCard=SDCard, unique_id=unique_id
    )
