"""Image source: drop on the field, paste event, and the 'Colar imagem' button."""
import base64, sys, time, os
from playwright.sync_api import sync_playwright
URL, OUT, KRUX = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
png = base64.b64encode(open(os.path.join(KRUX, "simulator/sequences/qrcodes/12-word-mnemonic_b.png"), "rb").read()).decode()

def tap(page, x, y):
    b = page.locator("#lcd").bounding_box()
    page.mouse.click(b["x"] + (x + 0.5) * b["width"] / 320, b["y"] + (y + 0.5) * b["height"] / 480)

MAKE_FILE = "async (b64) => { const r = await fetch('data:image/png;base64,' + b64); return new File([await r.blob()], 'qr.png', {type: 'image/png'}); }"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 860})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=URL.rstrip("/"))
    page = ctx.new_page()
    page.goto(URL + "?v=v26.09.0&device=amigo&lang=en-US")
    page.wait_for_function("window.__krux && window.__krux.lastFrame > 0 && document.querySelector('#overlay').hidden", timeout=120000)
    time.sleep(2.5)
    for (x, y) in [(160, 400), (160, 100), (160, 60), (160, 60)]:
        tap(page, x, y); time.sleep(1.8)

    # 1. drop a file on the field
    page.evaluate("""async (b64) => {
      const r = await fetch('data:image/png;base64,' + b64);
      const f = new File([await r.blob()], 'qr.png', {type: 'image/png'});
      const dt = new DataTransfer(); dt.items.add(f);
      const el = document.querySelector('#img-drop');
      el.dispatchEvent(new DragEvent('dragover', {dataTransfer: dt, bubbles: true, cancelable: true}));
      el.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
    }""", png)
    page.wait_for_function("document.querySelector('#qr-note').textContent.includes('bytes')", timeout=20000)
    print("drop -> QR read:", page.inner_text("#qr-note"))
    page.screenshot(path=OUT + "/img-drop.png")
    page.click("#cam-stop")

    # 2. 'Colar imagem' button reading the real clipboard
    page.evaluate("""async (b64) => {
      const r = await fetch('data:image/png;base64,' + b64);
      await navigator.clipboard.write([new ClipboardItem({'image/png': await r.blob()})]);
    }""", png)
    page.click("#img-paste"); time.sleep(1)
    print("paste button -> source:", page.evaluate("window.__cam && window.__cam.kind"), "| field active:", page.evaluate("document.querySelector('#img-drop').classList.contains('active')"))
    page.click("#cam-stop")

    # 3. paste event (Ctrl+V)
    page.evaluate("""async (b64) => {
      const r = await fetch('data:image/png;base64,' + b64);
      const dt = new DataTransfer(); dt.items.add(new File([await r.blob()], 'qr.png', {type: 'image/png'}));
      document.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    }""", png)
    time.sleep(1)
    print("Ctrl+V -> field active:", page.evaluate("document.querySelector('#img-drop').classList.contains('active')"))
    page.screenshot(path=OUT + "/img-pasted.png")
    b.close()
