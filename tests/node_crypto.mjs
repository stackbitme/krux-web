import fs from "node:fs";
import path from "node:path";
import { loadPyodide } from "../web/vendor/pyodide/pyodide.mjs";
import { bootKrux } from "../web/js/kruxcore.js";
import { createShared } from "../web/js/shared.js";
const WEB = path.resolve(new URL("../web/", import.meta.url).pathname);
const res = await bootKrux({
  loadPyodide, pyodideURL: new URL("../web/vendor/pyodide/", import.meta.url).pathname,
  versionURL: path.join(WEB, "versions", "v26.09.0") + "/", runtimeURL: path.join(WEB, "runtime.zip"),
  shared: createShared(), device: "maixpy_amigo", post: () => {}, postFile: () => {},
  files: [{ path: "../cv.py", data: fs.readFileSync(new URL("./crypto_vectors.py", import.meta.url)) }],
  fetchBytes: async (p) => new Uint8Array(fs.readFileSync(p)),
  run: `
import sys, hashlib, json
sys.path[:0] = ["/krux/vendor", "/krux/src"]
from unittest import mock
from kruxweb import boot, aes
hashlib.pbkdf2_hmac = boot._pbkdf2_hmac
sys.modules["ucryptolib"] = mock.MagicMock(aes=aes.new, MODE_ECB=aes.MODE_ECB, MODE_CBC=aes.MODE_CBC, MODE_CTR=aes.MODE_CTR, MODE_GCM=aes.MODE_GCM)
sys.modules["uhashlib_hw"] = mock.MagicMock(pbkdf2_hmac_sha256=lambda s, salt, it: hashlib.pbkdf2_hmac("sha256", s, salt, it), sha256=hashlib.sha256)
sys.modules["deflate"] = mock.MagicMock()
exec(open("/tmp/cv.py").read().split("if __name__")[0])
json.dumps(run(), sort_keys=True)
`.replace('open("/tmp/cv.py")', "open('/krux/cv.py')"),
});
console.log(res);
