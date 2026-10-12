// worker_threads side of the Node test harness: same kruxcore.js as the browser.
import { parentPort, workerData } from "node:worker_threads";
import fs from "node:fs";
import path from "node:path";
import { loadPyodide } from "/home/claude/dl/pyo/p0277/package/pyodide.mjs";
import { bootKrux } from "../web/js/kruxcore.js";

const WEB = path.resolve(new URL("../web/", import.meta.url).pathname);
const post = (m) => parentPort.postMessage(m);
const status = await bootKrux({
  loadPyodide,
  pyodideURL: "/home/claude/dl/pyo/p0277/package/",
  versionURL: path.join(WEB, "versions", workerData.version) + "/",
  runtimeURL: path.join(WEB, "runtime.zip"),
  shared: workerData.shared,
  device: workerData.device,
  files: workerData.files || [],
  post,
  postFile: (p, data) => post({ kind: "file", path: p, data }),
  fetchBytes: async (p) => new Uint8Array(fs.readFileSync(p)),
});
post({ kind: "exited", status });
