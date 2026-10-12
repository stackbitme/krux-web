"""Converts a BDF bitmap font into the compact font file used by the web
simulator (.kfnt). Glyph boxes (BBX) are kept so the runtime can lay text
out exactly like pygame.freetype does in the desktop simulator.

.kfnt layout (little endian):
    b"KFN2" | u16 cell_w | u16 cell_h | u16 ascent | u32 default_cp | u32 count
    count x record: u32 cp | u8 w | u8 h | i8 xoff | i8 yoff | u8 dwidth | u8 0 | u32 offset
    bitmap blob: for each glyph, h rows of ceil(w/8) bytes, MSB first
"""
import struct
import sys


def parse_bdf(path):
    glyphs = {}
    info = {"default": None}
    with open(path, "r", encoding="latin-1") as f:
        lines = f.read().splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("FONT_ASCENT"):
            info["ascent"] = int(line.split()[1])
        elif line.startswith("FONT_DESCENT"):
            info["descent"] = int(line.split()[1])
        elif line.startswith("DEFAULT_CHAR"):
            info["default"] = int(line.split()[1])
        elif line.startswith("FONTBOUNDINGBOX"):
            info["bbx"] = tuple(int(v) for v in line.split()[1:5])
        elif line.startswith("STARTCHAR"):
            enc = bbx = dwidth = None
            rows = []
            i += 1
            while not lines[i].startswith("ENDCHAR"):
                l = lines[i]
                if l.startswith("ENCODING"):
                    enc = int(l.split()[1])
                elif l.startswith("BBX"):
                    bbx = tuple(int(v) for v in l.split()[1:5])
                elif l.startswith("DWIDTH"):
                    dwidth = int(l.split()[1])
                elif l.startswith("BITMAP"):
                    i += 1
                    while not lines[i].startswith("ENDCHAR"):
                        rows.append(lines[i].strip())
                        i += 1
                    break
                i += 1
            if enc is not None and enc >= 0 and bbx is not None:
                w = bbx[0]
                bpr = (w + 7) // 8
                data = bytearray()
                for r in range(bbx[1]):
                    hexrow = rows[r] if r < len(rows) else ""
                    v = int(hexrow, 16) if hexrow else 0
                    nbits = len(hexrow) * 4
                    # normalise to bpr bytes, MSB first
                    if nbits > bpr * 8:
                        v >>= nbits - bpr * 8
                    elif nbits < bpr * 8:
                        v <<= bpr * 8 - nbits
                    data += v.to_bytes(bpr, "big")
                glyphs[enc] = (bbx, dwidth if dwidth is not None else bbx[0], bytes(data))
        i += 1
    return glyphs, info


def write_kfnt(path, dest):
    glyphs, info = parse_bdf(path)
    cps = sorted(glyphs)
    cell_w = info["bbx"][0]
    cell_h = info["ascent"] + info["descent"]
    default = info["default"] if info["default"] in glyphs else 0xFFFFFFFF
    head = bytearray(b"KFN2")
    head += struct.pack("<HHHII", cell_w, cell_h, info["ascent"], default, len(cps))
    recs = bytearray()
    blob = bytearray()
    for cp in cps:
        (w, h, xoff, yoff), dw, data = glyphs[cp]
        recs += struct.pack("<IBBbbBBI", cp, w, h, xoff, yoff, dw, 0, len(blob))
        blob += data
    out = head + recs + blob
    with open(dest, "wb") as f:
        f.write(out)
    return len(cps), cell_w, cell_h, len(out)


if __name__ == "__main__":
    n, w, h, size = write_kfnt(sys.argv[1], sys.argv[2])
    print("%s: %d glyphs, cell %dx%d, %d bytes" % (sys.argv[2], n, w, h, size))
