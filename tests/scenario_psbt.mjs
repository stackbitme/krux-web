// Scenario: load the "abandon ... about" wallet on testnet via QR, sign a
// PSBT scanned from a QR, and export the signed PSBT as a QR code.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { startSim } from "./node_sim.mjs";
import { C } from "../web/js/shared.js";
const require = createRequire(import.meta.url);
const { PNG } = require("pngjs");
const zbar = require("@undecaf/zbar-wasm");
const KRUX = process.env.KRUX_DIR || "../krux";
const QR = KRUX + "/simulator/sequences/qrcodes/";
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });

async function qrFile(name) {
  const png = PNG.sync.read(fs.readFileSync(QR + name));
  const syms = await zbar.scanRGBABuffer(png.data.buffer, png.width, png.height);
  return new Uint8Array(syms[0].data);
}

const sim = await startSim({ outDir: out, log: false });
let n = 0;
const shot = (label) => sim.shot(String(++n).padStart(2, "0") + "-" + label);
const press = async (k, times = 1) => { for (let i = 0; i < times; i++) { await sim.key(k); await sim.ready(); } };
const waitCam = async () => { const t = Date.now(); while (!sim.ctrl.get(C.CAM_ON) && Date.now() - t < 15000) await sim.sleep(20); };

await sim.ready();
await sim.tap(160, 400); await sim.ready();
await sim.tap(160, 100); await sim.ready(); shot("login");
await press("ENTER");           // activates buttons
await press("ENTER");           // Load Mnemonic
await press("ENTER"); shot("load-options"); // QR Code
await waitCam(); sim.qr(await qrFile("12-word-mnemonic.png")); await sim.ready(); shot("words");
await press("ENTER"); shot("wallet-options");
await press("DOWN", 2); await press("ENTER"); shot("customize");
await press("ENTER"); shot("network");
await press("DOWN"); await press("ENTER"); shot("network-set");
await press("UP"); await press("ENTER"); shot("back");
const t0 = Date.now();
await press("ENTER"); shot("home"); console.log("load wallet ms", Date.now() - t0);
await press("UP", 2); await press("ENTER"); shot("sign-options");
await press("ENTER"); shot("psbt-from");
await press("ENTER");
await waitCam(); sim.qr(await qrFile("singlesig-psbt-testnet.png")); await sim.ready(); shot("psbt-info-1");
await press("ENTER"); shot("psbt-info-2");
await press("ENTER"); shot("psbt-info-3");
await press("ENTER"); shot("psbt-info-4");
await press("DOWN"); shot("sign-prompt");
const t1 = Date.now();
await press("ENTER"); shot("after-sign"); console.log("sign ms", Date.now() - t1);
// Read the animated signed-PSBT QR straight from the LCD
const parts = {};
const fbView = new Uint8Array(sim.shared.fb);
for (let i = 0; i < 40 && Object.keys(parts).length < 8; i++) {
  await sim.sleep(150);
  const [w, h] = sim.lcd();
  const syms = await zbar.scanRGBABuffer(fbView.slice(0, w * h * 4).buffer, w, h);
  if (syms.length) { const t = syms[0].decode(); parts[t.split(" ")[0]] = t; }
}
fs.writeFileSync(out + "/signed-parts.json", JSON.stringify(parts, null, 1));
console.log("signed QR parts:", Object.keys(parts).sort().join(","));
fs.writeFileSync(out + "/stdout.txt", sim.stdout.join("\n"));
if (sim.crash) console.log("CRASH", sim.crash);
sim.stop(); process.exit(0);
