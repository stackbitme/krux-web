"""Camera sources in Chromium: fake webcam, screen capture, region select."""
import sys, time, os
from playwright.sync_api import sync_playwright
URL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

def tap(page, x, y):
    b = page.locator("#lcd").bounding_box()
    page.mouse.click(b["x"] + (x + 0.5) * b["width"] / 320, b["y"] + (y + 0.5) * b["height"] / 480)

C = dict(MOUSE_DOWN=5, EV_TOUCH=8, INPUT_POLLS=23, FRAME_SEQ=11, CAM_ON=13)
def st(page):
    return page.evaluate("(C) => { const c = window.__krux.ctrl; const o = {}; for (const k in C) o[k] = c.get(C[k]); return o; }", C)

def lit(page):
    # how many non-black pixels in the camera area of the LCD
    return page.evaluate("""() => { const d = document.querySelector('#lcd').getContext('2d').getImageData(40,120,240,240).data;
      let n=0; for (let i=0;i<d.length;i+=4) if (d[i]+d[i+1]+d[i+2] > 60) n++; return n; }""")

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                "--auto-select-desktop-capture-source=Entire screen", "--auto-accept-this-tab-capture",
                                "--enable-usermedia-screen-capturing"])
    ctx = b.new_context(viewport={"width": 1280, "height": 860})
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text))
    page.goto(URL + "?v=v26.09.0&device=amigo&lang=en-US")
    page.wait_for_function("window.__krux && window.__krux.lastFrame > 0 && document.querySelector('#overlay').hidden", timeout=120000)
    time.sleep(2.5)
    for (x, y) in [(160, 400), (160, 100), (160, 60), (160, 60)]:
        a = st(page); tap(page, x, y); time.sleep(0.3); b2 = st(page); time.sleep(1.5); print(a, b2, st(page))
    print("before webcam lit:", lit(page))
    page.click('[data-src="webcam"]'); time.sleep(2.5)
    print("webcam lit:", lit(page), "status:", page.inner_text("#cam-status"))
    page.screenshot(path=OUT + "/cam-webcam.png")
    # region select on the preview
    box = page.locator("#cam-preview").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    page.mouse.down(); page.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.8, steps=5); page.mouse.up()
    time.sleep(1)
    print("region set:", page.evaluate("!document.querySelector('#cam-full').disabled"))
    page.screenshot(path=OUT + "/cam-region.png")
    try:
        page.click('[data-src="screen"]'); time.sleep(2.5)
        print("screen pressed:", page.evaluate("document.querySelector('[data-src=screen]').getAttribute('aria-pressed')"), "lit:", lit(page))
        page.screenshot(path=OUT + "/cam-screen.png")
    except Exception as e:
        print("screen capture error:", e)
    print("toast:", page.inner_text("#toast") if page.is_visible("#toast") else "")
    print([l for l in logs if "rror" in l][:5])
    b.close()
