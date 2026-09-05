# Portability — open decision

**Status:** 2026-09-04. Originals received from Ragnarok at `~/bitcomposer-vendor`
(not versioned here). `bitcomposer-master.sh` is installed and verified working.
Open: the import mechanism (see "The import gap"), then the A/B/C scope choice.

Goal: `git clone` and it works, on any machine, without the KDE desktop stack.
Today the generator writes wherever you happen to be standing, and the player
side lives entirely outside the repo in three places that only exist on this
laptop.

---

## The scoping question

How far should "runs when anyone clones it" go? These are cumulative.

### Option A — generator self-contained *(recommended starting point)*

- Default output to `<repo>/output/` instead of the current working directory.
- Override order: `-o` > `-d` > `$BITCOMPOSER_OUTPUT_DIR` > `<repo>/output/`.
- A smoke test so a fresh clone can verify itself.

Repo stays a clean library + CLI with zero runtime dependencies. No desktop
coupling whatsoever. Small, and it is the part that is unambiguously wanted.

### Option B — also vendor the helper scripts

Add `scripts/bitcomposer-generate.sh` and `scripts/bitcomposer-master.sh` to the
repo so the widget's dead buttons can be pointed at a clone rather than at
`~/.local/bin`. Contracts for both are recovered below.

### Option C — full player stack in-repo

Also vendor the chiptune daemon and the Plasma widget, with an `install.sh` that
deploys them to `~/.local`. Makes a fresh machine reproducible end to end. Much
larger, and pulls the desktop back into scope.

---

## What is already true

Groundwork that exists and needs no work:

- `.gitignore` already lists `output/` and `*.it` — the convention was intended,
  the CLI just never defaulted to it.
- `pyproject.toml` already declares the console script
  (`bitcomposer = "bitcomposer.cli:main"`), so `pip install .` gives a
  `bitcomposer` command.
- `tools/analyze.py` is stdlib-only and does not import the package, so it works
  from a clone with nothing installed.

The single gap for Option A: `cli.py` has `-d` defaulting to `"."` and `-o`
defaulting to an auto-generated name in the current directory.

---

## What lives outside the repo

Three things the project depends on that are not versioned anywhere:

| thing | location | notes |
|---|---|---|
| chiptune daemon | `~/.local/bin/cyberpunk-chiptune-daemon.py` | MPRIS2 over D-Bus, libopenmpt playback |
| Plasma widget | `~/.local/share/plasma/plasmoids/org.kde.plasma.cyberpunkchiptune/` | ported from Ragnarok |
| systemd unit | `~/.config/systemd/user/cyberpunk-chiptune-daemon.service` | carries the PYTHONPATH fix below |
| helper scripts | `~/.local/bin/bitcomposer-{generate,master}.sh` | originals in `~/bitcomposer-vendor/bin/` |

The daemon, `main.qml` and `metadata.json` on this machine are md5-identical to
Ragnarok's (verified 2026-09-04). The **service unit is not** — it is the one
locally modified file, carrying the `Environment=PYTHONPATH` line below. Do not
overwrite it from a bundle; that would silently break autogen.

`~/Music/Chiptune/` is hardcoded in **two** places — `MUSIC_DIR` in the daemon
and `musicDir` in the widget QML. The daemon scans with `rglob`, so
subdirectories work. Do not put generated `.it` files in the repo expecting the
widget to see them; it will not.

The daemon's autogen shells out to `python3 -m bitcomposer.cli`. bitcomposer is
not installed (PEP 668 blocks a system pip install on Debian 13), so the unit
carries:

```ini
Environment=PYTHONPATH=%h/bitComposer
```

Autogen therefore follows whichever git branch is checked out, which is useful
for A/B testing but means **a stale checkout silently changes what it
generates**. Note `AUTOGEN_MAX = 10` in the daemon, which hard-deletes the oldest
`bitcomposer_auto_*.it` via `unlink()` — no trash.

---

## Helper script contracts

Both are referenced by the widget. Originals arrived from Ragnarok in
`~/bitcomposer-vendor/bin/`. An earlier version of this document reconstructed
them from the QML and got the broad shape right but the details wrong — what
follows is from the actual scripts.

### `bitcomposer-master.sh` — installed and verified

```
bitcomposer-master.sh <path.it> v0 v1 ... v11
```

13 arguments: file path plus 12 channel volumes, each clamped to 0–64. Channel
order is melody, harm 1–3, bass, arp, kick, snare, hihat, tom, crash, open hat.

Two details the reconstruction missed:

- It writes the **full 64-byte channel-volume block** at offset 128, zero-padding
  channels 12–63 — not just 12 bytes. This matches what `write_it_file` already
  emits for unused channels, so a 12-byte write would have worked by accident,
  but it is not what the script does.
- It does not only patch bytes. Afterwards it **stops, rescans and replays the
  current track** over D-Bus, taking the index from `GetState` field 12, so the
  edit is audible immediately.

