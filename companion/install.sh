#!/usr/bin/env bash
#
# Install the bitComposer companion player stack: D-Bus daemon, KDE Plasma
# widget, and the two helper scripts the widget shells out to.
#
# Generated music is NOT part of this repo and never goes in it. Tracks live in
# $MUSIC_DIR (default ~/Music/Chiptune), which this script creates but never
# writes to or clears.
#
# Idempotent: safe to re-run to pick up changes.
#
#   ./companion/install.sh              install everything
#   ./companion/install.sh --check      report what is installed, change nothing
#   ./companion/install.sh --uninstall  remove everything except generated music
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

BIN_DIR="$HOME/.local/bin"
UNIT_DIR="$HOME/.config/systemd/user"
PLASMOID_DIR="$HOME/.local/share/plasma/plasmoids/org.kde.plasma.cyberpunkchiptune"
MUSIC_DIR="${BITCOMPOSER_MUSIC_DIR:-$HOME/Music/Chiptune}"
SERVICE="cyberpunk-chiptune-daemon.service"

# The .pth makes bitcomposer importable by the *system* python3 without pip.
# See docs/INSTALL.md — this path carries the Python minor version and must be
# recreated after a Python upgrade.
PTH_FILE="$(python3 -m site --user-site)/bitcomposer.pth"

say()  { printf '  %s\n' "$*"; }
head_() { printf '\n== %s\n' "$*"; }

# ── Checks ────────────────────────────────────────────────────────────────────

check_deps() {
    head_ "Dependencies"
    local missing=0

    # The daemon dlopens this by SONAME via ctypes, so test it the same way.
    # Do NOT use `ldconfig -p` here: ldconfig lives in /sbin and is absent from a
    # normal user PATH, so it fails silently and reports a false negative.
    if python3 -c "import ctypes; ctypes.CDLL('libopenmpt.so.0')" 2>/dev/null; then
        say "libopenmpt.so.0  ok"
    else
        say "libopenmpt.so.0  MISSING  (apt install libopenmpt0)"; missing=1
    fi

    for cmd in python3 qdbus6 paplay systemctl; do
        if command -v "$cmd" >/dev/null 2>&1; then
            say "$cmd  ok"
        else
            say "$cmd  MISSING"; missing=1
        fi
    done

    for mod in dbus gi; do
        if python3 -c "import $mod" 2>/dev/null; then
            say "python3-$mod  ok"
        else
            say "python3-$mod  MISSING  (apt install python3-$mod)"; missing=1
        fi
    done

    case ":$PATH:" in
        *":$BIN_DIR:"*) say "$BIN_DIR on PATH  ok" ;;
        *) say "$BIN_DIR NOT on PATH — the widget shells out by bare name"; missing=1 ;;
    esac

    return $missing
}

do_check() {
    check_deps || true

    head_ "Installed components"
    for f in bitcomposer-generate.sh bitcomposer-master.sh cyberpunk-chiptune-daemon.py; do
        [ -x "$BIN_DIR/$f" ] && say "$f  ok" || say "$f  missing"
    done
    [ -f "$UNIT_DIR/$SERVICE" ] && say "$SERVICE  ok" || say "$SERVICE  missing"
    [ -f "$PLASMOID_DIR/contents/ui/main.qml" ] && say "plasmoid  ok" || say "plasmoid  missing"
    [ -d "$MUSIC_DIR" ] && say "$MUSIC_DIR  ok" || say "$MUSIC_DIR  missing"

    head_ "Python import"
    if [ -f "$PTH_FILE" ]; then
        say ".pth  $PTH_FILE -> $(cat "$PTH_FILE")"
    else
        say ".pth  missing"
    fi
    if (cd / && env -u PYTHONPATH python3 -c "import bitcomposer" 2>/dev/null); then
        say "import bitcomposer (no PYTHONPATH, from /)  ok"
    else
        say "import bitcomposer  FAILS — GENERATE button and autogen will not work"
    fi

    head_ "Daemon"
    systemctl --user is-enabled "$SERVICE" 2>/dev/null | sed 's/^/  enabled: /' || say "enabled: no"
    systemctl --user is-active  "$SERVICE" 2>/dev/null | sed 's/^/  active:  /' || say "active:  no"
}

