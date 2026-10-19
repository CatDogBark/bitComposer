# Contributing

bitComposer is small on purpose: the generator is pure Python with no runtime
dependencies (the player adds Qt), and every generator change is judged by
measurement rather than by ear alone.

## Branches

`main` holds released code and nothing else. Work goes into `dev` through
pull requests, one topic each; `dev` merges into `main` for a release.

Pull requests into `dev` run no checks on GitHub (the Windows build alone
takes ten minutes); the tests below, run locally with the player's
dependencies, are the check. Pull requests into `main` run everything: the
tests on every supported Python and the Windows build. Either workflow can
also be started by hand on any branch (`gh workflow run ci.yml --ref
<branch>`, or `windows.yml`) when a change could break Windows or an older
Python.

## Before you open a pull request

1. Run the tests:

   ```bash
   python3 -m unittest discover -s tests -v
   ```

   The generator's tests need nothing. The player's (`tests/test_player.py`)
   skip without what CI installs: PySide6-Essentials and jeepney
   (`pip install PySide6-Essentials jeepney`), libopenmpt (`libopenmpt0` on
   Debian and Ubuntu) and `dbus-daemon`. A skip is not a pass: have them
   before touching `bitcomposer/player/`. The window's tests run Qt
   offscreen, so no display is needed.

2. If you touched anything in `bitcomposer/`, generate a fixed batch before
   and after your change and paste both analyzer tables in the PR:

   ```bash
   for s in $(seq 1 12); do python3 -m bitcomposer.cli -s $s -d /tmp/before; done
   python3 tools/analyze.py '/tmp/before/*.it'
   ```

   `docs/ANALYSIS.md` explains what the columns mean and why ear-checking
   alone has repeatedly missed real defects here.

3. Keep seeded output deterministic. If your change alters what a seed
   produces, say so; that is fine, silently breaking it is not. A change
   meant to leave the music alone (a refactor, a cleanup, moving code
   between modules) must leave every file byte-identical: see the check
   below.

4. Keep it dependency-free. The generator must run with a bare `python3`.

## Where things live

| path | what |
|---|---|
| `bitcomposer/composer.py` | `compose_song`: the draws, the section loop, the song message; `compose_and_save` |
| `bitcomposer/builder.py` | one pattern at a time: chord timeline, key plan, every layer written into it |
| `bitcomposer/instruments.py` | palettes, the per-song instrument draw (contrast rule), the sample set |
| `bitcomposer/echo.py` | echo settings tables and the bus that makes taps and darker variants |
| `bitcomposer/mix.py` | written channel volumes, sustaining-arp level, pack trims, master gain |
| `bitcomposer/samples/` | `dsp.py` builders and filters; `chip.py`, `snes.py`, `genesis.py` palettes; `__init__.py` the registry, loudness rules, `generate_instrument` |
| `emu/` | the SNES sound CPU and SNES chip emulator, in Rust (a second package, `bitcomposer-emu`); see Building the emulator |
| `bitcomposer/spc/` | SPC snapshots read: the file, ID666, the DSP registers, BRR decoding (`brr.py`); running the driver (`emulate.py`, needs `bitcomposer-emu`), its writes as notes (`notes.py`), sample pitch (`tuning.py`), SPC to IT (`convert.py` decides, in stages, how IT carries a song; `snes_chip.py` is the SNES chip's sound from a note's registers; `it_song.py` writes the IT song on a row grid and knows nothing of the SNES); `python -m bitcomposer.spc` |
| `bitcomposer/packs/` | one module per style pack: its voices, their registry entries and its `PACK` habits; `packfile.py` reads pack files (`docs/PACKS.md`) |
| `bitcomposer/melody.py`, `harmony.py`, `bass.py`, `arp.py`, `drums.py` | the parts |
| `bitcomposer/registers.py` | the register plan: where the chord, the lead and the counter-line sit, placed once per song |
| `bitcomposer/theory.py`, `structure.py`, `names.py` | scales and chords, song forms, titles |
| `bitcomposer/pattern.py`, `it_format.py` | channel layout, note writing, echo planning; the `.it` writer |
| `bitcomposer/cli.py` | the command line; its parser is also the player's list of compose settings |
| `bitcomposer/player/` | the player: `engine.py` (playlist, playback, auto-generate, the prune and KEEP), the Qt window (`qml/Main.qml`, `backend.py`, `app.py`), `openmpt.py` and `audio.py` (libopenmpt and the sound output), `mpris.py` and `mediakeys_win.py` (media keys), `autostart.py`, `desktop.py` (the Linux menu entry), `update.py` (the release check and UPDATE) |
| `tools/analyze.py` | measures written files (the regression harness behind the tests) |
| `tools/spc_check.py` | measures SPC-to-IT conversions against the emulator, voice by voice; sweeps a folder of SPC files and reports by music driver |
| `tools/make_logo.py` | writes the README logo from the icon and the bundled font |
| `tools/windows/` | the Windows build: PyInstaller launchers, the icon and version-details makers, the Inno Setup installer and its privacy page |
| `docs/` | ANALYSIS, ROADMAP, PORTABILITY, PACKS (the pack file format), SPC-IMPORT (the plan); the listening page (`index.html`, `tracks/`, `player/`), served by GitHub Pages |
| `tests/` | one module per area, sharing `support.py` |

