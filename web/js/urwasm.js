// Thin JS wrapper over ur.wasm (Krux's bc-ur C library compiled to wasm32).
// Used from the Pyodide worker; the Python side (runtime/kruxweb/uUR.py)
// exposes the same `uUR` module surface as Krux's native binding.

const enc = new TextEncoder();
const dec = new TextDecoder();

export async function createUR(source) {
  let module;
  if (source instanceof WebAssembly.Module) module = source;
  else if (source instanceof ArrayBuffer || ArrayBuffer.isView(source)) module = await WebAssembly.compile(source);
  else module = await WebAssembly.compileStreaming(fetch(source));
  const inst = await WebAssembly.instantiate(module, {});
  const x = inst.exports;
  const u8 = () => new Uint8Array(x.memory.buffer);

  const putBytes = (bytes) => {
    const p = x.kx_malloc(bytes.length);
    u8().set(bytes, p);
    return p;
  };
  const putStr = (s) => {
    const b = enc.encode(s);
    const p = x.kx_malloc(b.length + 1);
    const m = u8();
    m.set(b, p);
    m[p + b.length] = 0;
    return p;
  };
  const readStr = (p) => {
    const m = u8();
    let e = p;
    while (m[e]) e++;
    return dec.decode(m.subarray(p, e));
  };
  const readBytes = (p, n) => u8().slice(p, p + n);
  const toU8 = (b) => (b instanceof Uint8Array ? b : new Uint8Array(b));

  // Calls fn(ptr, len) with `bytes` copied into wasm memory; frees afterwards.
  const withBytes = (bytes, fn) => {
    bytes = toU8(bytes);
    const p = putBytes(bytes);
    try { return fn(p, bytes.length); } finally { x.kx_free(p); }
  };
  const withStr = (s, fn) => {
    const p = putStr(s);
    try { return fn(p); } finally { x.kx_free(p); }
  };
  const takeBytes = (p) => {
    if (!p) return null;
    const out = readBytes(p, x.kx_out_len());
    x.kx_free(p);
    return out;
  };
  const takeStr = (p) => {
    if (!p) return null;
    const out = readStr(p);
    x.kx_free(p);
    return out;
  };

  return {
    isUrType: (t) => withStr(t, (p) => !!x.kx_is_ur_type(p)),

    urNew: (type, cbor) => withStr(type, (tp) => withBytes(cbor, (cp, n) => x.kx_ur_new(tp, cp, n))),
    urFree: (h) => x.kx_ur_free(h),
    urType: (h) => readStr(x.kx_ur_type(h)),
    urCbor: (h) => readBytes(x.kx_ur_cbor(h), x.kx_ur_cbor_len(h)),
    urCborLen: (h) => x.kx_ur_cbor_len(h),

    decNew: () => x.kx_dec_new(),
    decFree: (h) => x.kx_dec_free(h),
    decReceive: (h, part) => withStr(part, (p) => x.kx_dec_receive(h, p)),
    decState: (h) => x.kx_dec_state(h),
    decPct: (h, weighted) => x.kx_dec_pct(h, weighted ? 1 : 0),
    decExpected: (h) => x.kx_dec_expected(h),
    decProcessed: (h) => x.kx_dec_processed(h),
    decResult: (h) => x.kx_dec_result(h),

    encNew: (type, cbor, maxFrag, firstSeq, minFrag) =>
      withStr(type, (tp) => withBytes(cbor, (cp, n) => x.kx_enc_new(tp, cp, n, maxFrag, firstSeq >>> 0, minFrag))),
    encFree: (h) => x.kx_enc_free(h),
    encNext: (h) => takeStr(x.kx_enc_next(h)),
    encComplete: (h) => !!x.kx_enc_complete(h),
    encSingle: (h) => !!x.kx_enc_single(h),
    encHasFountain: (h) => !!x.kx_enc_has_fountain(h),
    encSeqLen: (h) => x.kx_enc_seq_len(h),

    bytesFromCbor: (b) => withBytes(b, (p, n) => takeBytes(x.kx_bytes_from_cbor(p, n))),
    bytesToCbor: (b) => withBytes(b, (p, n) => takeBytes(x.kx_bytes_to_cbor(p, n))),
    psbtFromCbor: (b) => withBytes(b, (p, n) => takeBytes(x.kx_psbt_from_cbor(p, n))),
    psbtToCbor: (b) => withBytes(b, (p, n) => takeBytes(x.kx_psbt_to_cbor(p, n))),
    bip39WordsFromCbor: (b) => withBytes(b, (p, n) => takeStr(x.kx_bip39_words_from_cbor(p, n))),
    outputFromCbor: (b) => withBytes(b, (p, n) => takeStr(x.kx_output_from_cbor(p, n))),
    outputFromCborAccount: (b) => withBytes(b, (p, n) => takeStr(x.kx_output_from_cbor_account(p, n))),

    constInt: (i) => x.kx_const_int(i),
    constStr: (i) => readStr(x.kx_const_str(i)),
  };
}
