# Companion install — daemon, widget, helper scripts

The player stack around the generator — a D-Bus daemon, a KDE Plasma widget, and
two helper scripts — is vendored in `companion/` and installed with:

```bash
./companion/install.sh              # install everything
./companion/install.sh --check      # report what is installed, change nothing
./companion/install.sh --uninstall  # remove everything except generated music
```

Idempotent, so re-run it to pick up changes. Start with `--check` on an existing
machine; it verifies dependencies, installed components, the Python import path
and daemon status without touching anything.

**Generated music is not part of this repo and never goes in it.** Tracks live in
`~/Music/Chiptune` (override with `$BITCOMPOSER_MUSIC_DIR`). The installer
creates that directory and otherwise never reads, writes or clears it —
including on `--uninstall`.

The vendored copies came from this laptop's **installed** files, which are
authoritative. Ragnarok's dev copies under
`~/Projects/cyberpunk-hud/plasmoids/chiptune-player/` are stale — behind by ~61
lines of daemon and ~250 lines of QML. Do not sync from them.

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
echo "/path/to/your/bitComposer" > "$SITE/bitcomposer.pth"
```

`companion/install.sh` writes this for you, using the location of the checkout
it is run from — the path is not fixed, and differs per machine (`~/bitComposer`
on one, `~/Projects/bitComposer` on another).

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

The systemd unit also carries `Environment=PYTHONPATH`, written as the
placeholder `@REPO@` in the repo and substituted by `install.sh` with the real
checkout path. That is redundant with the `.pth` but harmless, and is left in
place as a fallback for the daemon specifically. Do not `cp` the unit into
place by hand — an unsubstituted `@REPO@` gives the daemon a PYTHONPATH that
does not exist.

---

## What the installer does

| From `companion/` | Installs to |
|---|---|
| `bin/bitcomposer-generate.sh` | `~/.local/bin/` (0755) |
| `bin/bitcomposer-master.sh` | `~/.local/bin/` (0755) |
| `daemon/cyberpunk-chiptune-daemon.py` | `~/.local/bin/` (0755) |
| `daemon/cyberpunk-chiptune-daemon.service` | `~/.config/systemd/user/` (0644) |
| `plasmoid/` | `~/.local/share/plasma/plasmoids/org.kde.plasma.cyberpunkchiptune/` |
| — | writes the `.pth` described above |
| — | `mkdir -p` the music dir, then leaves it alone |

It then reloads systemd, enables the daemon, and `try-restart`s it before
starting it. `enable --now` alone would only *start* a stopped unit, so
re-running the installer on a machine where the daemon is already up would leave
the old process holding the old `daemon.py` and the old `Environment=` — a green
install that changed nothing. Finally it re-checks the import.

`main.qml` hardcodes the music dir at line 116 — the only hardcoded `/home/troy`
in the whole stack, since the daemon and both scripts use `$HOME`/`expanduser`.
The installer rewrites that line to match `$MUSIC_DIR`, so a different username
or a `$BITCOMPOSER_MUSIC_DIR` override works without hand-editing.

Then add the widget: right-click panel → Add Widgets → "Cyberpunk Chiptune
Player". After editing `main.qml` on an already-running shell:
`systemctl --user restart plasma-plasmashell`.

`~/.local/bin` must be on PATH — the widget shells out to the helper scripts by
bare name, and it inherits plasmashell's PATH, not a login shell's. `--check`
verifies this.

The vendored service unit includes the `Environment=PYTHONPATH` fallback, so it
is no longer a local-only modification that a reinstall would silently revert.

---

## Runtime dependencies

`./companion/install.sh --check` tests all of these.

| Dependency | Notes |
|---|---|
| `libopenmpt.so.0` | loaded via raw `ctypes.CDLL`, so the SONAME must match exactly. Stock on Debian trixie. Test with `python3 -c "import ctypes; ctypes.CDLL('libopenmpt.so.0')"` — **not** `ldconfig -p`, which lives in `/sbin` and is absent from a normal user PATH, so it fails silently and reports a false negative |
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
# import resolves to the CHECKOUT, with no PYTHONPATH, from any directory.
# Print the path — a bare `import` succeeding proves nothing, because a
# pip-installed copy in site-packages shadows the .pth and imports fine.
cd / && env -u PYTHONPATH python3 -c \
  "import bitcomposer, os; print(os.path.dirname(os.path.dirname(bitcomposer.__file__)))"

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
