#!/bin/bash
# Write channel volumes into an IT file header.
# Usage: bitcomposer-master.sh <filepath> <vol0> <vol1> ... <volN>
#
# Each volume is 0-64 and lands at header byte 128+i (the per-channel volume
# block). Only the channels given are written; the rest of the block is left
# as the generator wrote it. This persists a mix; the live mix is set over
# D-Bus (SetChannelVolume) and does not need the track restarted, so this
# script no longer stops and reloads playback. The daemon's folder monitor
# notices the write and rescans on its own.

FILE="$1"
shift

if [ ! -f "$FILE" ] || [ $# -lt 1 ] || [ $# -gt 64 ]; then
    echo "ERROR" >&2
    exit 1
fi

python3 - "$FILE" "$@" <<'PY' || { echo "ERROR" >&2; exit 1; }
import sys
path = sys.argv[1]
vals = bytes(max(0, min(64, int(v))) for v in sys.argv[2:])
with open(path, "r+b") as f:
    if f.read(4) != b"IMPM":
        sys.exit("not an IT module")
    f.seek(128)
    f.write(vals)
PY

echo "OK"
