#!/bin/bash
# Generate a chiptune track, rescan daemon playlist, and play the new track.
# Usage: bitcomposer-generate.sh [--auto] [--tempo T] [--energy E] ...
#
# Files are named after the song's title ("Haunted Orchard.it"), so what the
# player shows is what the folder shows. --auto appends " (auto)", which marks
# the file for the daemon's pruning (AUTOGEN_MAX, on every Rescan).

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

mkdir -p "$MUSIC_DIR"
SUFFIX=""
[ "$AUTO" = true ] && SUFFIX=" (auto)"

OUT=$(python3 -m bitcomposer.cli "${ARGS[@]}" -d "$MUSIC_DIR" --suffix "$SUFFIX") || exit 1
OUTPATH=$(printf '%s\n' "$OUT" | sed -n 's/^Generated: //p' | tail -1)
FILENAME=$(basename "$OUTPATH")

# Rescan daemon playlist, then play the new track by its list position.
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.Rescan" >/dev/null 2>&1
INDEX=$(qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.GetPlaylist" 2>/dev/null \
        | grep -n -F -x "$FILENAME" | cut -d: -f1)

if [ -n "$INDEX" ]; then
    qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.PlayIndex" $((INDEX - 1)) >/dev/null 2>&1
fi

echo "GENERATED:$FILENAME"
