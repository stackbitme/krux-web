// Node test harness: runs Krux (via kruxcore.js in a worker thread) and drives
// it like the page would, saving screenshots of the LCD.
import { Worker } from "node:worker_threads";
import fs from "node:fs";
import { createShared, Ctrl, C, KEY } from "../web/js/shared.js";
import { encodePNG } from "./png.mjs";

export async function startSim({ device = "maixpy_amigo", version = "v26.09.0", files = [], outDir, log = true } = {}) {
  const shared = createShared();
  const ctrl = new Ctrl(shared);
  const fb = new Uint8Array(shared.fb);
  const worker = new Worker(new URL("./node_worker.mjs", import.meta.url), {
    workerData: { shared, device, version, files },
  });
  const sim = { shared, ctrl, worker, messages: [], files: {}, exited: null, crash: null, stdout: [] };
  worker.on("message", (m) => {
    sim.messages.push(m);
    if (m.kind === "stdout" || m.kind === "stderr") { sim.stdout.push(m.text); if (log) console.log("  [krux]", m.text); }
    else if (m.kind === "file") sim.files[m.path] = Buffer.from(m.data);
    else if (m.kind === "fs-delete") delete sim.files[m.path];
    else if (m.kind === "crash") { sim.crash = m.traceback; console.log("CRASH", m.traceback); }
    else if (m.kind === "exited") sim.exited = m.status;
    else if (log && m.kind !== "progress") console.log("  [msg]", JSON.stringify(m));
  });
  worker.on("error", (e) => { console.log("WORKER ERROR", e); sim.exited = "error"; });
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  sim.sleep = sleep;
  sim.lcd = () => [ctrl.get(C.LCD_W), ctrl.get(C.LCD_H)];
  // Waits until the screen stops changing for `quiet` ms (or timeout).
  sim.settle = async (quiet = 700, timeout = 60000) => {
    const t0 = Date.now();
    let last = ctrl.get(C.FRAME_SEQ), lastChange = Date.now();
    while (Date.now() - t0 < timeout) {
      await sleep(50);
      const s = ctrl.get(C.FRAME_SEQ);
      if (s !== last) { last = s; lastChange = Date.now(); }
      else if (Date.now() - lastChange >= quiet && s > 0) return true;
      if (sim.exited) return false;
    }
    return false;
  };
  // Waits until Krux is idle waiting for input: the screen is quiet and
  // input is being polled continuously.
  sim.ready = async (timeout = 120000) => {
    const t0 = Date.now();
    let lastFrame = ctrl.get(C.FRAME_SEQ), frameAt = Date.now();
    let polls = [];
    while (Date.now() - t0 < timeout) {
      await sleep(25);
      const f = ctrl.get(C.FRAME_SEQ);
      if (f !== lastFrame) { lastFrame = f; frameAt = Date.now(); }
      polls.push([Date.now(), ctrl.get(C.INPUT_POLLS)]);
      polls = polls.filter(([t]) => Date.now() - t <= 250);
      const busyPolling = polls.length >= 8 && polls.every((p, i) => i === 0 || p[1] > polls[i - 1][1]);
      if (busyPolling && (Date.now() - frameAt >= 200 || ctrl.get(C.CAM_ON))) return Date.now() - t0;
      if (sim.exited) return -1;
    }
    return -2;
  };
  sim.shot = (name) => {
    const [w, h] = sim.lcd();
    const png = encodePNG(w, h, fb.slice(0, w * h * 4));
    const p = `${outDir}/${name}.png`;
    fs.writeFileSync(p, png);
    return p;
  };
  sim.tap = async (x, y, hold = 80) => {
    ctrl.set(C.MOUSE_X, x); ctrl.set(C.MOUSE_Y, y);
    ctrl.set(C.TOUCH_X, x); ctrl.set(C.TOUCH_Y, y);
    ctrl.set(C.MOUSE_DOWN, 1); ctrl.add(C.EV_TOUCH); ctrl.wake();
    await sleep(hold);
    ctrl.set(C.MOUSE_DOWN, 0); ctrl.wake();
  };
  sim.key = async (name, hold = 60) => {
    const bit = KEY[name], ev = { ENTER: C.EV_ENTER, DOWN: C.EV_PAGE, UP: C.EV_PREV }[name];
    Atomics.or(ctrl.i32, C.KEYS, bit); ctrl.add(ev); ctrl.wake();
    await sleep(hold);
    Atomics.and(ctrl.i32, C.KEYS, ~bit); ctrl.wake();
  };
  sim.qr = (text) => {
    const bytes = typeof text === "string" ? new TextEncoder().encode(text) : text;
    new Uint8Array(shared.qr).set(bytes);
    ctrl.set(C.QR_LEN, bytes.length); ctrl.add(C.QR_SEQ); ctrl.wake();
  };
  sim.stop = () => worker.terminate();
  return sim;
}
