"""Exercises the uUR module and returns a JSON-able trace.

Run under native CPython (Krux's compiled uUR) and under Pyodide (ur.wasm +
runtime/uUR.py); both traces must be identical.
"""
import glob
import os
import random
import re


def run(cases_dir):
    import uUR

    out = {}
    files = sorted(glob.glob(os.path.join(cases_dir, "*", "*.UR_fragments.txt")))
    for f in files:
        name = os.path.relpath(f, cases_dir)
        with open(f) as fh:
            parts = re.findall(r'"(ur:[^"]+)"', fh.read(), re.I)
        d = uUR.URDecoder()
        trace = []
        for p in parts:
            st = d.receive_part(p)
            trace.append([st, round(d.estimated_percent_complete(), 5),
                          round(d.estimated_percent_complete(weight_mixed_frames=True), 5),
                          d.expected_part_count, d.processed_parts_count])
        r = d.result
        entry = {"trace": trace, "state": d.state}
        if r is not None:
            entry["type"] = r.type
            entry["cbor"] = r.cbor.hex()
            for fn in ["bytes_from_cbor", "psbt_from_cbor", "bip39_words_from_cbor",
                       "output_from_cbor", "output_from_cbor_account"]:
                try:
                    v = getattr(uUR.Types, fn)(r.cbor)
                    entry[fn] = v.hex() if isinstance(v, bytes) else v
                except Exception as e:
                    entry[fn] = "EXC:" + type(e).__name__
            for mx in (30, 100, 400):
                try:
                    e = uUR.UREncoder(r, mx)
                    n = e.fountain_encoder.seq_len() if e.fountain_encoder else 0
                    ps = [e.next_part() for _ in range(n + 6)]
                    entry["enc%d" % mx] = [n, e.is_single_part(), e.is_complete(), ps]
                    # Round trip through a fresh decoder using fountain parts only
                    d2 = uUR.URDecoder()
                    for p in ps[n:] + ps:
                        if d2.receive_part(p) == uUR.DECODER_OK:
                            break
                    entry["rt%d" % mx] = [d2.state, d2.result == r]
                except Exception as ex:
                    entry["enc%d" % mx] = "EXC:" + type(ex).__name__ + str(ex)
        out[name] = entry

    # PSBT round-trip on raw binaries and random payloads
    rnd = random.Random(21)
    for f in sorted(glob.glob(os.path.join(cases_dir, "PSBTs", "*.psbt.bin"))):
        raw = open(f, "rb").read()
        c = uUR.Types.psbt_to_cbor(raw)
        out["psbt_to_cbor:" + os.path.basename(f)] = [c.hex()[:200], len(c),
                                                       uUR.Types.psbt_from_cbor(c) == raw]
    for i in range(5):
        data = bytes(rnd.getrandbits(8) for _ in range(rnd.randint(1, 3000)))
        c = uUR.Types.bytes_to_cbor(data)
        ur = uUR.UR("bytes", c)
        e = uUR.UREncoder(ur, 150, 7, 12)
        out["rand%d" % i] = [c[:40].hex(), [e.next_part() for _ in range(4)], repr(ur), hash(ur) == hash(uUR.UR("bytes", c))]
    # Error behaviours
    errs = {}
    for label, fn in [
        ("bad_type", lambda: uUR.UR("Bad Type", b"\x01")),
        ("empty", lambda: uUR.UR("bytes", b"")),
        ("kw", lambda: uUR.UR(type="bytes", cbor=b"\x01")),
        ("frag", lambda: uUR.UREncoder(uUR.UR("bytes", b"\x41\x01"), 5)),
        ("short", lambda: uUR.UREncoder(uUR.UR("bytes", b"\x41\x01"), 100)),
        ("junk", lambda: uUR.URDecoder().receive_part("hello")),
        ("junk2", lambda: uUR.URDecoder().receive_part("ur:bytes/1-3/lpadaxcsencylobemohsgmoyadhdeynteelblrcygldwvarfl")),
        ("bad_cbor", lambda: uUR.Types.psbt_from_cbor(b"\xff\x00")),
    ]:
        try:
            errs[label] = repr(fn())
        except Exception as e:
            errs[label] = "EXC:" + type(e).__name__ + ":" + str(e)
    out["errors"] = errs
    out["consts"] = [uUR.DECODER_OK, uUR.DECODER_PROCESSING, uUR.DECODER_ERR_INVALID_CHECKSUM,
                     uUR.Types.CRYPTO_PSBT_TAG, uUR.Types.CRYPTO_ACCOUNT_TYPE, uUR.Types.CRYPTO_OUTPUT_TYPE,
                     uUR.Types.CRYPTO_BIP39_TYPE, uUR.Types.CRYPTO_PSBT_TYPE]
    return out


if __name__ == "__main__":
    import json, sys
    print(json.dumps(run(sys.argv[1]), sort_keys=True))
