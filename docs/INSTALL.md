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

The companion is Linux-only and assumes KDE Plasma 6, PipeWire or
PulseAudio, and Debian-style paths (`/usr/bin/python3`). It is optional:
the generator itself runs anywhere Python does.

---

## Making bitComposer importable

Both the daemon's autogen and `bitcomposer-generate.sh` shell out to
`python3 -m bitcomposer.cli`, so the package must be importable by the **system**
python3 — not a venv. On Debian 13, PEP 668 (`/usr/lib/python3.13/
EXTERNALLY-MANAGED`) blocks a plain `pip install`.

Use a `.pth` file:

```bash
SITE=$(python3 -m site --user-site)     # ~/.local/lib/python3.13/site-packages
mkdir -p "$SITE"
echo "/path/to/your/bitComposer" > "$SITE/bitcomposer.pth"
```

`companion/install.sh` writes this for you, using the location of the checkout
it is run from.

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

`main.qml` has no music dir of its own: the installer writes `$MUSIC_DIR` into
it as a fallback, and at runtime the widget uses whatever the daemon reports in
`GetState` field 16, so the two cannot drift.

Widget settings (preset and every chip) persist in the plasmoid's own
configuration (`contents/config/main.xml`), so they survive a shell restart.

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

- `GetState() -> s` — pipe-delimited, **16 fields**, 1-indexed for `cut -d'|'`:
  1 status, 2 position, 3 duration, 4 channels, 5 title, 6 artist, 7 type,
  8 file, 9 patterns, 10 shuffle, 11 playlistCount, 12 currentIndex, 13 autoGen,
  14 volume (linear gain, `1.00` = unity), 15 blurb (the module's song message
  minus its title line, lines joined with `  /  `; generated tracks carry key,
  BPM, style and form there), 16 music directory.
  Free-text fields have `|` replaced so a module title cannot shift the columns.
- `GetPlaylistInfo() -> as` — one `filename|title|auto` line per track in
  `GetPlaylist` order; `auto` is 1 for `bitcomposer_auto_*` files, which
  `Rescan()` may prune. Titles are read through libopenmpt and cached by mtime.
- `KeepTrack(i) -> s` — renames an auto-generated track to drop the prefix so
  pruning leaves it alone; returns the new filename.
- `Properties.Set Player Volume <0..3>` — linear gain; above 1.0 boosts with a
  soft limiter on the output. Volume, Shuffle and the auto-generate flag with
  its CLI flags persist in `~/.config/cyberpunk-chiptune/state.json`. Boolean and numeric variants may
  arrive as strings (qdbus6 sends them that way) and are parsed.
- `GetPlaylist() -> as`
- `PlayIndex(i)` — `i` is a position in `GetPlaylist`, with or without shuffle.
  `currentIndex` in `GetState` uses the same numbering; shuffle only changes
  the order Next/Previous step through.
- `Rescan()` — also prunes auto-generated tracks (`*(auto).it`, and the
  older `bitcomposer_auto_*.it`) down to `AUTOGEN_MAX`, never the loaded
  track, and keeps `currentIndex` on the loaded file.
- `SetAutoGenerate(b enabled, s cliFlags)` — flags are split with `shlex` and
  passed to the CLI as arguments, not through a shell. Only an off→on switch
  while stopped starts a generation; re-sending with new flags just updates
  them. Switching off mid-generation keeps the file but does not play it.

Daemon config constants: `MUSIC_DIR=~/Music/Chiptune`, `SAMPLE_RATE=48000`,
`EXTENSIONS={.mod,.xm,.it,.s3m,.mptm}`, `AUTOGEN_SUFFIX=" (auto)"`,
`AUTOGEN_MAX=10`, `VOLUME_MAX=3.0`, `STATE_FILE=~/.config/cyberpunk-chiptune/state.json`.

---

## Gotchas

- **File monitor.** The daemon watches the music dir (Gio) and rescans a
  second after changes settle, so files dropped in or deleted show up on
  their own. `Rescan()` and the widget's REFRESH button force it immediately.
- **File names are song titles.** The CLI names output after the module
  title ("Haunted Orchard.it", with " 2", " 3" on a clash) unless `-o` or
  `--name timestamp` is given, so the player's playlist and the folder agree.
- **Auto-file pruning is hard deletion.** The daemon prunes auto-generated
  tracks — `<Title> (auto).it`, and the older `bitcomposer_auto_*.it` — to
  `AUTOGEN_MAX` (10) on every `Rescan()`, with `unlink()` and no trash. It is
  the single place pruning happens. Use KEEP in the widget (or `KeepTrack`)
  to rename one out of the set.
- **Default music dir in the QML.** `main.qml` carries a fallback path that
  the installer patches to `$MUSIC_DIR`; at runtime the daemon's reported
  directory overrides it.
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

# mastering, on a copy — this patches in place. One volume per channel, in
# bitcomposer.pattern order (14 for current output: melody, harm x3, bass,
# arp, kick, snare, hihat, tom, crash, open hat, echo x2). Only the channels
# given are written.
cp ~/Music/Chiptune/some.it /tmp/t.it
bitcomposer-master.sh /tmp/t.it 64 20 20 20 12 30 40 40 40 40 40 40 13 13

# unit tests
python3 -m unittest discover -s tests

# generation quality did not regress
python3 tools/analyze.py '~/Music/Chiptune/*.it'
```

A healthy generated track measures roughly 2–4 kick, ~2 snare and 4–8 hat hits
per bar. Substantially below that means the drum grid regression described in
`ANALYSIS.md` is back.
