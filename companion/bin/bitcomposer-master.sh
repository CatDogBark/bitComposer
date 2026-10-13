#!/bin/bash
# Write channel volumes into an IT file header and reload playback.
# Usage: bitcomposer-master.sh <filepath> <vol0> <vol1> ... <volN>
#
# Each volume is 0-64 and lands at header byte 128+i (the per-channel volume
# block). Only the channels given are written; the rest of the block is left
# as the generator wrote it. The old version zero-padded to 64 channels, which
# muted any channel the caller did not know about.

BUSNAME="org.mpris.MediaPlayer2.CyberpunkChiptune"
BUSPATH="/org/mpris/MediaPlayer2"

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

# Stop, rescan, replay the same track so the change is audible at once.
IDX=$(qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.GetState" 2>/dev/null | cut -d'|' -f12)
qdbus6 "$BUSNAME" "$BUSPATH" org.mpris.MediaPlayer2.Player.Stop >/dev/null 2>&1
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.Rescan" >/dev/null 2>&1
sleep 0.2
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.PlayIndex" "${IDX:-0}" >/dev/null 2>&1

echo "OK"
