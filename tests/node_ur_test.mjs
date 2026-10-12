// Runs tests/ur_vectors.py inside Pyodide (Node) against ur.wasm + runtime/uUR.py
import { loadPyodide } from "../web/vendor/pyodide/pyodide.mjs";
import { createUR } from "../web/js/urwasm.js";
import fs from "node:fs";
const [wasmPath, casesDir] = process.argv.slice(2);
const py = await loadPyodide({ indexURL: new URL("../web/vendor/pyodide/", import.meta.url).pathname });
py.registerJsModule("_kxur", await createUR(fs.readFileSync(wasmPath)));
py.FS.mkdirTree("/rt");
py.FS.writeFile("/rt/uUR.py", fs.readFileSync(new URL("../web/runtime/uUR.py", import.meta.url)));
py.FS.writeFile("/rt/ur_vectors.py", fs.readFileSync(new URL("./ur_vectors.py", import.meta.url)));
py.FS.mkdirTree("/cases");
py.FS.mount(py.FS.filesystems.NODEFS, { root: casesDir }, "/cases");
const t = Date.now();
const out = py.runPython(`
import sys, json; sys.path.insert(0, "/rt")
import ur_vectors
json.dumps(ur_vectors.run("/cases"), sort_keys=True)`);
console.error("pyodide run ms", Date.now() - t);
process.stdout.write(out + "\n");
