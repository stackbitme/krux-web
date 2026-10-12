// Web Worker that runs Krux (Pyodide). Krux blocks this worker for as long
// as it runs; the page talks to it through shared memory (see shared.js).
import { loadPyodide } from "../vendor/pyodide/pyodide.mjs";
import { bootKrux } from "./kruxcore.js";

const base = new URL("../", import.meta.url);

self.onmessage = async (e) => {
  const { shared, device, version, files } = e.data;
  const post = (m) => self.postMessage(m);
  try {
    const status = await bootKrux({
      loadPyodide,
      pyodideURL: new URL("vendor/pyodide/", base).href,
      versionURL: new URL(`versions/${version}/`, base).href,
      runtimeURL: new URL("runtime.zip", base).href,
      shared,
      device,
      files,
      post,
      postFile: (path, data) => self.postMessage({ kind: "file", path, data }, [data.buffer]),
      fetchBytes: async (url) => {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`${r.status} ao baixar ${url}`);
        return new Uint8Array(await r.arrayBuffer());
      },
    });
    post({ kind: "exited", status });
  } catch (err) {
    post({ kind: "crash", traceback: String((err && err.stack) || err) });
    post({ kind: "exited", status: "crash" });
  }
};
