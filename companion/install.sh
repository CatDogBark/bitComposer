#!/usr/bin/env bash
#
# Install the bitComposer companion player stack: D-Bus daemon, KDE Plasma
# widget, and the two helper scripts the widget shells out to.
#
# The generator itself is installed separately, with pipx:
#     pipx install bitcomposer
# The daemon and the GENERATE button run the bitcomposer command on PATH.
# A developer who wants generation to follow the checkout this script is run
# from installs with --dev instead: that points the system python3 at the
# checkout (a .pth file and a systemd drop-in) and the companion falls back
# to "python3 -m bitcomposer.cli" when no command is installed.
#
# Generated music is NOT part of this repo and never goes in it. Tracks live in
# $MUSIC_DIR (default ~/Music/Chiptune), which this script creates but never
# writes to or clears.
#
# Idempotent: safe to re-run to pick up changes.
#
#   ./companion/install.sh              install everything (generator from pipx)
#   ./companion/install.sh --dev        install, generation follows this checkout
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

# Developer mode: the .pth makes the checkout importable by the *system*
# python3 without pip, and the drop-in gives the daemon the same path. Both
# carry the Python minor version or the checkout path; see docs/INSTALL.md.
PTH_FILE="$(python3 -m site --user-site)/bitcomposer.pth"
DROPIN_DIR="$UNIT_DIR/$SERVICE.d"
DROPIN="$DROPIN_DIR/dev.conf"

say()  { printf '  %s\n' "$*"; }
head_() { printf '\n== %s\n' "$*"; }

# ── The generator ─────────────────────────────────────────────────────────────

