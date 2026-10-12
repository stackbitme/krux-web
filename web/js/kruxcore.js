// Boots Krux inside Pyodide. Runs in a Web Worker (browser) or a
// worker_threads Worker (Node tests); everything environment specific is
// passed in `env`.
import { createUR } from "./urwasm.js";
import { pbkdf2Sync } from "./vendor/noble-pbkdf2.js";

const enc = new TextEncoder();

export async function bootKrux(env) {
  const {
    loadPyodide, pyodideURL, versionURL, runtimeURL, shared, device,
    files = [], post, postFile, fetchBytes, stdout, stderr, fonts = ["ter-u24b"],
  } = env;
  const progress = (step) => post({ kind: "progress", step });

  progress("python");
  const py = await loadPyodide({
    indexURL: pyodideURL,
    stdout: stdout || ((s) => post({ kind: "stdout", text: s })),
    stderr: stderr || ((s) => post({ kind: "stderr", text: s })),
  });

  progress("krux");
  const [kruxZip, runtimeZip, urWasm, ...fontData] = await Promise.all([
    fetchBytes(versionURL + "krux.zip"),
    fetchBytes(runtimeURL),
    fetchBytes(versionURL + "ur.wasm"),
    ...fonts.map((f) => fetchBytes(versionURL + "fonts/" + f + ".kfnt")),
  ]);
  const FS = py.FS;
  FS.mkdirTree("/krux/runtime");
  FS.mkdirTree("/krux/fonts");
  py.unpackArchive(kruxZip, "zip", { extractDir: "/krux" });
  py.unpackArchive(runtimeZip, "zip", { extractDir: "/krux/runtime" });
  fonts.forEach((f, i) => FS.writeFile("/krux/fonts/" + f + ".kfnt", fontData[i]));

  // Saved SD card / flash contents
  for (const { path, data } of files) {
    const full = "/krux/simulator/" + path.replace(/^\/+/, "");
    FS.mkdirTree(full.substring(0, full.lastIndexOf("/")));
    FS.writeFile(full, data);
  }

  const ctrl = new Int32Array(shared.ctrl);
  py.registerJsModule("_kxur", await createUR(urWasm));
  py.registerJsModule("_kxio", {
    ctrl,
    fb: new Uint8ClampedArray(shared.fb),
    cam: new Uint8Array(shared.cam),
    qr: new Uint8Array(shared.qr),
    inbox: new Uint8Array(shared.inbox),
    load: (i) => Atomics.load(ctrl, i),
    store: (i, v) => Atomics.store(ctrl, i, v),
    add: (i, v) => Atomics.add(ctrl, i, v),
    wait: (seen, ms) => Atomics.wait(ctrl, 0, seen, ms),
    post: (msg) => post(msg),
    postFile: (path, data) => postFile(path, data.slice ? data.slice() : data),
    pbkdf2: (name, pw, salt, iters, dklen) =>
      pbkdf2Sync(name, new Uint8Array(pw), new Uint8Array(salt), iters, dklen),
    fontsURL: versionURL + "fonts/",
  });

  progress("boot");
  py.runPython(`
import sys
sys.path.insert(0, "/krux/runtime")
`);
  if (env.run) return py.runPython(env.run); // tests: run a snippet instead of booting
  const status = py.runPython(`
from kruxweb import boot
boot.start(${JSON.stringify(device)})
`);
  return status;
}
