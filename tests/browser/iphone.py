"""Layout and touch on iPhone/iPad-sized viewports (Chromium emulation)."""
import sys, time, os
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for name in ["iPhone 14", "iPad Pro 11"]:
        dev = dict(p.devices[name])
        dev.pop("default_browser_type", None)
        ctx = b.new_context(**dev)
        page = ctx.new_page()
        page.goto(URL)
        page.wait_for_selector("#sel-version option", state="attached", timeout=30000)
        page.screenshot(path=f"{OUT}/{name}-launcher.png")
        page.tap("#btn-start")
        page.wait_for_function("window.__krux && window.__krux.lastFrame > 0 && document.querySelector('#overlay').hidden", timeout=120000)
        time.sleep(2.5)
        box = page.locator("#lcd").bounding_box()
        page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.8); time.sleep(1.8)
        page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.2); time.sleep(1.8)
        page.screenshot(path=f"{OUT}/{name}-sim.png")
        page.screenshot(path=f"{OUT}/{name}-full.png", full_page=True)
        print(name, "viewport", dev["viewport"], "lcd box", {k: round(v) for k, v in box.items()},
              "keys hint visible:", page.is_visible("#keys-hint"))
        ctx.close()
    b.close()
