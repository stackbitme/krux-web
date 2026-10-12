# Krux Web Simulator - `uUR` module for Pyodide.
#
# Same module surface as Krux's native binding (bc-ur/python/uUR.c), backed by
# the very same bc-ur C sources compiled to wasm (ur.wasm). The JS side is
# registered by the worker as the `_kxur` module (see js/urwasm.js).
#
#   UR(type, cbor)            -> .type, .cbor, == / hash by value
#   URDecoder()               -> receive_part, estimated_percent_complete,
#                                .result, .state, .expected_part_count,
#                                .processed_parts_count
#   UREncoder(ur, max_fragment_len, first_seq_num=0, min_fragment_len=10)
#                             -> next_part, is_complete, is_single_part,
#                                .fountain_encoder(.seq_len())
#   Types.*                   -> CBOR payload codecs + CRYPTO_* constants
#   DECODER_*                 -> decoder states

import _kxur as _w
from pyodide.ffi import to_js as _to_js


def _buf(data):
    if isinstance(data, str):
        raise TypeError("a bytes-like object is required, not 'str'")
    return _to_js(bytes(data))


def _pybytes(js):
    return None if js is None else bytes(js.to_py())


DECODER_OK = _w.constInt(10)
DECODER_PROCESSING = _w.constInt(11)
DECODER_NO_RESULT = _w.constInt(12)
DECODER_ERR_INVALID_SCHEME = _w.constInt(13)
DECODER_ERR_INVALID_TYPE = _w.constInt(14)
DECODER_ERR_INVALID_PATH_LENGTH = _w.constInt(15)
DECODER_ERR_INVALID_SEQUENCE_COMPONENT = _w.constInt(16)
DECODER_ERR_INVALID_FRAGMENT = _w.constInt(17)
DECODER_ERR_INVALID_PART = _w.constInt(18)
DECODER_ERR_INVALID_CHECKSUM = _w.constInt(19)
DECODER_ERR_MEMORY = _w.constInt(20)
DECODER_ERR_NULL_POINTER = _w.constInt(21)


class UR:
    """Uniform Resource: a typed CBOR payload."""

    def __init__(self, *args, **kwargs):
        if kwargs:
            raise TypeError("UR() takes no keyword arguments")
        if len(args) != 2:
            raise TypeError("UR() takes exactly 2 arguments")
        ur_type, cbor = args
        if not isinstance(ur_type, str):
            raise TypeError("type must be str")
        cbor = bytes(cbor)
        if not _w.isUrType(ur_type):
            raise ValueError(
                "invalid UR type (want [a-z0-9-], no leading/trailing '-')"
            )
        if len(cbor) == 0:
            raise ValueError("cbor must not be empty")
        h = _w.urNew(ur_type, _buf(cbor))
        if not h:
            raise MemoryError("Failed to create UR object")
        self._free()
        self._h = h

    @classmethod
    def _from_handle(cls, h):
        obj = cls.__new__(cls)
        obj._h = h
        return obj

    def _free(self):
        h = getattr(self, "_h", 0)
        if h:
            _w.urFree(h)
        self._h = 0

    def __del__(self):
        self._free()

    @property
    def type(self):
        h = getattr(self, "_h", 0)
        return _w.urType(h) if h else None

    @property
    def cbor(self):
        h = getattr(self, "_h", 0)
        return _pybytes(_w.urCbor(h)) if h else None

    def __eq__(self, other):
        if not isinstance(other, UR):
            return NotImplemented
        a, b = getattr(self, "_h", 0), getattr(other, "_h", 0)
        if not a or not b:
            return a == b
        return self.type == other.type and self.cbor == other.cbor

    def __ne__(self, other):
        r = self.__eq__(other)
        return r if r is NotImplemented else not r

    def __hash__(self):
        if not getattr(self, "_h", 0):
            return 0
        return hash((self.type, self.cbor))

    def __repr__(self):
        if getattr(self, "_h", 0):
            return "UR(type='%s')" % self.type
        return "UR(invalid)"


class URDecoder:
    """Multi-part BC-UR fountain decoder."""

    def __init__(self):
        h = _w.decNew()
        if not h:
            raise MemoryError("Failed to create URDecoder")
        old = getattr(self, "_h", 0)
        if old:
            _w.decFree(old)
        self._h = h

    def __del__(self):
        h = getattr(self, "_h", 0)
        if h:
            _w.decFree(h)
        self._h = 0

    def receive_part(self, part):
        h = getattr(self, "_h", 0)
        if not h:
            raise RuntimeError("URDecoder is closed")
        if isinstance(part, (bytes, bytearray)):
            part = bytes(part).decode("utf-8", "surrogateescape")
        elif not isinstance(part, str):
            raise TypeError(
                "part must be str or bytes, not %s" % type(part).__name__
            )
        return _w.decReceive(h, part)

    def estimated_percent_complete(self, weight_mixed_frames=False):
        h = getattr(self, "_h", 0)
        if not h:
            return 0.0
        return float(_w.decPct(h, bool(weight_mixed_frames)))

    @property
    def result(self):
        h = getattr(self, "_h", 0)
        if not h:
            return None
        rh = _w.decResult(h)
        if not rh:
            return None
        return UR._from_handle(rh)

    @property
    def state(self):
        h = getattr(self, "_h", 0)
        if not h:
            return DECODER_ERR_NULL_POINTER
        return _w.decState(h)

    @property
    def expected_part_count(self):
        h = getattr(self, "_h", 0)
        return _w.decExpected(h) if h else 0

    @property
    def processed_parts_count(self):
        h = getattr(self, "_h", 0)
        return _w.decProcessed(h) if h else 0

    def __repr__(self):
        h = getattr(self, "_h", 0)
        if not h:
            return "URDecoder(closed)"
        return "URDecoder(state=%d, progress=%d%%)" % (
            self.state,
            int(self.estimated_percent_complete() * 100.0),
        )