# ── Install ───────────────────────────────────────────────────────────────────

do_install() {
    if ! check_deps; then
        printf '\n  Some dependencies are missing. Continuing anyway — install them\n'
        printf '  and re-run, or the daemon will fail to start.\n'
    fi

    head_ "Installing"
    install -Dm755 "$HERE/bin/bitcomposer-generate.sh"      "$BIN_DIR/bitcomposer-generate.sh"
    install -Dm755 "$HERE/bin/bitcomposer-master.sh"        "$BIN_DIR/bitcomposer-master.sh"
    install -Dm755 "$HERE/daemon/cyberpunk-chiptune-daemon.py" "$BIN_DIR/cyberpunk-chiptune-daemon.py"
    say "helper scripts + daemon -> $BIN_DIR"

    # The unit carries Environment=PYTHONPATH as a fallback for the daemon
    # specifically. It is redundant with the .pth below but harmless, and having
    # it in the repo means this file is no longer a local-only modification.
    install -Dm644 "$HERE/daemon/$SERVICE" "$UNIT_DIR/$SERVICE"
    say "$SERVICE -> $UNIT_DIR"

    mkdir -p "$PLASMOID_DIR"
    cp -r "$HERE/plasmoid/." "$PLASMOID_DIR/"
    say "plasmoid -> $PLASMOID_DIR"

    mkdir -p "$MUSIC_DIR"
    say "music dir -> $MUSIC_DIR  (contents never touched by this script)"

    mkdir -p "$(dirname "$PTH_FILE")"
    printf '%s\n' "$REPO" > "$PTH_FILE"
    say ".pth -> $PTH_FILE  ($REPO)"

    # main.qml hardcodes the music dir; patch it if this is not the same user.
    local qml="$PLASMOID_DIR/contents/ui/main.qml"
    if ! grep -q "\"$MUSIC_DIR/\"" "$qml" 2>/dev/null; then
        sed -i "s|readonly property string musicDir: \".*\"|readonly property string musicDir: \"$MUSIC_DIR/\"|" "$qml"
        say "patched musicDir in main.qml -> $MUSIC_DIR/"
    fi

    head_ "Starting daemon"
    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE"
    say "$(systemctl --user is-active "$SERVICE")"

    head_ "Verify"
    if (cd / && env -u PYTHONPATH python3 -c "import bitcomposer" 2>/dev/null); then
        say "import bitcomposer  ok"
    else
        say "import bitcomposer  FAILS — check $PTH_FILE"
    fi

    cat <<EOF

Add the widget: right-click panel -> Add Widgets -> "Cyberpunk Chiptune Player".
After editing main.qml on a running shell: systemctl --user restart plasma-plasmashell

Generated music goes to $MUSIC_DIR, never into the repo.
EOF
}

# ── Uninstall ─────────────────────────────────────────────────────────────────

do_uninstall() {
    head_ "Removing"
    systemctl --user disable --now "$SERVICE" 2>/dev/null || true
    rm -f "$BIN_DIR/bitcomposer-generate.sh" \
          "$BIN_DIR/bitcomposer-master.sh" \
          "$BIN_DIR/cyberpunk-chiptune-daemon.py" \
          "$UNIT_DIR/$SERVICE" \
          "$PTH_FILE"
    rm -rf "$PLASMOID_DIR"
    systemctl --user daemon-reload
    say "removed scripts, daemon, unit, plasmoid and .pth"
    say "left alone: $MUSIC_DIR and everything in it"
}

case "${1:-}" in
    --check)     do_check ;;
    --uninstall) do_uninstall ;;
    "")          do_install ;;
    *) printf 'usage: %s [--check|--uninstall]\n' "$0" >&2; exit 2 ;;
esac
