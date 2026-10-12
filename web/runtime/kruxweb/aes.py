# Krux Web Simulator - pure-Python AES with the pycryptodome `AES.new` API
# subset that Krux's `ucryptolib` usage needs (ECB, CBC, CTR, GCM).
#
# The desktop simulator maps `ucryptolib.aes` to pycryptodome's `AES.new`;
# pycryptodome has no wasm build here, so this module reproduces its
# semantics (stateful CBC/CTR across calls, CTR nonce||counter layout,
# GCM with truncated tags) and is cross-checked against pycryptodome by
# tests/test_aes.py.

MODE_ECB = 1
MODE_CBC = 2
MODE_CTR = 6
MODE_GCM = 11

block_size = 16

# ---------------------------------------------------------------- core

_SBOX = bytearray(256)
_INV = bytearray(256)


def _init_tables():
    p = q = 1
    while True:
        # multiply p by 3
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        # divide q by 3
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ (
            ((q << 1) | (q >> 7))
            ^ ((q << 2) | (q >> 6))
            ^ ((q << 3) | (q >> 5))
            ^ ((q << 4) | (q >> 4))
        ) & 0xFF
        x = (x ^ 0x63) & 0xFF
        _SBOX[p] = x
        _INV[x] = p
        if p == 1:
            break
    _SBOX[0] = 0x63
    _INV[0x63] = 0


_init_tables()


