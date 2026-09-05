# Companion install — daemon, widget, helper scripts

The bitComposer repo is only the Python package. The player stack around it —
a D-Bus daemon, a KDE Plasma widget, and two helper scripts — lives outside the
repo and is not versioned here yet (see `PORTABILITY.md` for that open question).

Sources for the unversioned parts are on Ragnarok, and a bundle of the
**installed** (authoritative) copies was taken 2026-09-04. Ragnarok's dev copies
under `~/Projects/cyberpunk-hud/plasmoids/chiptune-player/` are stale — behind
the installed versions by ~61 lines of daemon and ~250 lines of QML.

---

## Making bitComposer importable

Both the daemon's autogen and `bitcomposer-generate.sh` shell out to
`python3 -m bitcomposer.cli`, so the package must be importable by the **system**
python3 — not a venv. On Debian 13, PEP 668 (`/usr/lib/python3.13/
EXTERNALLY-MANAGED`) blocks a plain `pip install`.

This machine uses a `.pth` file:

```bash
SITE=$(python3 -m site --user-site)     # ~/.local/lib/python3.13/site-packages
mkdir -p "$SITE"
echo "$HOME/bitComposer" > "$SITE/bitcomposer.pth"
```

One line, no pip, no PEP 668 override. Every `python3` this user runs picks it
up — shell, daemon, and the widget via plasmashell alike. It points at the
working tree, so **autogen follows whichever git branch is checked out**, which
makes A/B testing generator changes a `git checkout` away. Undo by deleting the
file.

> ### ⚠️ This breaks silently on a Python version bump
>
> The path contains the Python minor version. When Debian moves to 3.14, the
> user-site directory becomes `~/.local/lib/python3.14/site-packages`, the old
> `.pth` is no longer read, and **the widget's GENERATE button and the daemon's
> autogen both start failing with `ModuleNotFoundError`** — with no other
> symptom, since playback keeps working fine.
>
> Recreate it after any Python upgrade by re-running the snippet above.
> Check with:
>
> ```bash
> python3 -c "import bitcomposer, os; print(os.path.dirname(bitcomposer.__file__))"
> ```
>
> An editable `pip install` has exactly the same failure mode. Only a plain
> (non-editable) install is immune — but that is a static copy, so it gives up
> the branch-tracking property above.

The systemd unit also carries `Environment=PYTHONPATH=%h/bitComposer`. That is
now redundant with the `.pth` but harmless, and it is deliberately left in place
as a fallback for the daemon specifically.

---

## Install

```bash
V=~/bitcomposer-vendor   # or wherever the bundle is

install -Dm755 $V/bin/bitcomposer-generate.sh          ~/.local/bin/bitcomposer-generate.sh
install -Dm755 $V/bin/bitcomposer-master.sh            ~/.local/bin/bitcomposer-master.sh
install -Dm755 $V/daemon/cyberpunk-chiptune-daemon.py  ~/.local/bin/cyberpunk-chiptune-daemon.py
install -Dm644 $V/daemon/cyberpunk-chiptune-daemon.service ~/.config/systemd/user/cyberpunk-chiptune-daemon.service
mkdir -p ~/Music/Chiptune
cp -r $V/plasmoid/. ~/.local/share/plasma/plasmoids/org.kde.plasma.cyberpunkchiptune/
systemctl --user daemon-reload
systemctl --user enable --now cyberpunk-chiptune-daemon.service
```

Then add the widget: right-click panel → Add Widgets → "Cyberpunk Chiptune
Player". After editing `main.qml` on an already-running shell:
`systemctl --user restart plasma-plasmashell`.

`~/.local/bin` must be on PATH — the widget shells out to the helper scripts by
bare name, and it inherits plasmashell's PATH, not a login shell's.

> **Do not blindly overwrite the service unit on a machine that already has one.**
> On this laptop it is the single locally-modified file, carrying the
> `Environment=PYTHONPATH` line. Copying Ragnarok's version reverts that.

---

## Runtime dependencies

| Dependency | Notes |
|---|---|
| `libopenmpt.so.0` | loaded via raw `ctypes.CDLL`, so the SONAME must match exactly. Stock on Debian trixie; elsewhere check `ldconfig -p \| grep openmpt` |
| `python3-dbus`, `python3-gi` | apt |
| `paplay` (pulseaudio-utils) | audio path is raw PCM 48k/16-bit stereo piped to `paplay --raw` |
| `qdbus6` (qt6-tools) | the QML widget shells out to this for every call |

---

## Daemon D-Bus contract

Bus `org.mpris.MediaPlayer2.CyberpunkChiptune`, path `/org/mpris/MediaPlayer2`.
Standard MPRIS2 (Play/Pause/PlayPause/Stop/Next/Previous/Seek/SetPosition) plus:

- `GetState() -> s` — pipe-delimited, **13 fields**, 1-indexed for `cut -d'|'`:
  1 status, 2 position, 3 duration, 4 channels, 5 title, 6 artist, 7 type,
  8 file, 9 patterns, 10 shuffle, 11 playlistCount, 12 currentIndex, 13 autoGen
- `GetPlaylist() -> as`
- `PlayIndex(i)`
- `Rescan()`
- `SetAutoGenerate(b enabled, s cliFlags)`

Daemon config constants: `MUSIC_DIR=~/Music/Chiptune`, `SAMPLE_RATE=48000`,
`EXTENSIONS={.mod,.xm,.it,.s3m,.mptm}`, `AUTOGEN_PREFIX="bitcomposer_auto_"`,
`AUTOGEN_MAX=10`.

---

## Gotchas

- **No file monitor.** The installed daemon dropped `Gio.File.monitor_directory`,
  so the playlist refreshes *only* on an explicit `Rescan()`. Dropping a file
  into `~/Music/Chiptune/` will not surface it until something calls that; both
  helper scripts do. Monitor code is on Ragnarok at
  `~/Projects/cyberpunk-hud/plasmoids/chiptune-player/daemon/...` lines ~754–767.
- **Auto-file pruning happens twice.** `bitcomposer-generate.sh --auto` prunes to
  10, and the daemon's `_prune_autogen` independently prunes to 10. Both hard
  `rm`/`unlink()` with no trash, so a generation can silently destroy old output.
- **Hardcoded music dir.** `plasmoid/contents/ui/main.qml:116` has
  `/home/troy/Music/Chiptune/`. It is the only hardcoded `/home/troy` in the
  stack — the daemon and both scripts use `$HOME` / `expanduser`. Patch it if the
  user is not `troy`.
- **Mastering restarts the track.** `bitcomposer-master.sh` stops, rescans and
  replays the current track so the edit is audible immediately. That is by
  design, not a bug, but it is not a seamless in-place update.

---

## Verifying an install

```bash
# import works with no PYTHONPATH, from any directory
cd / && env -u PYTHONPATH python3 -c "import bitcomposer; print('ok')"

# generator end to end (widget-like environment)
env -u PYTHONPATH bitcomposer-generate.sh --form standard --harmony-voicing full

# mastering, on a copy — this patches in place
cp ~/Music/Chiptune/some.it /tmp/t.it
bitcomposer-master.sh /tmp/t.it 64 20 20 20 12 30 40 40 40 40 40 40

# generation quality did not regress
python3 tools/analyze.py '~/Music/Chiptune/*.it'
```

A healthy generated track measures roughly 2–4 kick, ~2 snare and 4–8 hat hits
per bar. Substantially below that means the drum grid regression described in
`ANALYSIS.md` is back.
