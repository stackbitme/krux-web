# Krux Simulator for the browser

> **For educational purposes only.** Unofficial simulator, not a wallet: do not
> use it with real funds. Not affiliated with or endorsed by the Krux project.

Vibecoded by [Valandro](https://stackbit.me).

The real Krux running inside the browser, for study and presentations. Krux's
code is not modified: it is the same `src/` as the official release, running on
a Python that runs in the browser (Pyodide). Only the layer that pretends to be
the hardware (screen, touch, buttons, camera, SD card) was rebuilt for the
browser.

Included: **Krux v26.09.0**, device **Maix Amigo**.

## Opening it

**Online (any device, including iPhone and iPad):**
https://stackbitme.github.io/krux-web/

On iPhone and iPad, open it in Safari and use **Share → Add to Home Screen**:
the simulator becomes a full-screen app, without the browser bar.

**On a computer, offline:**

Needs Python 3 (nothing else, no extra packages). Works without internet.

| System | How to open |
| --- | --- |
| macOS | Double-click `Iniciar simulador (Mac).command`. The first time macOS may block it: right-click, **Open**. |
| Windows | Double-click `Iniciar simulador (Windows).bat`. If Python is missing, install it from python.org. |
| Linux | `./iniciar-simulador.sh` |
| Any | In a terminal, inside this folder: `python3 serve.py` |

The browser opens at `http://localhost:8000`. To stop, close the terminal
window (or Ctrl+C).

Opening `index.html` directly (double-clicking the file) **does not work**: the
browser only allows the shared memory the simulator needs when the page comes
from a server.

## Using it

- **Screen:** click or tap the device's screen.
- **Buttons:** Enter, Down arrow (next) and Up arrow (previous), or the buttons
  in the panel. As on the device, the first button press only switches to
  button mode.
- **Camera:** when Krux opens the camera, pick the source in the panel:
  - **Webcam**;
  - **Screen or window**: the browser asks what to share (whole screen, a
    window or a tab, e.g. Ian Coleman's). The first time on a Mac, allow
    "Screen Recording" for the browser in System Settings;
  - **Image**: in the field below, drag a QR image (from a folder or another
    browser tab), paste it with Ctrl+V / Cmd+V, or use "Paste image" and
    "Choose file".

  When sharing a screen, Krux can read just part of it (useful when there is
  more than one QR on screen): "Select area" opens the capture large so you can
  draw a rectangle around the QR. It opens by itself after you start sharing.
  Animated QRs (PSBT, UR, BBQr) work.
- **SD card:** add files (button or drag onto the page), download, delete,
  export everything as `.zip` or import a `.zip`. Works while Krux is running.
  In Chrome and Edge you can use **a folder on your computer** as the card:
  whatever Krux writes shows up in the folder.
- **Internal memory:** settings, PIN and the acceptance of Krux's initial
  notice are kept per device. "Erase internal memory" goes back to factory
  state.
- **Present:** hides the panels and enlarges the device (Esc to exit).
- **Screenshot:** downloads a 2x PNG of the Krux screen, good for slides.
- **Direct link:** `?v=v26.09.0&device=amigo&lang=pt-BR` opens without the
  start menu. The "Copy link to this setup" button builds that link.
- **Page language:** English by default. The selector at the top right (and in
  the opening notice) switches to Portuguese, and the choice is remembered.
  `?ui=pt` or `?ui=en` in the link forces one. Krux's own language is separate:
  it is picked in the start menu and also defaults to English.
- **Opening notice:** the "for educational purposes only" notice shows when the
  page opens. It comes back in each new tab or window, but not on reload. It
  can be reopened from the link in the start menu.

Everything is stored only in this browser (IndexedDB). Clearing the site's data
erases the card and the internal memory.

## Hosting it

Upload the whole `web/` folder to any static file host (a subdomain, GitHub
Pages, Netlify, Cloudflare Pages, your own server).

- The simulator needs to be "cross-origin isolated" (headers
  `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: require-corp`). If the host lets you set
  headers, set them. If not (GitHub Pages), the bundled `coi-serviceworker.js`
  takes care of it.
- Use HTTPS, otherwise the browser blocks the camera.
- **It does not work inside an iframe** on a regular site (WordPress and the
  like): the browser only isolates the page if the outer page is isolated too.
  Use a link or a dedicated subdomain, e.g. `krux.stackbit.me`.
- The first load downloads about 15 MB (Python). After that it is cached.

## Updating to a new Krux version

What changes per version lives in `web/versions/<version>/`. To build a new one:

1. Get the new Krux version with its submodules:
   ```
   git clone --branch v26.10.0 --recurse-submodules https://github.com/selfcustody/krux.git
   ```
2. Have `clang` and `wasm-ld` (to compile Krux's bc-ur library to
   WebAssembly): on macOS `brew install llvm lld`; on Debian/Ubuntu
   `apt install clang lld`; on Windows, the LLVM installer.
3. Run:
   ```
   python3 tools/build.py --krux ../krux --tag v26.10.0
   ```
   This creates `web/versions/v26.10.0/` and updates the version list in the
   menu.
4. Run the tests (below). If something in the simulation layer changed in Krux,
   the tests show where.

To enable other devices, add them to `ENABLED_DEVICES` in `tools/build.py` and
build again. The simulation layer already handles every model the official
simulator handles, but only the Amigo has been tested.

## How it works

```
browser (page)                             Web Worker
──────────────                             ──────────────────────────────────
screen (canvas) ◄──── shared memory ────── Pyodide (Python 3.12)
touch, buttons  ──►  (SharedArrayBuffer)   ├─ Krux src/ (unmodified)
camera + zbar   ──► frames and decoded QR  ├─ kruxsim (official simulator mocks)
SD card         ◄─► files                  ├─ runtime/kruxweb (screen, touch,
IndexedDB                                  │   camera, SD for the browser)
                                           └─ ur.wasm (Krux's bc-ur in C)
```

- Krux runs as on the device: in a loop that never gives control back. So it
  lives in a Web Worker and talks to the page through shared memory; waits use
  `Atomics.wait` and wake up immediately when you tap or press something.
- The screen is drawn in Python, reproducing pixel for pixel what pygame does
  in the official simulator (Krux's BDF fonts, rectangles, circles, lines).
- The `uUR` module (animated QRs) is Krux's own C library compiled to
  WebAssembly, with the same interface as the native module.
- AES (`ucryptolib`) is a pure-Python implementation compatible with
  pycryptodome; PBKDF2 uses `@noble/hashes`.
- QR codes are decoded with zbar (the same library the official simulator uses
  through pyzbar).

## Tests

`tests/run_all.sh` (with `KRUX_DIR` pointing to a Krux checkout of the same
version, with the official simulator's environment installed, and
`npm install` inside `tests/`) checks:

1. text in every translation and the drawn shapes are identical to pygame;
2. AES identical to pycryptodome (ECB, CBC, CTR, GCM);
3. KEF, PBKDF2 and BIP39 seeds identical to native Python;
4. `uUR` in wasm identical to Krux's native module on the bc-ur test cases;
5. signing a PSBT end to end, reading the signed QR off the screen and
   comparing it with native embit.

`tests/browser/` has Chromium tests (Playwright): boot, QR from an image,
wallet, SD card, keyboard, presentation, phone layout, power off and on again,
webcam, screen capture and area selection.

## iPhone and iPad

Works in Safari, at the online address (it needs HTTPS; opening it through the
computer's IP on the local network does not work).

- Touch, buttons, SD card, camera (back or front) and pasted or chosen images
  work.
- The device fills the screen. Camera, SD card and the other controls are in a
  sheet that slides up from the bottom: it opens from the **Camera** button at
  the top right, and by itself when Krux turns the camera on. Once a source is
  chosen it closes so you can see the Krux screen.
- "Screen or window" and "Use a folder on this computer" don't exist on iOS
  and are hidden.
- Python in the browser uses a few hundred MB of memory: on an older iPhone
  Safari may reload the page if it runs out.

## Known limitations

- Tested in Chromium. Firefox and Safari should work but have not been tested.
- "Use a folder on this computer" only exists in Chrome and Edge.
- Reading a TinySeed photographed by the camera does not work (it doesn't in
  the official simulator either).
- The printer is not simulated.

## Licenses

This project: MIT. Third-party components and their licenses are in
`THIRD_PARTY.md`. Krux is © Krux contributors, MIT license. This simulator is
not an official Krux project.
