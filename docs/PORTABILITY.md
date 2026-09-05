# Portability — open decision

**Status:** parked 2026-09-04, pending helper-script originals from Ragnarok.

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

## Recovered contracts

Both helper scripts are referenced by the widget and **neither exists on this
machine**. The widget QML specifies them well enough to rebuild.

### `bitcomposer-master.sh` — fully specified

Writes the mastering panel's channel volumes into an existing `.it` file.

```
bitcomposer-master.sh <path.it> v0 v1 v2 v3 v4 v5 v6 v7 v8 v9 v10 v11
```

13 arguments: file path plus 12 channel volumes, each 0–64. It must write those
12 bytes at **offset 128** of the file.

Three independent sources agree on this, so there is no guesswork:

1. QML comment: *"Channel volumes for mastering (0-64, matches IT header bytes
   128-191)"*.
2. The **read** path needs no script and pins the format exactly — the QML runs
   `python3 -c "f=open(path,'rb');f.seek(128);d=f.read(12);..."`.
3. `channel_volumes` in `composer.py`, the QML `channelVolumes` default, and
   bytes 128–139 of a generated file all read
   `[13, 25, 25, 25, 8, 33, 36, 36, 36, 36, 36, 36]`.

Channel order is melody, harm 1–3, bass, arp, kick, snare, hihat, tom, crash,
open hat.

### `bitcomposer-generate.sh` — mostly specified

```
bitcomposer-generate.sh [--auto] <bitcomposer CLI flags>
```

Flags come from `_buildSettingsFlags()` in the QML and are all real, existing
CLI options (`--tempo`, `--energy`, `--scale`, `--style`, `--drum-density`,
`--no-fills`, `--swing`, `--melody`, `--harmony-voicing`, `--harmony-mode`,
`--bass-weight`, `--form`). The widget drives them from ten presets — MEGA
DRIVE, CASTLEVANIA, BOSS FIGHT, OVERWORLD, CHILL WAVE, DUNGEON, CREDITS, STREET
FIGHT, CYBER NOIR, RANDOM.

It must generate into `~/Music/Chiptune/` and then make the daemon aware of the
new file, since the QML's completion handler ignores stdout entirely and only
re-polls `GetPlaylist` — so the script itself has to call the daemon's `Rescan`
over D-Bus.

**Open question:** what `--auto` does. Best guess is that it writes with the
`bitcomposer_auto_` prefix so `AUTOGEN_MAX` pruning applies, but that is
inference, not documentation.

---

## Needed from Ragnarok

In priority order:

1. **`bitcomposer-generate.sh`** — settles the `--auto` semantics, the only
   genuine unknown.
2. **Any daemon or widget install notes** — more valuable than either script,
   since the daemon and plasmoid are the parts not versioned anywhere and Option
   C depends on them.
3. **`bitcomposer-master.sh`** — reconstructible from the spec above, but worth
   a look to confirm it does not do something extra such as backing up the file
   before patching it.

## Next step

Pick A, B, or C, then implement. Option A is independent of the Ragnarok
material and can start at any time.