A pack can also be a pack file, with no code at all (`docs/PACKS.md`). A habit or role the
composer starts reading must be added to `packs/packfile.py` too, or pack files cannot carry it;
the round-trip test in `tests/test_packfile.py` fails until it is.

Adding a built-in pack: its module in `bitcomposer/packs/`, registered in
`packs/__init__.py` (the import, `_MODULES` and `PACKS`); its name in the
CLI's `--sound` and `--pack` choices (`cli.py`); and in the player's SOUND
row in `bitcomposer/player/qml/Main.qml`, where the mixer's voice labels
also drop each pack's voice-name prefix (`ffvi_`, `mmx_`, ...) by one
pattern near the top of the file. The random sound draw picks a new pack
up by itself.

The byte-identical check, on one version (the song message records it),
before and after the change:

```bash
mkdir -p /tmp/before
for sound in chip snes genesis ffvi mana evermore megamanx; do for s in $(seq 1 10); do python3 -m bitcomposer.cli --sound $sound -s $s -o /tmp/before/$sound-$s.it; done; done
```

then the same into `/tmp/after`, and compare:

```bash
diff <(cd /tmp/before && sha256sum *.it) <(cd /tmp/after && sha256sum *.it)
```

No output means no song changed. Add the options your change touches
(`--keys home`, `--form aaba`, `--lead-shift -3`, ...) to the loop.

## Building the emulator

The emulator in `emu/` is Rust (why: `docs/SPC-IMPORT.md`), and is the one
part of the repository that needs a compiler: the Rust toolchain
(rustup.rs) and, for the Python module, maturin (`pip install maturin`).
Everything else stays pure Python.

```bash
cd emu
cargo test                          # the emulator alone; no Python involved
maturin build --release -o dist     # the Python module, as a wheel for this machine
```

The wheel is abi3: one file serves every Python from 3.10 on. Install it where the Python tests run (`pip install emu/dist/bitcomposer_emu-*.whl`) and they exercise it too; without it they skip. `bitcomposer/spc/emulate.py` names the emulator version it calls (`NEEDS`); bump both together when the binding changes.

