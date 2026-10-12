"""Checks the PSBT signed by the web simulator against embit (native)."""
import json, sys, base64
from embit import bip39, bip32
from embit.psbt import PSBT
from embit.networks import NETWORKS

parts = json.load(open(sys.argv[1]))
n = int(next(iter(parts)).split("of")[1])
data = "".join(parts["p%dof%d" % (i, n)].split(" ", 1)[1] for i in range(1, n + 1))
signed = PSBT.parse(base64.b64decode(data))

# Same PSBT signed natively
unsigned_b64 = sys.argv[2]
ref = PSBT.parse(base64.b64decode(unsigned_b64))
seed = bip39.mnemonic_to_seed("abandon " * 11 + "about")
root = bip32.HDKey.from_seed(seed, version=NETWORKS["test"]["xprv"])
ref.sign_with(root)

def sigs(p):
    return [{k.serialize().hex(): v.hex() for k, v in inp.partial_sigs.items()} for inp in p.inputs]

a, b = sigs(signed), sigs(ref)
print("inputs signed by web:", sum(1 for x in a if x), "/", len(a))
print("signatures identical to native embit:", a == b)
