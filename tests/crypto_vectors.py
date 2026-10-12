"""Krux crypto paths (KEF all versions, PBKDF2, BIP39 seed, encrypted QR)
run natively and in Pyodide; the JSON outputs must match.

Native:  python tests/crypto_vectors.py <krux-dir>
Pyodide: imported by tests/node_crypto.mjs (setup done there)
"""
import json
import sys


def native_setup(krux):
    from unittest import mock
    import hashlib
    from Crypto.Cipher import AES

    sys.path[:0] = [krux + "/src", krux + "/vendor/embit/src"]
    sys.modules["ucryptolib"] = mock.MagicMock(
        aes=AES.new, MODE_ECB=AES.MODE_ECB, MODE_CBC=AES.MODE_CBC,
        MODE_CTR=AES.MODE_CTR, MODE_GCM=AES.MODE_GCM)
    sys.modules["uhashlib_hw"] = mock.MagicMock(
        pbkdf2_hmac_sha256=lambda s, salt, it: hashlib.pbkdf2_hmac("sha256", s, salt, it),
        sha256=hashlib.sha256)
    sys.modules["deflate"] = mock.MagicMock()


def run():
    import hashlib
    import random
    from embit import bip39
    from krux import kef

    out = {}
    rnd = random.Random(7)
    out["pbkdf2_sha256"] = hashlib.pbkdf2_hmac("sha256", b"abc", b"salt", 100000).hex()
    out["pbkdf2_sha512_dklen"] = hashlib.pbkdf2_hmac("sha512", b"pw", b"s", 2048, 32).hex()
    out["bip39_seed"] = bip39.mnemonic_to_seed("abandon " * 11 + "about", "TREZOR").hex()
    for version in sorted(kef.VERSIONS):
        v = kef.VERSIONS[version]
        if v is None or v.get("compress"):
            continue
        key = bytes(rnd.getrandbits(8) for _ in range(5))
        salt = bytes(rnd.getrandbits(8) for _ in range(8))
        plain = bytes(rnd.getrandbits(8) for _ in range(16 * rnd.randint(1, 4)))
        iv = bytes(rnd.getrandbits(8) for _ in range(kef.MODE_IVS.get(v["mode"], 0)))
        try:
            c = kef.Cipher(key, salt, 10000)
            enc = c.encrypt(plain, version, iv, fail_unsafe=False)
            dec = c.decrypt(enc, version)
            out["kef_v%d" % version] = [enc.hex(), dec == plain]
        except Exception as e:
            out["kef_v%d" % version] = "EXC " + type(e).__name__ + str(e)
    return out


if __name__ == "__main__":
    native_setup(sys.argv[1])
    print(json.dumps(run(), sort_keys=True))
