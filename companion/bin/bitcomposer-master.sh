#!/bin/bash
# Write channel volumes to an IT file header and reload playback.
# Usage: bitcomposer-master.sh <filepath> <vol0> <vol1> ... <vol11>
# Volumes are 0-64, written to IT header bytes 128-139.

BUSNAME="org.mpris.MediaPlayer2.CyberpunkChiptune"
BUSPATH="/org/mpris/MediaPlayer2"

FILE="$1"
shift

if [ ! -f "$FILE" ] || [ $# -lt 12 ]; then
    echo "ERROR" >&2
    exit 1
fi

# Build binary string and write at offset 128
python3 -c "
import sys
vals = [max(0, min(64, int(v))) for v in sys.argv[1:13]]
# Pad to 64 bytes (full channel volume block) - remaining channels disabled
vals.extend([0] * (64 - len(vals)))
with open(sys.argv[13], 'r+b') as f:
    f.seek(128)
    f.write(bytes(vals))
" "$@" "$FILE"

if [ $? -ne 0 ]; then
    echo "ERROR"
    exit 1
fi

# Stop, rescan, replay the same track
IDX=$(qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.GetState" 2>/dev/null | cut -d'|' -f12)
qdbus6 "$BUSNAME" "$BUSPATH" org.mpris.MediaPlayer2.Player.Stop 2>/dev/null
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.Rescan" 2>/dev/null
sleep 0.2
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.PlayIndex" "${IDX:-0}" 2>/dev/null

echo "OK"
