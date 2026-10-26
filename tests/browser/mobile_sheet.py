"""Phone layout: the panel is a bottom sheet that opens by itself when Krux
turns the camera on, closes once a source is chosen, and opens again from the
Camera button. Region tools only appear for screen capture.

    python3 tests/browser/mobile_sheet.py http://localhost:8000/ <outdir> <krux-dir>
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

URL, OUT, KRUX = sys.argv[1], sys.argv[2], sys.argv[3]
QR = os.path.join(KRUX, "simulator", "sequences", "qrcodes", "12-word-mnemonic_b.png")
os.makedirs(OUT, exist_ok=True)
SKIP_NOTICE = "try { sessionStorage.setItem('krux-web:notice', '1') } catch (e) {}"
results = []


def check(name, ok, info=""):
    results.append(ok)
    print("%s %s %s" % ("OK  " if ok else "FAIL", name, info), flush=True)


def tap(page, x, y):
    b = page.locator("#lcd").bounding_box()
    page.mouse.click(b["x"] + (x + 0.5) * b["width"] / 320, b["y"] + (y + 0.5) * b["height"] / 480)


def sheet_open(page):
    return page.evaluate("document.querySelector('#app').classList.contains('sheet-open')")


with sync_playwright() as p:
    b = p.chromium.launch()
    for name in ["iPhone SE", "iPhone 14"]:
        tag = name.replace(" ", "")
        ctx = b.new_context(**p.devices[name])
        ctx.add_init_script(SKIP_NOTICE)
        page = ctx.new_page()
        page.goto(URL + "?v=v26.09.0&device=amigo&lang=en-US")
        page.wait_for_function("window.__krux && window.__krux.lastFrame > 0 && document.querySelector('#overlay').hidden", timeout=120000)
        time.sleep(2.5)
        check(name + ": header in one row", page.locator(".bar").bounding_box()["height"] < 60)
        check(name + ": no page scroll", page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1"))
        check(name + ": sheet closed at start", not sheet_open(page))
        page.screenshot(path="%s/%s-1-device.png" % (OUT, tag))

        tap(page, 160, 400); time.sleep(1.2)   # Krux disclaimer
        tap(page, 160, 100); time.sleep(1.5)
        tap(page, 160, 60); time.sleep(1.2)    # Load mnemonic
        tap(page, 160, 60); time.sleep(1.5)    # QR code -> camera on
        check(name + ": sheet opens when Krux turns the camera on", sheet_open(page))
        check(name + ": button shows Krux waiting", page.get_attribute("#btn-sheet", "data-state") == "waiting")
        check(name + ": no preview or area tools", not page.is_visible("#cam-preview-box") and not page.is_visible("#cam-pick"))
        page.screenshot(path="%s/%s-2-sheet.png" % (OUT, tag))

        page.set_input_files("#cam-file", QR)
        page.wait_for_function("document.querySelector('#qr-note').textContent.includes('bytes')", timeout=20000)
        time.sleep(1.5)
        check(name + ": sheet closes after choosing an image", not sheet_open(page))
        page.screenshot(path="%s/%s-3-read.png" % (OUT, tag))

        page.click("#btn-sheet"); time.sleep(0.4)
        check(name + ": Camera button opens the sheet", sheet_open(page))
        page.click("#sheet-close"); time.sleep(0.4)
        check(name + ": Close button closes it", not sheet_open(page))
        ctx.close()

    # desktop: area tools hidden for an image, shown for screen capture
    page = b.new_page(viewport={"width": 1280, "height": 860})
    page.add_init_script(SKIP_NOTICE)
    page.goto(URL + "?v=v26.09.0&device=amigo&lang=en-US")
    page.wait_for_function("window.__krux && window.__krux.lastFrame > 0", timeout=120000)
    page.set_input_files("#cam-file", QR); time.sleep(0.5)
    check("desktop: image source has no area tools",
          page.is_visible("#cam-preview-box") and not page.is_visible("#cam-pick") and not page.is_visible("#cam-hint"))
    check("desktop: no Camera toggle", not page.is_visible("#btn-sheet"))
    b.close()

print("\n%d/%d checks passed" % (sum(results), len(results)))
