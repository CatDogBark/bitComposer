#!/bin/bash
# Generate a chiptune track, rescan daemon playlist, and play the new track.
# Usage: bitcomposer-generate.sh [--auto] [--tempo T] [--energy E] ...

BUSNAME="org.mpris.MediaPlayer2.CyberpunkChiptune"
BUSPATH="/org/mpris/MediaPlayer2"

# Check for --auto flag
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
OUTPATH="$HOME/Music/Chiptune/$FILENAME"

# Pass remaining arguments through to bitcomposer CLI
python3 -m bitcomposer.cli "${ARGS[@]}" -o "$OUTPATH" || exit 1

# Prune old auto files if this is an auto-generated track
if [ "$AUTO" = true ]; then
    MAX=10
    AUTOFILES=($(ls -1t "$HOME/Music/Chiptune"/bitcomposer_auto_*.it 2>/dev/null))
    if [ ${#AUTOFILES[@]} -gt $MAX ]; then
        for f in "${AUTOFILES[@]:$MAX}"; do
            rm -f "$f"
        done
    fi
fi

# Rescan daemon playlist
qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.Rescan"

# Find the new track index in playlist
PLAYLIST=$(qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.GetPlaylist")
INDEX=$(echo "$PLAYLIST" | grep -n "$FILENAME" | cut -d: -f1)

if [ -n "$INDEX" ]; then
    qdbus6 "$BUSNAME" "$BUSPATH" "${BUSNAME}.PlayIndex" $((INDEX - 1))
fi

echo "GENERATED:$FILENAME"
