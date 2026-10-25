"""End-to-end browser test of the web simulator (Chromium via Playwright).

    python3 tests/browser/e2e.py http://localhost:8765/ <outdir> <krux-dir>
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

URL, OUT, KRUX = sys.argv[1], sys.argv[2], sys.argv[3]
QR_DIR = os.path.join(KRUX, "simulator", "sequences", "qrcodes")
os.makedirs(OUT, exist_ok=True)
results = []


def check(name, ok, info=""):
    results.append((name, ok))
    print("%s %s %s" % ("OK  " if ok else "FAIL", name, info), flush=True)


def tap(page, x, y):
    b = page.locator("#lcd").bounding_box()
    page.mouse.click(b["x"] + (x + 0.5) * b["width"] / 320, b["y"] + (y + 0.5) * b["height"] / 480)


def lcd_pixel(page, x, y):
    return page.evaluate(
        "([x,y]) => Array.from(document.querySelector('#lcd').getContext('2d').getImageData(x,y,1,1).data)",
        [x, y],
    )


with sync_playwright() as p:
    browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 860})
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append("%s: %s" % (m.type, m.text)))
    page.on("pageerror", lambda e: logs.append("PAGEERROR: %s" % e))

    t0 = time.time()
    page.goto(URL)
    page.wait_for_selector("#sel-version option", state="attached", timeout=30000)
    check("cross-origin isolated", page.evaluate("crossOriginIsolated"))
    page.screenshot(path=OUT + "/01-launcher.png")
    page.click("#btn-start")
    page.wait_for_function("document.querySelector('#overlay').hidden === true", timeout=120000)
    check("boot", True, "%.1fs" % (time.time() - t0))
    check("url has config", "v=v26.09.0" in page.url and "device=amigo" in page.url, page.url)
    time.sleep(2.5)  # past the splash screen (taps there are ignored, like on the device)
    page.screenshot(path=OUT + "/02-disclaimer.png")

    # disclaimer -> "I understand"
    tap(page, 160, 400); time.sleep(1.2)
    tap(page, 160, 100); time.sleep(1.5)
    page.screenshot(path=OUT + "/03-menu.png")

    # Load mnemonic -> QR code
    tap(page, 160, 60); time.sleep(1.2)
    tap(page, 160, 60); time.sleep(1.5)
    st = page.inner_text("#cam-status")
    check("camera requested by Krux", "esperando" in st, st)
    page.screenshot(path=OUT + "/04-camera-waiting.png")
    page.set_input_files("#cam-file", os.path.join(QR_DIR, "12-word-mnemonic_b.png"))
    page.wait_for_function("document.querySelector('#qr-note').textContent.includes('bytes')", timeout=20000)
    time.sleep(1.5)
    page.screenshot(path=OUT + "/05-mnemonic-from-qr.png")
    check("QR decoded", True, page.inner_text("#qr-note"))

    # Go -> wallet -> load wallet
    tap(page, 241, 447); time.sleep(2)
    page.screenshot(path=OUT + "/06-wallet.png")
    tap(page, 160, 175); time.sleep(2)
    page.screenshot(path=OUT + "/07-home.png")

    # SD card: add a file while running, it must show up in the list
    sample = os.path.join(OUT, "exemplo.txt")
    with open(sample, "w") as f:
        f.write("ola krux")
    page.set_input_files("#sd-file", sample)
    page.wait_for_function("document.querySelector('#sd-list').textContent.includes('exemplo.txt')", timeout=10000)
    check("SD file added", True)

    # keyboard: ArrowDown moves the selection
    page.locator("#lcd").focus()
    page.keyboard.press("ArrowDown"); time.sleep(0.8)
    page.screenshot(path=OUT + "/08-after-down.png")

    # presentation mode
    page.click("#btn-present"); time.sleep(0.8)
    page.screenshot(path=OUT + "/09-present.png")
    page.keyboard.press("Escape"); time.sleep(0.5)

    # reload: SD file and acknowledged disclaimer persist, link opens directly
    page.reload()
    page.wait_for_function("window.__krux && window.__krux.lastFrame > 0 && document.querySelector('#overlay').hidden", timeout=120000)
    time.sleep(1.5)
    page.screenshot(path=OUT + "/10-after-reload.png")
    check("SD persists", "exemplo.txt" in page.inner_text("#sd-list"))
    # disclaimer was acknowledged before: we are straight at the login menu
    time.sleep(1.0)
    tap(page, 160, 437)  # Shutdown
    time.sleep(1.5)
    page.screenshot(path=OUT + "/10a-shutdown-confirm.png")
    tap(page, 240, 285)  # "Sim"
    page.wait_for_function("!document.querySelector('#overlay').hidden && document.querySelector('#overlay-text').textContent.includes('desligada')", timeout=20000)
    check("shutdown shows overlay", True, page.inner_text("#overlay-text"))
    page.screenshot(path=OUT + "/10b-shutdown.png")
    page.click("#overlay-btn")
    page.wait_for_function("document.querySelector('#overlay').hidden", timeout=60000)
    check("power on again", True)
    time.sleep(1.5)
    page.click("#btn-restart")
    page.wait_for_function("document.querySelector('#overlay').hidden && window.__krux.lastFrame > 0", timeout=60000)
    check("restart button", True)

    # mobile layout
    mob = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mp = mob.new_page()
    mp.goto(URL)
    mp.wait_for_selector("#sel-version option", state="attached", timeout=30000)
    mp.screenshot(path=OUT + "/11-mobile-launcher.png")
    mp.click("#btn-start")
    mp.wait_for_function("document.querySelector('#overlay').hidden === true", timeout=120000)
    time.sleep(1.5)
    mp.screenshot(path=OUT + "/12-mobile-sim.png")
    mp.screenshot(path=OUT + "/13-mobile-full.png", full_page=True)

    errs = [l for l in logs if "PAGEERROR" in l or l.startswith("error")]
    check("no page errors", not errs, "\n".join(errs[:10]))
    browser.close()

print("\n%d/%d checks passed" % (sum(ok for _, ok in results), len(results)))