class FountainEncoder:
    """View over a UREncoder's fountain encoder."""

    def __init__(self, parent):
        self._parent = parent

    def seq_len(self):
        h = getattr(self._parent, "_h", 0)
        if h and _w.encHasFountain(h):
            return _w.encSeqLen(h)
        return 0


class UREncoder:
    """Multi-part BC-UR fountain encoder."""

    def __init__(self, ur, max_fragment_len, first_seq_num=0, min_fragment_len=10):
        if not isinstance(ur, UR):
            raise TypeError("First argument must be a UR object")
        if not getattr(ur, "_h", 0):
            raise ValueError("Invalid UR object")
        max_fragment_len = int(max_fragment_len)
        min_fragment_len = int(min_fragment_len)
        first_seq_num = int(first_seq_num)
        if (
            max_fragment_len < 10
            or max_fragment_len > 2048
            or min_fragment_len < 1
            or min_fragment_len > max_fragment_len
        ):
            raise ValueError("fragment_len out of range (min 1..max, max 10..2048)")
        if first_seq_num < 0 or first_seq_num > 0xFFFFFFFF:
            raise ValueError("first_seq_num out of range (0..4294967295)")
        cbor = ur.cbor
        if len(cbor) < min_fragment_len:
            raise ValueError("UR payload is shorter than min_fragment_len")
        h = _w.encNew(
            ur.type, _buf(cbor), max_fragment_len, first_seq_num, min_fragment_len
        )
        if not h:
            raise MemoryError("Failed to create UREncoder")
        old = getattr(self, "_h", 0)
        if old:
            _w.encFree(old)
        self._h = h

    def __del__(self):
        h = getattr(self, "_h", 0)
        if h:
            _w.encFree(h)
        self._h = 0

    def next_part(self):
        h = getattr(self, "_h", 0)
        if not h:
            raise RuntimeError("UREncoder is closed")
        part = _w.encNext(h)
        if part is None:
            raise RuntimeError("Failed to generate next part")
        return part

    def is_complete(self):
        h = getattr(self, "_h", 0)
        return bool(_w.encComplete(h)) if h else False

    def is_single_part(self):
        h = getattr(self, "_h", 0)
        return bool(_w.encSingle(h)) if h else False

    @property
    def fountain_encoder(self):
        h = getattr(self, "_h", 0)
        if not h or not _w.encHasFountain(h):
            return None
        return FountainEncoder(self)

    def __repr__(self):
        h = getattr(self, "_h", 0)
        if not h:
            return "UREncoder(invalid)"
        return "UREncoder(seq_len=%d, complete=%s)" % (
            _w.encSeqLen(h),
            "True" if self.is_complete() else "False",
        )


class _Types:
    """BC-UR typed CBOR payload codecs (uUR.Types)."""

    CRYPTO_PSBT_TAG = _w.constInt(0)
    CRYPTO_BIP39_TAG = _w.constInt(1)
    CRYPTO_ACCOUNT_TAG = _w.constInt(2)
    CRYPTO_OUTPUT_TAG = _w.constInt(3)
    CRYPTO_PSBT_TYPE = _w.constStr(0)
    CRYPTO_BIP39_TYPE = _w.constStr(1)
    CRYPTO_OUTPUT_TYPE = _w.constStr(2)
    CRYPTO_ACCOUNT_TYPE = _w.constStr(3)

    @staticmethod
    def bytes_from_cbor(cbor):
        out = _w.bytesFromCbor(_buf(cbor))
        if out is None:
            raise ValueError("Failed to decode Bytes from CBOR")
        return _pybytes(out)

    @staticmethod
    def bytes_to_cbor(data):
        out = _w.bytesToCbor(_buf(data))
        if out is None:
            raise RuntimeError("Failed to encode Bytes to CBOR")
        return _pybytes(out)

    @staticmethod
    def psbt_from_cbor(cbor):
        out = _w.psbtFromCbor(_buf(cbor))
        if out is None:
            raise ValueError("Failed to decode PSBT from CBOR")
        return _pybytes(out)

    @staticmethod
    def psbt_to_cbor(data):
        out = _w.psbtToCbor(_buf(data))
        if out is None:
            raise RuntimeError("Failed to encode PSBT to CBOR")
        return _pybytes(out)

    @staticmethod
    def bip39_words_from_cbor(cbor):
        out = _w.bip39WordsFromCbor(_buf(cbor))
        if out is None:
            raise ValueError("Failed to decode BIP39 from CBOR")
        return out.split(" ") if out else []

    @staticmethod
    def output_from_cbor(cbor):
        out = _w.outputFromCbor(_buf(cbor))
        if out is None:
            raise ValueError("Failed to decode Output from CBOR")
        return out

    @staticmethod
    def output_from_cbor_account(cbor):
        out = _w.outputFromCborAccount(_buf(cbor))
        if out is None:
            raise ValueError("Failed to extract output descriptor from Account CBOR")
        return out


Types = _Types