Prints `OK` on success, `ERROR` to stderr on bad input. It imports nothing from
bitcomposer — stdlib file I/O plus `qdbus6` — which is why it works today while
`generate.sh` does not.

Verified 2026-09-04 on a copy: bytes written correctly, patched file still
decodes clean through libopenmpt, daemon left healthy.

### `bitcomposer-generate.sh` — not yet installed, blocked on the import gap

```
bitcomposer-generate.sh [--auto] <bitcomposer CLI flags>
```

Flags come from `_buildSettingsFlags()` in the QML and are all real CLI options
(`--tempo`, `--energy`, `--scale`, `--style`, `--drum-density`, `--no-fills`,
`--swing`, `--melody`, `--harmony-voicing`, `--harmony-mode`, `--bass-weight`,
`--form`), driven by ten widget presets — MEGA DRIVE, CASTLEVANIA, BOSS FIGHT,
OVERWORLD, CHILL WAVE, DUNGEON, CREDITS, STREET FIGHT, CYBER NOIR, RANDOM.

`--auto` is now settled: it selects the `bitcomposer_auto_<ts>.it` filename
instead of `bitcomposer_<ts>.it`, **and the script prunes to 10 itself**. So
auto-file pruning is implemented twice — here and in the daemon's
`_prune_autogen` — both capped at 10, both hard `rm`. Worth consolidating.

It writes into `~/Music/Chiptune/`, calls `Rescan`, then locates the new file in
`GetPlaylist` and calls `PlayIndex`. The QML completion handler ignores stdout
and only re-polls `GetPlaylist`, so the script must do that work itself.

---

## The import gap

`generate.sh` calls `python3 -m bitcomposer.cli` with no import path of its own,
and bitcomposer is not installed (PEP 668 blocks a system pip install on Debian
13). The widget launches it from **plasmashell**, not from a login shell:

```
plasmashell PATH includes ~/.local/bin : yes
plasmashell PYTHONPATH                 : unset
```

So neither a shell-profile `export` nor the daemon's `Environment=PYTHONPATH`
reaches it — that unit only covers the daemon's own autogen. Installing
`generate.sh` as-is leaves the GENERATE button throwing `ModuleNotFoundError`.

Options, undecided:

- **`.pth` file** — one line in `~/.local/lib/python3.13/site-packages/`
  pointing at the repo. No pip, no PEP 668 argument, importable by every
  `python3` this user runs, still tracks the checked-out branch, reversible by
  deleting one file. Would make the systemd `Environment=` line redundant.
  Caveat: version-pathed, so a Debian Python bump breaks it silently.
- **Editable install** (`pip install --break-system-packages -e .`) — same
  branch-tracking property, same version-path caveat, needs the PEP 668 override.
- **Plain install** (`pip install --break-system-packages .`) — what Ragnarok's
  `INSTALL.md` says. Static copy, so autogen would stop following the checked-out
  branch and one-command A/B testing is lost.
- **PYTHONPATH inside `generate.sh`** — works, but hardcodes the repo location,
  which is the thing this document exists to remove.

---

## Also learned from the bundle

- **The installed daemon has no file monitor.** The dev copy used
  `Gio.File.monitor_directory`; the installed (newer) one dropped `Gio` entirely,
  so rescans happen *only* via explicit `Rescan()`. That is why both helper
  scripts call it. Monitor code is on Ragnarok at
  `~/Projects/cyberpunk-hud/plasmoids/chiptune-player/daemon/...` lines ~754–767.
- **Ragnarok's dev copies are stale** — installed is ahead (daemon +61 lines,
  QML 1188 → 1436 lines). Vendor the *installed* versions, and push them back to
  `cyberpunk-hud` so that repo stops being misleading.
- **Daemon D-Bus surface**: standard MPRIS2 plus `GetState() -> s` (pipe
  delimited, 13 fields: status, position, duration, channels, title, artist,
  type, file, patterns, shuffle, playlistCount, currentIndex, autoGen),
  `GetPlaylist() -> as`, `PlayIndex(i)`, `Rescan()`,
  `SetAutoGenerate(b, s)`.
- **Runtime deps** beyond Python: `libopenmpt.so.0` via raw `ctypes.CDLL` (SONAME
  must match exactly), `python3-dbus`, `python3-gi`, `paplay` from
  pulseaudio-utils (audio is raw 48k/16-bit stereo piped to `paplay --raw`), and
  `qdbus6` from qt6-tools.
- Ragnarok keeps the repo at `~/Projects/bitComposer`; this machine uses
  `~/bitComposer`. Nothing outside the QML hardcodes a path — the daemon and both
  scripts use `$HOME` / `expanduser`.

## Next step

Decide the import mechanism, install `generate.sh`, then pick A, B or C. The
bundle makes **Option C** more realistic than when it was first proposed, since
Ragnarok's `INSTALL.md` is most of an install script already. Option A remains
independent of all of this and can start at any time.
