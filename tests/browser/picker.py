"""Region picker after screen capture, and the layout at a ~1000px window."""
import sys, time, os
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SKIP_NOTICE = "try { sessionStorage.setItem('krux-web:notice', '1') } catch (e) {}"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                "--auto-select-desktop-capture-source=Entire screen", "--auto-accept-this-tab-capture"])
    page = b.new_page(viewport={"width": 1000, "height": 730}, device_scale_factor=2)
    page.add_init_script(SKIP_NOTICE)
    page.goto(URL + "?v=v26.09.0&device=amigo&lang=en-US")
    page.wait_for_function("window.__krux && window.__krux.lastFrame > 0 && document.querySelector('#overlay').hidden", timeout=120000)
    time.sleep(2)
    page.screenshot(path=OUT + "/layout-1000.png")
    page.click('[data-src="screen"]'); time.sleep(2)
    print("picker open:", page.is_visible("#picker"))
    box = page.locator("#picker-canvas").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.3)
    page.mouse.down(); page.mouse.move(box["x"] + box["width"] * 0.65, box["y"] + box["height"] * 0.75, steps=8); page.mouse.up()
    time.sleep(0.6)
    page.screenshot(path=OUT + "/picker.png")
    page.click("#picker-done"); time.sleep(0.5)
    print("picker closed:", not page.is_visible("#picker"), "| region set:", page.evaluate("!document.querySelector('#cam-full').disabled"))
    page.screenshot(path=OUT + "/after-picker.png")
    b.close()