# Which generator the daemon and the GENERATE button will run: the
# bitcomposer command on PATH first, else the package on the import path.
# Run from / with PYTHONPATH cleared, so neither the caller's cwd nor its
# environment can mask a broken install.
check_generator() {
    local exe ver got
    if exe="$(command -v bitcomposer 2>/dev/null)"; then
        ver="$("$exe" --version 2>/dev/null || echo "broken")"
        say "bitcomposer -> $exe  ($ver)"
        if [ "$DEV" = 1 ]; then
            say "  NOTE: the command wins over the checkout; for generation to"
            say "  follow this checkout:  pipx uninstall bitcomposer"
        fi
        return 0
    fi
    got="$(cd / && env -u PYTHONPATH python3 -c \
        'import bitcomposer, os; print(os.path.dirname(os.path.dirname(bitcomposer.__file__)))' \
        2>/dev/null)" || got=""
    if [ -n "$got" ]; then
        say "no bitcomposer command; python3 -m bitcomposer.cli -> $got"
        if [ "$DEV" = 1 ] && [ "$got" != "$REPO" ]; then
            say "  WRONG SOURCE — expected $REPO"
            say "  a pip install shadows the .pth; remove it with:"
            say "    python3 -m pip uninstall -y --break-system-packages bitcomposer"
            return 1
        fi
        return 0
    fi
    say "generator MISSING — GENERATE button and autogen will not work"
    say "  install it:  pipx install bitcomposer   (pipx: apt install pipx)"
    say "  or, to run this checkout:  ./companion/install.sh --dev"
    return 1
}

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

    # The widget shells out by bare name, and pipx puts bitcomposer here too.
    case ":$PATH:" in
        *":$BIN_DIR:"*) say "$BIN_DIR on PATH  ok" ;;
        *) say "$BIN_DIR NOT on PATH — the widget shells out by bare name"; missing=1 ;;
    esac

    check_generator || missing=1
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

    head_ "Developer mode"
    if [ -f "$PTH_FILE" ]; then
        say ".pth  $PTH_FILE -> $(cat "$PTH_FILE")"
    else
        say ".pth  none (not in developer mode)"
    fi
    if [ -f "$DROPIN" ]; then
        say "daemon drop-in  $DROPIN -> $(sed -n 's/^Environment=PYTHONPATH=//p' "$DROPIN")"
    else
        say "daemon drop-in  none"
    fi

    head_ "Daemon"
    local st
    st="$(systemctl --user is-enabled "$SERVICE" 2>/dev/null)" || st="${st:-no}"
    say "enabled: $st"
    st="$(systemctl --user is-active "$SERVICE" 2>/dev/null)" || st="${st:-no}"
    say "active:  $st"
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

    install -Dm644 "$HERE/daemon/$SERVICE" "$UNIT_DIR/$SERVICE"
    say "$SERVICE -> $UNIT_DIR"

    mkdir -p "$PLASMOID_DIR"
    cp -r "$HERE/plasmoid/." "$PLASMOID_DIR/"
    say "plasmoid -> $PLASMOID_DIR"

    mkdir -p "$MUSIC_DIR"
    say "music dir -> $MUSIC_DIR  (contents never touched by this script)"

    if [ "$DEV" = 1 ]; then
        mkdir -p "$(dirname "$PTH_FILE")"
        printf '%s\n' "$REPO" > "$PTH_FILE"
        say ".pth -> $PTH_FILE  ($REPO)"
        mkdir -p "$DROPIN_DIR"
        printf '[Service]\nEnvironment=PYTHONPATH=%s\n' "$REPO" > "$DROPIN"
        say "daemon drop-in -> $DROPIN  (PYTHONPATH=$REPO)"
    else
        # A previous --dev install left the checkout on the import path; a
        # plain install means the pipx command, so take that override away
        # rather than leave two generators in play.
        if [ -f "$PTH_FILE" ] || [ -f "$DROPIN" ]; then
            rm -f "$PTH_FILE" "$DROPIN"
            say "removed the developer .pth and drop-in (re-run with --dev to keep them)"
        fi
    fi

    # main.qml hardcodes the music dir; patch it if this is not the same user.
    local qml="$PLASMOID_DIR/contents/ui/main.qml"
    if ! grep -q "\"$MUSIC_DIR/\"" "$qml" 2>/dev/null; then
        sed -i "s|property string musicDir: \".*\"|property string musicDir: \"$MUSIC_DIR/\"|" "$qml"
        say "patched musicDir in main.qml -> $MUSIC_DIR/"
    fi

    head_ "Starting daemon"
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE"
    # enable --now only *starts* a stopped unit; it will not restart a running
    # one, so re-running this script would leave the old process holding the old
    # daemon.py and the old Environment=. try-restart restarts it if running and
    # no-ops if not, so a first install still needs the start below.
    systemctl --user try-restart "$SERVICE"
    systemctl --user start "$SERVICE"
    say "$(systemctl --user is-active "$SERVICE")"

    head_ "Verify"
    check_generator || true

    cat <<MSG

Add the widget: right-click panel -> Add Widgets -> "Cyberpunk Chiptune Player".
After editing main.qml on a running shell: systemctl --user restart plasma-plasmashell

Generated music goes to $MUSIC_DIR, never into the repo.
MSG
}

# ── Uninstall ─────────────────────────────────────────────────────────────────

do_uninstall() {
    head_ "Removing"
    systemctl --user disable --now "$SERVICE" 2>/dev/null || true
    rm -f "$BIN_DIR/bitcomposer-generate.sh" \
          "$BIN_DIR/bitcomposer-master.sh" \
          "$BIN_DIR/cyberpunk-chiptune-daemon.py" \
          "$UNIT_DIR/$SERVICE" \
          "$DROPIN" \
          "$PTH_FILE"
    rmdir "$DROPIN_DIR" 2>/dev/null || true
    rm -rf "$PLASMOID_DIR"
    systemctl --user daemon-reload
    say "removed scripts, daemon, unit, drop-in, plasmoid and .pth"
    say "left alone: $MUSIC_DIR and everything in it, and the pipx bitcomposer"
}

DEV=0
case "${1:-}" in
    --check)     do_check ;;
    --uninstall) do_uninstall ;;
    --dev)       DEV=1; do_install ;;
    "")          do_install ;;
    *) printf 'usage: %s [--dev|--check|--uninstall]\n' "$0" >&2; exit 2 ;;
esac
