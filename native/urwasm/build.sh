#!/usr/bin/env bash
# Compiles Krux's bc-ur C library (the same sources the firmware uses) to a
# standalone wasm32 module, with a tiny bundled libc. Needs clang + wasm-ld.
#
#   ./build.sh <krux-repo-dir> <output.wasm>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
KRUX="$(cd "$1" && pwd)"
OUT="$2"
UR="$KRUX/firmware/MaixPy/components/micropython/port/src/bc-ur"
SRCS=$(ls "$UR"/src/*.c "$UR"/src/types/*.c "$UR"/src/sha256/sha256.c)
clang --target=wasm32 -O2 -std=c11 -ffreestanding -nostdlib \
  -fno-builtin-malloc -fno-builtin-free -fno-builtin-calloc -fno-builtin-realloc \
  -isystem "$HERE/libc/include" -I "$UR" -I "$UR/src" \
  -Wno-unused-parameter -Wno-incompatible-library-redeclaration \
  -Wl,--no-entry -Wl,--export=__heap_base -Wl,-z,stack-size=1048576 \
  -Wl,--initial-memory=4194304 -Wl,--max-memory=268435456 \
  -o "$OUT" "$HERE/libc/libc.c" "$HERE/glue.c" $SRCS
echo "built $OUT ($(stat -c %s "$OUT") bytes)"