The SNES sound CPU is checked against the SingleStepTests suite, 1,000
cases per instruction (81 MB, not in the repository): fetch
[ProcessorTests](https://github.com/SingleStepTests/ProcessorTests)'
`spc700/v1` folder and run

```bash
SPC700_TESTS=path/to/spc700/v1 cargo test --release -- --nocapture
```

Without `SPC700_TESTS` the suite says it was skipped and passes. To watch
a driver run: `cargo run --release --example run_spc -- song.spc 10`.

### Checking the SPC converter

`tools/spc_check.py` renders a conversion and the emulator's own output and
compares them, the whole mix and then voice by voice (the emulator can play
one voice alone): loudness over time, the gap in dB, the level, the tone,
and each voice's echo against its dry sound. A converter change is judged
this way first and by ear second.

```bash
python3 tools/spc_check.py voice song.spc --seconds 30              # one song, voice by voice
python3 tools/spc_check.py voice song.spc --trace 3 --bands         # voice 3 over time; octave levels
python3 tools/spc_check.py sweep ~/spc /tmp/sweep --workers 12      # every <game>/*.spc under ~/spc
python3 tools/spc_check.py report /tmp/sweep/results.jsonl          # the summary, by music driver
python3 tools/spc_check.py traits ~/spc /tmp/traits.json             # what each song's driver does, per game
python3 tools/spc_check.py doc ~/spc /tmp/traits.json /tmp/sweep/results.jsonl   # docs/drivers/'s measured tables
```

`docs/drivers/` records every game tested, by console and music driver
(a file per driver family): its composer, what the driver does with the
sound chip, the scores and what is still off. A converter change or a new
game updates it from a sweep.

A `drivers.json` beside the game folders (`{"<game folder>": {"driver":
"<driver file>", "game": "<its name>"}}`) names each game's music driver,
which groups the report and decides which file in `docs/drivers/` a game
belongs in. The SPC files and the converted modules
are the user's and stay out of the repository.

## Style

Match the surrounding code. Comments explain *why* — most of them record a
defect that was measured and what the fix changed, so the next reader does
not re-break it.

## Cutting a release

The version lives in one place, `bitcomposer/__init__.py`; pyproject reads
it from there and the publish workflow refuses a tag that does not match it.

1. `CHANGELOG.md`: the Unreleased section becomes `## X.Y.Z — date`, with a
   one-paragraph summary at its top the way the earlier releases have.
2. `bitcomposer/__init__.py`: `__version__ = "X.Y.Z"`.
3. `docs/ROADMAP.md`: move what shipped out of the open items.
4. If the sound changed, regenerate the listening page's tracks so the
   page people hear is the release. Each entry in `docs/tracks/tracks.json`
   names its seed and its sound (the pack in brackets in `arrangement`, or
   else `palette`); write it again with the CLI, e.g.
   `python3 -m bitcomposer.cli --sound megamanx -s 24 -o "docs/tracks/Grotto Charge.it" -v`,
   and bring the entry up to date from the `-v` output (key and tempo,
   voices) and its version. A changed title renames the file.
5. Open a pull request from `dev` into `main`: CI (tests on every Python)
   and the Windows build run on it. Merge when both are green, and wait for
   them to go green again on main's merge commit.
6. Tag and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "X.Y.Z: one line on what it is"
   git push origin vX.Y.Z
   ```

   The tag starts two workflows: `publish.yml` builds the sdist and wheel,
   checks the tag against the version and uploads to PyPI through trusted
   publishing; `windows.yml` builds the executables and the installer,
   installs and uninstalls it on the runner, creates the GitHub release
   from the tag message if none exists, attaches the zip and
   `bitComposer-setup.exe`, and adds the code signing policy link to the
   notes.
7. Check both: `pip install bitcomposer==X.Y.Z` in a fresh venv, and the
   release page carries `bitComposer-windows.zip` and `bitComposer-setup.exe`.
8. Start a player on the previous release (pipx on Linux, the installed
   one on Windows): it should offer UPDATE to the new version and come
   back on it.

The update path can be tried before any tag: `--try-update` makes the
player offer a local file as the update. On a pipx install, build a wheel
(`python3 -m pip wheel --no-deps -w dist .`) and run
`bitcomposer-player --try-update dist/bitcomposer-X.Y.Z-py3-none-any.whl`;
on Windows, `bitComposer.exe --try-update bitComposer-setup.exe` with an
installer from a Windows build.

A pre-release tag (`v1.0.0rc1`) goes through the same path. PyPI lists it
as a pre-release that `pip` and `pipx` only install by exact version, so it
proves the pipeline without becoming anyone's default.
