"""Cross-checks runtime/kruxweb/aes.py against pycryptodome (native CPython)."""
import os, random, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "runtime"))
from kruxweb import aes as K
from Crypto.Cipher import AES as P

rnd = random.Random(1)
def rb(n): return bytes(rnd.getrandbits(8) for _ in range(n))

t = time.time()
n = 0
for keylen in (16, 24, 32):
    for trial in range(40):
        key = rb(keylen)
        # ECB
        data = rb(16 * rnd.randint(1, 6))
        assert K.new(key, K.MODE_ECB).encrypt(data) == P.new(key, P.MODE_ECB).encrypt(data)
        assert K.new(key, K.MODE_ECB).decrypt(data) == P.new(key, P.MODE_ECB).decrypt(data)
        # CBC (stateful across calls)
        iv = rb(16)
        a, b = K.new(key, K.MODE_CBC, iv), P.new(key, P.MODE_CBC, iv)
        for _ in range(3):
            d = rb(16 * rnd.randint(1, 4))
            assert a.encrypt(d) == b.encrypt(d)
        a, b = K.new(key, K.MODE_CBC, iv), P.new(key, P.MODE_CBC, iv)
        d = rb(48)
        assert a.decrypt(d) == b.decrypt(d)
        # CTR with 12-byte nonce, uneven chunks
        nonce = rb(12)
        a, b = K.new(key, K.MODE_CTR, nonce=nonce), P.new(key, P.MODE_CTR, nonce=nonce)
        for _ in range(4):
            d = rb(rnd.randint(1, 50))
            assert a.encrypt(d) == b.encrypt(d)
        # GCM with truncated tags, positional nonce like Krux does
        for mac_len in (4, 8, 16):
            nonce = rb(12)
            d = rb(rnd.randint(1, 100))
            a, b = K.new(key, K.MODE_GCM, nonce, mac_len=mac_len), P.new(key, P.MODE_GCM, nonce, mac_len=mac_len)
            ca, cb = a.encrypt(d), b.encrypt(d)
            assert ca == cb
            ta, tb = a.digest(), b.digest()
            assert ta == tb, (ta.hex(), tb.hex())
            x = K.new(key, K.MODE_GCM, nonce, mac_len=mac_len)
            assert x.decrypt(ca) == d
            x.verify(ta)
            y = K.new(key, K.MODE_GCM, nonce, mac_len=mac_len)
            y.decrypt(ca)
            try:
                y.verify(bytes(len(ta)))
                raise AssertionError("bad tag accepted")
            except ValueError:
                pass
        n += 1
print("aes ok", n, "trials, %.2fs" % (time.time() - t))