def _xt(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1


def _mul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xt(a)
        b >>= 1
    return r


# Encryption / decryption T-tables (32-bit words, big-endian column order)
_TE = [[0] * 256 for _ in range(4)]
_TD = [[0] * 256 for _ in range(4)]
for _i in range(256):
    _s = _SBOX[_i]
    _w = (_mul(_s, 2) << 24) | (_s << 16) | (_s << 8) | _mul(_s, 3)
    _v = _INV[_i]
    _d = (_mul(_v, 14) << 24) | (_mul(_v, 9) << 16) | (_mul(_v, 13) << 8) | _mul(_v, 11)
    for _k in range(4):
        _TE[_k][_i] = ((_w >> (8 * _k)) | (_w << (32 - 8 * _k))) & 0xFFFFFFFF
        _TD[_k][_i] = ((_d >> (8 * _k)) | (_d << (32 - 8 * _k))) & 0xFFFFFFFF
_TE0, _TE1, _TE2, _TE3 = _TE
_TD0, _TD1, _TD2, _TD3 = _TD


class _Block:
    """AES block cipher on 16-byte blocks (128/192/256-bit keys)."""

    def __init__(self, key):
        key = bytes(key)
        if len(key) not in (16, 24, 32):
            raise ValueError("Incorrect AES key length (%d bytes)" % len(key))
        nk = len(key) // 4
        self.rounds = nk + 6
        total = 4 * (self.rounds + 1)
        w = [int.from_bytes(key[4 * i : 4 * i + 4], "big") for i in range(nk)]
        rcon = 1
        for i in range(nk, total):
            t = w[i - 1]
            if i % nk == 0:
                t = ((t << 8) & 0xFFFFFFFF) | (t >> 24)
                t = (
                    (_SBOX[t >> 24] << 24)
                    | (_SBOX[(t >> 16) & 0xFF] << 16)
                    | (_SBOX[(t >> 8) & 0xFF] << 8)
                    | _SBOX[t & 0xFF]
                )
                t ^= rcon << 24
                rcon = _xt(rcon)
            elif nk > 6 and i % nk == 4:
                t = (
                    (_SBOX[t >> 24] << 24)
                    | (_SBOX[(t >> 16) & 0xFF] << 16)
                    | (_SBOX[(t >> 8) & 0xFF] << 8)
                    | _SBOX[t & 0xFF]
                )
            w.append(w[i - nk] ^ t)
        self.ek = w
        # Decryption key schedule (equivalent inverse cipher)
        r = self.rounds
        dk = [0] * total
        for rnd in range(r + 1):
            for c in range(4):
                v = w[4 * (r - rnd) + c]
                if 0 < rnd < r:
                    v = (
                        _TD0[_SBOX[v >> 24]]
                        ^ _TD1[_SBOX[(v >> 16) & 0xFF]]
                        ^ _TD2[_SBOX[(v >> 8) & 0xFF]]
                        ^ _TD3[_SBOX[v & 0xFF]]
                    )
                dk[4 * rnd + c] = v
        self.dk = dk

    def encrypt(self, b):
        k = self.ek
        s0 = int.from_bytes(b[0:4], "big") ^ k[0]
        s1 = int.from_bytes(b[4:8], "big") ^ k[1]
        s2 = int.from_bytes(b[8:12], "big") ^ k[2]
        s3 = int.from_bytes(b[12:16], "big") ^ k[3]
        i = 4
        for _ in range(self.rounds - 1):
            t0 = _TE0[s0 >> 24] ^ _TE1[(s1 >> 16) & 255] ^ _TE2[(s2 >> 8) & 255] ^ _TE3[s3 & 255] ^ k[i]
            t1 = _TE0[s1 >> 24] ^ _TE1[(s2 >> 16) & 255] ^ _TE2[(s3 >> 8) & 255] ^ _TE3[s0 & 255] ^ k[i + 1]
            t2 = _TE0[s2 >> 24] ^ _TE1[(s3 >> 16) & 255] ^ _TE2[(s0 >> 8) & 255] ^ _TE3[s1 & 255] ^ k[i + 2]
            t3 = _TE0[s3 >> 24] ^ _TE1[(s0 >> 16) & 255] ^ _TE2[(s1 >> 8) & 255] ^ _TE3[s2 & 255] ^ k[i + 3]
            s0, s1, s2, s3 = t0, t1, t2, t3
            i += 4
        S = _SBOX
        out = bytearray(16)
        for j, (a, b2, c, d) in enumerate(((s0, s1, s2, s3), (s1, s2, s3, s0), (s2, s3, s0, s1), (s3, s0, s1, s2))):
            v = ((S[a >> 24] << 24) | (S[(b2 >> 16) & 255] << 16) | (S[(c >> 8) & 255] << 8) | S[d & 255]) ^ k[i + j]
            out[4 * j : 4 * j + 4] = v.to_bytes(4, "big")
        return bytes(out)

    def decrypt(self, b):
        k = self.dk
        s0 = int.from_bytes(b[0:4], "big") ^ k[0]
        s1 = int.from_bytes(b[4:8], "big") ^ k[1]
        s2 = int.from_bytes(b[8:12], "big") ^ k[2]
        s3 = int.from_bytes(b[12:16], "big") ^ k[3]
        i = 4
        for _ in range(self.rounds - 1):
            t0 = _TD0[s0 >> 24] ^ _TD1[(s3 >> 16) & 255] ^ _TD2[(s2 >> 8) & 255] ^ _TD3[s1 & 255] ^ k[i]
            t1 = _TD0[s1 >> 24] ^ _TD1[(s0 >> 16) & 255] ^ _TD2[(s3 >> 8) & 255] ^ _TD3[s2 & 255] ^ k[i + 1]
            t2 = _TD0[s2 >> 24] ^ _TD1[(s1 >> 16) & 255] ^ _TD2[(s0 >> 8) & 255] ^ _TD3[s3 & 255] ^ k[i + 2]
            t3 = _TD0[s3 >> 24] ^ _TD1[(s2 >> 16) & 255] ^ _TD2[(s1 >> 8) & 255] ^ _TD3[s0 & 255] ^ k[i + 3]
            s0, s1, s2, s3 = t0, t1, t2, t3
            i += 4
        S = _INV
        out = bytearray(16)
        for j, (a, b2, c, d) in enumerate(((s0, s3, s2, s1), (s1, s0, s3, s2), (s2, s1, s0, s3), (s3, s2, s1, s0))):
            v = ((S[a >> 24] << 24) | (S[(b2 >> 16) & 255] << 16) | (S[(c >> 8) & 255] << 8) | S[d & 255]) ^ k[i + j]
            out[4 * j : 4 * j + 4] = v.to_bytes(4, "big")
        return bytes(out)


def _xor(a, b):
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big")


# ---------------------------------------------------------------- modes


class _ECB:
    def __init__(self, cipher):
        self._c = cipher

    def encrypt(self, data):
        data = bytes(data)
        if len(data) % 16:
            raise ValueError("Data must be aligned to block boundary in ECB mode")
        return b"".join(self._c.encrypt(data[i : i + 16]) for i in range(0, len(data), 16))

    def decrypt(self, data):
        data = bytes(data)
        if len(data) % 16:
            raise ValueError("Data must be aligned to block boundary in ECB mode")
        return b"".join(self._c.decrypt(data[i : i + 16]) for i in range(0, len(data), 16))


class _CBC:
    def __init__(self, cipher, iv):
        iv = bytes(iv)
        if len(iv) != 16:
            raise ValueError("Incorrect IV length (it must be 16 bytes long)")
        self._c = cipher
        self._iv = iv
        self.iv = iv
        self._next = None

    def encrypt(self, data):
        if self._next == "decrypt":
            raise TypeError("encrypt() cannot be called after decrypt()")
        self._next = "encrypt"
        data = bytes(data)
        if len(data) % 16:
            raise ValueError("Data must be padded to 16 byte boundary in CBC mode")
        out = []
        prev = self._iv
        for i in range(0, len(data), 16):
            prev = self._c.encrypt(_xor(data[i : i + 16], prev))
            out.append(prev)
        self._iv = prev
        return b"".join(out)

    def decrypt(self, data):
        if self._next == "encrypt":
            raise TypeError("decrypt() cannot be called after encrypt()")
        self._next = "decrypt"
        data = bytes(data)
        if len(data) % 16:
            raise ValueError("Data must be padded to 16 byte boundary in CBC mode")
        out = []
        prev = self._iv
        for i in range(0, len(data), 16):
            blk = data[i : i + 16]
            out.append(_xor(self._c.decrypt(blk), prev))
            prev = blk
        self._iv = prev
        return b"".join(out)


class _Keystream:
    """Counter-mode keystream over a 16-byte counter block (nonce || ctr)."""

    def __init__(self, cipher, prefix, counter, ctr_len):
        self._c = cipher
        self._prefix = prefix
        self._ctr = counter
        self._ctr_len = ctr_len
        self._buf = b""

    def take(self, n):
        out = []
        need = n
        while need:
            if not self._buf:
                if self._ctr >= 1 << (8 * self._ctr_len):
                    raise OverflowError("The counter has wrapped around")
                blk = self._prefix + self._ctr.to_bytes(self._ctr_len, "big")
                self._ctr += 1
                self._buf = self._c.encrypt(blk)
            chunk = self._buf[:need]
            self._buf = self._buf[need:]
            out.append(chunk)
            need -= len(chunk)
        return b"".join(out)


class _CTR:
    def __init__(self, cipher, nonce, initial_value=0):
        nonce = bytes(nonce)
        if len(nonce) >= 16:
            raise ValueError("Nonce is too long")
        self.nonce = nonce
        self._ks = _Keystream(cipher, nonce, initial_value, 16 - len(nonce))

    def encrypt(self, data):
        data = bytes(data)
        if not data:
            return b""
        return _xor(data, self._ks.take(len(data)))

    decrypt = encrypt


_R = 0xE1 << 120


def _gf_mul(x, y):
    z = 0
    v = x
    for i in range(127, -1, -1):
        if (y >> i) & 1:
            z ^= v
        v = (v >> 1) ^ _R if v & 1 else v >> 1
    return z


class _GHASH:
    def __init__(self, h):
        self._h = h
        # 8-bit windowed multiplication table: tab[i][b] = H * (b << 8*(15-i)).
        # Multiplication by H is linear, so each table is filled from its 8
        # single-bit entries (128 field multiplications in total).
        self._tab = []
        for i in range(16):
            bits = [_gf_mul(h, 1 << (8 * (15 - i) + k)) for k in range(8)]
            tab = [0] * 256
            for b in range(1, 256):
                low = b & -b
                tab[b] = tab[b ^ low] ^ bits[low.bit_length() - 1]
            self._tab.append(tab)
        self._y = 0

    def update_block(self, blk16):
        x = self._y ^ int.from_bytes(blk16, "big")
        z = 0
        tab = self._tab
        for i in range(16):
            z ^= tab[i][(x >> (8 * (15 - i))) & 0xFF]
        self._y = z

    def update(self, data):
        for i in range(0, len(data), 16):
            blk = data[i : i + 16]
            if len(blk) < 16:
                blk = blk + bytes(16 - len(blk))
            self.update_block(blk)

    @property
    def value(self):
        return self._y


class _GCM:
    def __init__(self, cipher, nonce, mac_len=16):
        nonce = bytes(nonce)
        if not nonce:
            raise ValueError("Nonce cannot be empty")
        if not 4 <= mac_len <= 16:
            raise ValueError("'mac_len' must be between 4 and 16")
        self.nonce = nonce
        self._mac_len = mac_len
        self._c = cipher
        h = int.from_bytes(cipher.encrypt(bytes(16)), "big")
        if len(nonce) == 12:
            j0 = nonce + b"\x00\x00\x00\x01"
        else:
            g = _GHASH(h)
            g.update(nonce)
            g.update_block(bytes(8) + (8 * len(nonce)).to_bytes(8, "big"))
            j0 = g.value.to_bytes(16, "big")
        self._j0 = j0
        ctr = int.from_bytes(j0[12:], "big") + 1
        self._ks = _Keystream(cipher, j0[:12], ctr & 0xFFFFFFFF, 4)
        self._ghash = _GHASH(h)
        self._ct_len = 0
        self._pending = b""
        self._next = None
        self._tag = None

    def _absorb(self, ct):
        self._ct_len += len(ct)
        data = self._pending + ct
        full = len(data) - (len(data) % 16)
        if full:
            self._ghash.update(data[:full])
        self._pending = data[full:]

    def encrypt(self, data):
        if self._next == "decrypt" or self._tag is not None:
            raise TypeError("encrypt() can only be called before digest()")
        self._next = "encrypt"
        data = bytes(data)
        ct = _xor(data, self._ks.take(len(data))) if data else b""
        self._absorb(ct)
        return ct

    def decrypt(self, data):
        if self._next == "encrypt" or self._tag is not None:
            raise TypeError("decrypt() can only be called before verify()")
        self._next = "decrypt"
        data = bytes(data)
        self._absorb(data)
        return _xor(data, self._ks.take(len(data))) if data else b""

    def _compute_tag(self):
        if self._tag is None:
            if self._pending:
                self._ghash.update(self._pending)
                self._pending = b""
            self._ghash.update_block(bytes(8) + (8 * self._ct_len).to_bytes(8, "big"))
            s = self._ghash.value.to_bytes(16, "big")
            self._tag = _xor(s, self._c.encrypt(self._j0))[: self._mac_len]
        return self._tag

    def digest(self):
        if self._next == "decrypt":
            raise TypeError("digest() cannot be called when decrypting")
        return self._compute_tag()

    def verify(self, received_mac_tag):
        if self._next == "encrypt":
            raise TypeError("verify() cannot be called when encrypting")
        tag = self._compute_tag()
        received = bytes(received_mac_tag)
        diff = len(tag) ^ len(received)
        for a, b in zip(tag, received):
            diff |= a ^ b
        if diff:
            raise ValueError("MAC check failed")

    def encrypt_and_digest(self, data):
        return self.encrypt(data), self.digest()

    def decrypt_and_verify(self, data, tag):
        pt = self.decrypt(data)
        self.verify(tag)
        return pt


def new(key, mode, *args, **kwargs):
    """pycryptodome-compatible AES.new(key, mode, [iv|nonce], ...)."""
    cipher = _Block(key)
    if mode == MODE_ECB:
        if args or kwargs:
            raise TypeError("Unknown parameters for ECB mode")
        return _ECB(cipher)
    if mode == MODE_CBC:
        iv = args[0] if args else kwargs.get("iv", kwargs.get("IV"))
        if iv is None:
            raise TypeError("CBC mode needs an IV in this simulator")
        return _CBC(cipher, iv)
    if mode == MODE_CTR:
        nonce = args[0] if args else kwargs.get("nonce", b"")
        return _CTR(cipher, nonce, kwargs.get("initial_value", 0))
    if mode == MODE_GCM:
        nonce = args[0] if args else kwargs.get("nonce")
        if nonce is None:
            raise TypeError("GCM mode needs a nonce in this simulator")
        return _GCM(cipher, nonce, kwargs.get("mac_len", 16))
    raise ValueError("Mode not supported: %r" % (mode,))
