# Companion install — daemon, widget, helper scripts

The companion is the KDE Plasma panel version of the player. The player
itself (`bitcomposer-player`, the same program as `bitComposer.exe` on
Windows) needs none of this: `pipx install bitcomposer`, then launch
`bitcomposer-player` once (that adds it to the app menu), and
`bitcomposer-player --check` to see that libopenmpt and an audio output
are found. This page is for the widget and its daemon.

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
the generator itself runs anywhere Python does, and installs on its own
with `pipx install bitcomposer` (README); the companion runs that command.

---

## Where the companion finds the generator

The daemon's autogen and `bitcomposer-generate.sh` run the `bitcomposer`
command. Install it with pipx, which puts it in `~/.local/bin` without
touching the system Python (Debian 13's PEP 668 guard blocks a plain
`pip install` there):

```bash
sudo apt install pipx
pipx install bitcomposer
```

`~/.local/bin` has to be on PATH anyway: the widget shells out to the helper
scripts by bare name. The daemon's unit adds it for the service, since a
user service does not get it from a login shell.

### Developer mode: generation follows the checkout

To hear the branch you have checked out instead of the released package,
install with `--dev`:

```bash
./companion/install.sh --dev
```

That writes two things and the companion falls back to
`python3 -m bitcomposer.cli` whenever no `bitcomposer` command is on PATH:

- a `.pth` file in the system python3's user site
  (`~/.local/lib/python3.13/site-packages/bitcomposer.pth`) holding the
  checkout path, so every `python3` this user runs imports from it;
- a systemd drop-in (`~/.config/systemd/user/cyberpunk-chiptune-daemon.service.d/dev.conf`)
  giving the daemon the same path as `PYTHONPATH`.

A plain `./companion/install.sh` removes both again. If a pipx `bitcomposer`
is also installed, it wins over the checkout; `--check` says so, and
`pipx uninstall bitcomposer` restores the checkout.

> ### ⚠️ Developer mode breaks silently on a Python version bump
>
> The `.pth` path contains the Python minor version. When Debian moves to
> 3.14, the user-site directory becomes `~/.local/lib/python3.14/site-packages`,
> the old `.pth` is no longer read, and **the widget's GENERATE button and
> the daemon's autogen both start failing with `ModuleNotFoundError`** with
> no other symptom, since playback keeps working fine. The daemon's drop-in
> keeps autogen alive; the widget's button does not have it. Re-run
> `./companion/install.sh --dev` after a Python upgrade. Check with:
>
> ```bash
> ./companion/install.sh --check
> ```
>
> A pipx install has no such failure mode (pipx keeps its own venv), which
> is why it is the user's path.

---

## What the installer does

| From `companion/` | Installs to |
|---|---|
| `bin/bitcomposer-generate.sh` | `~/.local/bin/` (0755) |
| `bin/bitcomposer-master.sh` | `~/.local/bin/` (0755) |
| `daemon/cyberpunk-chiptune-daemon.py` | `~/.local/bin/` (0755) |
| `daemon/cyberpunk-chiptune-daemon.service` | `~/.config/systemd/user/` (0644) |
| `plasmoid/` | `~/.local/share/plasma/plasmoids/org.kde.plasma.cyberpunkchiptune/` |
| — (`--dev` only) | the `.pth` and the daemon drop-in described above |
| — | `mkdir -p` the music dir, then leaves it alone |

It then reloads systemd, enables the daemon, and `try-restart`s it before
starting it. `enable --now` alone would only *start* a stopped unit, so
re-running the installer on a machine where the daemon is already up would leave
the old process holding the old `daemon.py` and the old `Environment=` — a green
install that changed nothing. Finally it reports which generator the daemon
will run.

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

---

## Runtime dependencies

`./companion/install.sh --check` tests all of these.

| Dependency | Notes |
|---|---|
| `bitcomposer` command | `pipx install bitcomposer` (`apt install pipx` first); or a checkout through `--dev` |
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
- `GetLayout() -> as` — the role of every channel of the loaded module, in
  order, from the `layout:` line bitcomposer writes into the song message
  (`echo.<role>` marks an echo return of that role). Older 14-channel
  bitcomposer files get the layout they were written with; other modules get
  `ch1`, `ch2`, … The widget builds its mixer from this: one fader per dry
  channel and one ECHO bus for all the returns (expand for LEAD / HARM /
  ARP), the bus being a ratio against the mix the file was written with.
  The COMPOSE tab's SOUND picker passes `--sound` (random / chip / genesis / snes / ffvi / mana / evermore / megamanx); a pack is snes narrowed to one score, so there is no separate palette picker.
- `GetSongInfo() -> as` — the machine-readable lines of the loaded module's
  song message: `voices: role=name,...` (every drawn voice, kit included,
  `alt=` the alternate lead), `drew: sound=,form=,intro=,harmony=,bass=,echo=,
  tempo=,key=` and the `echo:` and `layout:` lines. Empty for files without
  them. The widget's readout line and the voice labels on its faders read
  these; the KIT bus folds the six kit faders the way the ECHO bus folds the
  returns.
- `SetChannelVolume(i channel, i volume) -> b` — live mixer: sets a channel's
  volume (0–64) on the playing module via libopenmpt's interactive interface.
  Immediate, no restart. `GetChannelVolumes() -> ai` reads them back (with
  `qdbus6 --literal`).
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
- **Every track made through the player is provisional.** Both the GENERATE
  button and auto-generate write `<Title> (auto).it`. The daemon prunes those
  (and the older `bitcomposer_auto_*.it`) to `AUTOGEN_MAX` (10) on every
  `Rescan()`, with `unlink()` and no trash; it is the single place pruning
  happens. KEEP in the widget (or `KeepTrack`) renames one out of the set.
  The CLI itself writes plain `<Title>.it`.
- **Default music dir in the QML.** `main.qml` carries a fallback path that
  the installer patches to `$MUSIC_DIR`; at runtime the daemon's reported
  directory overrides it.
- **Mixer is live, APPLY persists.** Dragging a MIX slider calls
  `SetChannelVolume`, which changes the playing module at once; APPLY TO
  TRACK runs `bitcomposer-master.sh`, which only writes the values into the
  file header so they survive a reload (the folder monitor rescans). Reopening
  the panel reads the file's values back and re-applies them live.

---

## Verifying an install

```bash
# which generator the daemon and the widget will run, and from where
./companion/install.sh --check

# generator end to end (widget-like environment)
env -u PYTHONPATH bitcomposer-generate.sh --form standard --harmony-voicing full

# persisting a mix, on a copy — this patches the header in place. One volume per channel, in
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
