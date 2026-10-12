#!/usr/bin/env bash
# Runs the simulator's test suite. Needs:
#   KRUX_DIR  a Krux checkout (same tag as the built version) with its
#             simulator environment set up (uv sync --extra simulator)
#   node 18+, and `npm install` inside tests/
set -euo pipefail
cd "$(dirname "$0")/.."
KRUX_DIR="${KRUX_DIR:-../krux}"
export KRUX_DIR="$(cd "$KRUX_DIR" && pwd)"
PY="$KRUX_DIR/.venv/bin/python"
VERSION="${VERSION:-$(python3 -c 'import json;print(json.load(open("web/versions/index.json"))["default"])')}"
TMP="$(mktemp -d)"
ok() { echo "  ok  $*"; }

echo "1. Text and drawing identical to the desktop simulator (pygame)"
"$PY" tests/test_render_vs_pygame.py

echo "2. AES compatible with pycryptodome"
"$PY" tests/test_aes.py

echo "3. Krux crypto (KEF, PBKDF2, BIP39) identical to native Python"
"$PY" tests/crypto_vectors.py "$KRUX_DIR" > "$TMP/cv_native.json"
node tests/node_crypto.mjs > "$TMP/cv_web.json"
cmp -s "$TMP/cv_native.json" "$TMP/cv_web.json" && ok "identical" || { echo "DIFFERENT"; diff "$TMP/cv_native.json" "$TMP/cv_web.json"; exit 1; }

echo "4. bc-ur (uUR) in wasm identical to Krux's native module"
CASES="$KRUX_DIR/firmware/MaixPy/components/micropython/port/src/bc-ur/tests/test_cases"
"$PY" tests/ur_vectors.py "$CASES" > "$TMP/ur_native.json"
node tests/node_ur_test.mjs "web/versions/$VERSION/ur.wasm" "$CASES" > "$TMP/ur_web.json" 2>/dev/null
python3 - "$TMP/ur_native.json" "$TMP/ur_web.json" <<'PYEOF'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
def strip(d):  # the weighted progress estimate is not used by Krux
    for v in d.values():
        if isinstance(v, dict) and "trace" in v:
            v["trace"] = [t[:2] + t[3:] for t in v["trace"]]
    return d
same = strip(a) == strip(b)
print("  ok  identical" if same else "  DIFFERENT")
sys.exit(0 if same else 1)
PYEOF

echo "5. Sign a PSBT end to end and compare the signature with embit"
node tests/scenario_psbt.mjs "$TMP/psbt" | sed 's/^/  /'
node -e "
const fs=require('fs');const {PNG}=require('./tests/node_modules/pngjs');const z=require('./tests/node_modules/@undecaf/zbar-wasm');
(async()=>{const p=PNG.sync.read(fs.readFileSync(process.env.KRUX_DIR+'/simulator/sequences/qrcodes/singlesig-psbt-testnet.png'));
const s=await z.scanRGBABuffer(p.data.buffer,p.width,p.height);fs.writeFileSync('$TMP/unsigned.txt',s[0].decode());})()"
PYTHONPATH="$KRUX_DIR/vendor/embit/src" "$PY" tests/verify_psbt.py "$TMP/psbt/signed-parts.json" "$(cat "$TMP/unsigned.txt")" | sed 's/^/  /'

echo "Browser tests (Chromium + Playwright): see tests/browser/"
