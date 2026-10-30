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

## Issues and pull requests

Anyone can open an issue: a problem (the form asks for the version and what
happened) or an idea. A security problem goes privately instead, as
[SECURITY.md](SECURITY.md) says.

Pull requests come from collaborators. To work on something, open an issue
about it first; the maintainer invites contributors as collaborators.
Collaborators push branches of their own and open pull requests into `dev`;
only the maintainer merges into `dev` and `main` and makes release tags
(`v*`), and only `main` and those tags can reach the signing and PyPI
environments.

## Before you open a pull request

1. Run the tests:

   ```bash
   python3 -m unittest discover -s tests -v
   ```

   On a machine with many cores, `python3 tools/run_tests.py` runs the same
   suite in parallel, each test in a process of its own (`--workers N` for
   fewer; a module prefix such as `test_spc` for part of it): as long as its
   longest test rather than all of them added up.

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
| `bitcomposer/translate/` | the translator (`docs/TRANSLATOR.md`): a song's played notes read as music (`events.py` the notes, `beat.py` beat and bar, `roles.py` each voice's part, `harmony.py` key and chords, `form.py` its parts and loop, `reading.py` all of it), kept in a database on the user's machine (`store.py`); `measures.py` the yardsticks shared by a soundtrack and the generator's songs; `pack.py` a thin pack from a game's songs; `archives.py` a game's SPC files from a folder, a zip or a set 7-Zip or unar unpacks; `python -m bitcomposer.translate` |
| `bitcomposer/packs/` | one module per style pack: its voices, their registry entries and its `PACK` habits; `packfile.py` reads pack files (`docs/PACKS.md`); `library.py` the packs on this machine, for the player's PACKS panel (import in a worker process, add, export, move a voice, previews) |
| `bitcomposer/melody.py`, `harmony.py`, `bass.py`, `arp.py`, `drums.py` | the parts |
| `bitcomposer/registers.py` | the register plan: where the chord, the lead and the counter-line sit, placed once per song |
| `bitcomposer/theory.py`, `structure.py`, `names.py` | scales and chords, song forms, titles |
| `bitcomposer/pattern.py`, `it_format.py` | channel layout, note writing, echo planning; the `.it` writer |
| `bitcomposer/cli.py` | the command line; its parser is also the player's list of compose settings |
| `bitcomposer/player/` | the player: `engine.py` (playlist, playback, auto-generate, the prune and KEEP, voice previews), the Qt window (`qml/Main.qml`, `backend.py`, `app.py`; the PACKS panel is in them), `openmpt.py` and `audio.py` (libopenmpt and the sound output), `mpris.py` and `mediakeys_win.py` (media keys), `autostart.py`, `desktop.py` (the Linux menu entry), `update.py` (the release check, CANDIDATES, UPDATE and GET THE EMULATOR) |
| `tools/analyze.py` | measures written files (the regression harness behind the tests) |
| `tools/spc_check.py` | measures SPC-to-IT conversions against the emulator, voice by voice; sweeps a folder of SPC files and reports by music driver |
| `tools/make_logo.py` | writes the README logo from the icon and the bundled font |
| `tools/windows/` | the Windows build: PyInstaller launchers (`launch_player.py` is also IMPORT's worker, started with `library.WORKER`), the icon and version-details makers, the Inno Setup installer and its privacy page |
| `docs/` | ANALYSIS, ROADMAP, PORTABILITY, PACKS (the pack file format), SPC-IMPORT (the plan), TRANSLATOR (its stages); the listening page (`index.html`, `tracks/`, `player/`), served by GitHub Pages |
| `tests/` | one module per area, sharing `support.py` |

A pack can also be a pack file, with no code at all (`docs/PACKS.md`). A habit or role the
composer starts reading must be added to `packs/packfile.py` too, or pack files cannot carry it;
the round-trip test in `tests/test_packfile.py` fails until it is.

Adding a built-in pack: its module in `bitcomposer/packs/`, registered in
`packs/__init__.py` (the import, `_MODULES` and `PACKS`); its name in the
CLI's `--sound` and `--pack` choices (`cli.py`); and in the player's
`builtinSounds` list in `bitcomposer/player/qml/Main.qml` (the SOUND row:
the built-in sounds, then the packs on this machine), where the mixer's voice labels
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

`emu/Cargo.lock` is committed, so every wheel of a version is built from
the same crates; `cargo update` is a change to review like any other.

### Releasing the emulator

The emulator is published on PyPI as `bitcomposer-emu`, with a binary
wheel for each platform, on its own tags, apart from the package's
releases (it changes rarely, and a `bitcomposer` release needs no new
emulator unless `NEEDS` moved). The version lives in `emu/Cargo.toml` and
`emu/pyproject.toml`, which must agree, and the tag names it:

1. Bump both versions and, if the binding changed, `NEEDS` in
   `bitcomposer/spc/emulate.py` and the extra's floor in `pyproject.toml`.
2. Tag and push the tag, from `main` once the change is there:

   ```bash
   git tag -a emu-v0.3.2 -m "emulator 0.3.2: one line on what it is"
   git push origin emu-v0.3.2
   ```

   `emu.yml` runs the Rust tests with the whole instruction suite (fetched
   from SingleStepTests), builds a wheel for Linux x86_64 and aarch64,
   Windows x64, macOS arm64 and x86_64, and the sdist, runs the SPC tests
   against each wheel, and uploads them all through trusted publishing
   (the `pypi` environment, the pending publisher registered on pypi.org
   for this workflow file). Pull requests into `main` that touch `emu/`
   build and test the same way and publish nothing, as does a run started
   by hand (`gh workflow run emu.yml --ref <branch>`).
3. Check: `pip install bitcomposer-emu==0.3.2` in a fresh venv, and
   `python -m bitcomposer.spc --to-it song.it game.spc` runs on it.

Where no wheel matches (another architecture, a free-threaded Python,
which abi3 does not serve), pip takes the sdist and needs cargo; that is
why `bitcomposer` asks for the emulator as the `import` extra and not as
a dependency. On a pipx install the player's UPDATE asks for the extra
whenever the emulator is installed (`player/update.py`), so a release
that raises `NEEDS` brings the emulator along, and pipx remembers the
extra for a `pipx reinstall`.

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

`tools/spc_check.py` (it needs numpy, `pip install numpy`, for the arithmetic;
the package does not) renders a conversion and the emulator's own output and
compares them, the whole mix and then voice by voice (the emulator can play
one voice alone): loudness over time, the gap in dB, the level, the tone,
and each voice's echo against its dry sound. A converter change is judged
this way first and by ear second.

```bash
python3 tools/spc_check.py voice song.spc --seconds 30              # one song, voice by voice
python3 tools/spc_check.py voice song.spc --trace 3 --bands         # voice 3 over time; octave levels
python3 tools/spc_check.py sweep ~/spc /tmp/sweep --workers 12      # every <game>/*.spc under ~/spc
python3 tools/spc_check.py report /tmp/sweep/results.jsonl          # the summary, by music driver
python3 tools/spc_check.py sweep ~/spc /tmp/smoke --smoke /tmp/sweep/results.jsonl   # each driver's worst, a minute
python3 tools/spc_check.py sweep ~/spc /tmp/next --since /tmp/sweep/results.jsonl    # only what changed is measured
python3 tools/spc_check.py report /tmp/next/results.jsonl --against /tmp/sweep/results.jsonl   # what moved
python3 tools/spc_check.py traits ~/spc /tmp/traits.json             # what each song's driver does, per game
python3 tools/spc_check.py doc ~/spc /tmp/traits.json /tmp/sweep/results.jsonl   # docs/drivers/'s measured tables
python3 tools/spc_check.py family ~/spc                            # which games' drivers share code
```

`docs/drivers/` records every game tested, by console and music driver
(a file per driver family): its composer, what the driver does with the
sound chip, the scores and what is still off. A converter change or a new
game updates it from a sweep.

A `drivers.json` beside the game folders (`{"<game folder>": {"driver":
"<driver file>", "game": "<its name>"}}`) names each game's music driver,
which groups the report and decides which file in `docs/drivers/` a game
belongs in. `family` helps choose: it compares the games' driver code. The SPC files and the converted modules
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
   If the release calls a newer emulator (`emulate.NEEDS`), release that
   first (Releasing the emulator, above) and raise the `import` extra's
   floor in `pyproject.toml` to it; a test fails until the two agree, and
   UPDATE then brings the new emulator with the release.
4. If the sound changed, regenerate the listening page's tracks so the
   page people hear is the release. Each entry in `docs/tracks/tracks.json`
   names its seed and its sound (the pack in brackets in `arrangement`, or
   else `palette`); write it again with the CLI, e.g.
   `python3 -m bitcomposer.cli --sound megamanx -s 24 -o "docs/tracks/Grotto Charge.it" -v`,
   and bring the entry up to date from the `-v` output (key and tempo,
   voices) and its version. A changed title renames the file.
   If the window changed, retake the README's picture of it after step 2,
   so it shows the new version; a home folder of its own keeps the four
   demo songs out of your Music folder and still shows `~/Music/bitComposer`:

   ```bash
   HOME=$(mktemp -d) sh -c 'python3 -m bitcomposer.player --screenshot docs/images/player.png --screen 800x1440 --scale 2 --music-dir "$HOME/Music/bitComposer"'
   ```
5. Open a pull request from `dev` into `main`: CI (tests on every Python)
   and the Windows build run on it. Merge when both are green. There is
   nothing to wait for after the merge: main takes nothing but these pull
   requests, so the merge commit is the tree the pull request tested (CI
   runs once more on the push, for the README's badge; the Windows build
   does not).
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
   back on it. On a pipx install without the emulator, PACKS' GET THE
   EMULATOR should add it and come back with IMPORT ready.

The update path can be tried before any tag: `--try-update` makes the
player offer a local file as the update. On a pipx install, build a wheel
(`python3 -m pip wheel --no-deps -w dist .`) and run
`bitcomposer-player --try-update dist/bitcomposer-X.Y.Z-py3-none-any.whl`;
on Windows, `bitComposer.exe --try-update bitComposer-setup.exe` with an
installer from a Windows build.

A pre-release tag (`v1.0.0rc1`) goes through the same path. PyPI lists it
as a pre-release that `pip` and `pipx` only install by exact version, so it
proves the pipeline without becoming anyone's default. UPDATE offers it to
a player on a candidate, and to a release player whose SET → PLAYER →
CANDIDATES is on.
