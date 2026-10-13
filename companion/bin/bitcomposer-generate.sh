#!/bin/bash
# Generate a chiptune track, rescan daemon playlist, and play the new track.
# Usage: bitcomposer-generate.sh [--auto] [--tempo T] [--energy E] ...
#
# --auto only changes the filename prefix. Pruning of old auto-generated
# tracks is done by the daemon on every Rescan (AUTOGEN_MAX there), so it
# happens in exactly one place.

BUSNAME="org.mpris.MediaPlayer2.CyberpunkChiptune"
BUSPATH="/org/mpris/MediaPlayer2"
MUSIC_DIR="${BITCOMPOSER_MUSIC_DIR:-$HOME/Music/Chiptune}"

AUTO=false
ARGS=()
for arg in "$@"; do
    if [ "$arg" = "--auto" ]; then
        AUTO=true
    else
        ARGS+=("$arg")
    fi
done

TS=$(date +%s)
if [ "$AUTO" = true ]; then
    FILENAME="bitcomposer_auto_${TS}.it"
else
    FILENAME="bitcomposer_${TS}.it"
fi
mkdir -p "$MUSIC_DIR"
OUTPATH="$MUSIC_DIR/$FILENAME"

python3 -m bitcomposer.cli "${ARGS[@]}" -o "$OUTPATH" || exit 1

# Rescan daemon playlist, then play the new track by its list position.
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.Rescan" >/dev/null 2>&1
INDEX=$(qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.GetPlaylist" 2>/dev/null \
        | grep -n -F -x "$FILENAME" | cut -d: -f1)

if [ -n "$INDEX" ]; then
    qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.PlayIndex" $((INDEX - 1)) >/dev/null 2>&1
fi

echo "GENERATED:$FILENAME"
