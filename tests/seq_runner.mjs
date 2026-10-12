// Runs one of Krux's simulator sequence files (simulator/sequences/*.txt)
// against the web simulator core, saving LCD screenshots.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { startSim } from "./node_sim.mjs";
import { C } from "../web/js/shared.js";

const require = createRequire(import.meta.url);
const { PNG } = require("/home/claude/dl/npm/node_modules/pngjs");
const zbar = require("/home/claude/dl/npm/node_modules/@undecaf/zbar-wasm");

const COMMANDS = ["press", "press_amigo_only", "touch", "qrcode", "screenshot", "wait", "include", "x"];

function loadCommands(file, boardType) {
  let fp = file;
  if (!fs.existsSync(fp)) fp = path.join(path.dirname(file), boardType, path.basename(file));
  const out = [];
  for (let raw of fs.readFileSync(fp, "utf8").split("\n")) {
    if (!COMMANDS.some((c) => raw.startsWith(c))) continue;
    let times = 1;
    if (raw.startsWith("x")) { times = parseInt(raw.slice(1).split(/\s/)[0]); raw = raw.split(" ").slice(1).join(" "); }
    const parts = raw.trim().split(/\s+/);
    for (let i = 0; i < times; i++) {
      if (parts[0] === "include") out.push(...loadCommands(path.join(path.dirname(file), parts[1]), boardType));
      else out.push([parts[0], parts.slice(1)]);
    }
  }
  return out;
}

export async function runSequence({ seqFile, outDir, device = "maixpy_amigo", files = [], touch = true, log = false }) {
  fs.mkdirSync(outDir, { recursive: true });
  const boardType = device.replace("maixpy_", "");
  let cmds = loadCommands(seqFile, boardType);
  if (touch && cmds[0][0] === "wait" && cmds[1][0] !== "screenshot") cmds = [cmds[0], ["press", ["BUTTON_A"]], ...cmds.slice(1)];
  const sim = await startSim({ device, files, outDir, log });
  await sim.ready(120000);
  const shots = [];
  const timings = [];
  for (const [cmd, p] of cmds) {
    if (sim.exited || sim.crash) break;
    if (cmd === "wait") { await sim.sleep(parseFloat(p[0]) * 1000); }
    else if (cmd === "press" || (cmd === "press_amigo_only" && boardType === "amigo")) {
      const k = { BUTTON_A: C.EV_ENTER, BUTTON_B: C.EV_PAGE, BUTTON_C: C.EV_PREV }[p[0]];
      sim.ctrl.add(k); sim.ctrl.wake();
      await sim.sleep(40); timings.push([cmd + ' ' + p.join(' '), await sim.ready(60000)]);
    } else if (cmd === "touch") {
      const [x, y] = p.map(Number);
      sim.ctrl.set(C.TOUCH_X, x); sim.ctrl.set(C.TOUCH_Y, y); sim.ctrl.add(C.EV_TOUCH); sim.ctrl.wake();
      await sim.sleep(40); timings.push([cmd + ' ' + p.join(' '), await sim.ready(60000)]);
    } else if (cmd === "qrcode") {
      const png = PNG.sync.read(fs.readFileSync(path.join(path.dirname(seqFile), "qrcodes", p[0])));
      const syms = await zbar.scanRGBABuffer(png.data.buffer, png.width, png.height);
      const t0 = Date.now();
      while (!sim.ctrl.get(C.CAM_ON) && Date.now() - t0 < 10000) await sim.sleep(20);
      if (syms.length) sim.qr(new Uint8Array(syms[0].data));
      await sim.sleep(100); timings.push([cmd + ' ' + p.join(' '), await sim.ready(60000)]);
    } else if (cmd === "screenshot") {
      await sim.ready(30000);
      shots.push(sim.shot(p[0].replace(".png", "")));
    }
  }
  await sim.settle(300, 5000);
  const crash = sim.crash;
  sim.stop();
  return { shots, crash, stdout: sim.stdout, timings };
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  const [seqFile, outDir] = process.argv.slice(2);
  const files = [];
  const r = await runSequence({ seqFile, outDir, files, log: true });
  console.log(JSON.stringify({ shots: r.shots.length, crash: !!r.crash }));
  process.exit(0);
}
