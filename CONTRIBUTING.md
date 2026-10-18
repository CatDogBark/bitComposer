# Contributing

bitComposer is small on purpose: the generator is pure Python with no runtime
dependencies (the player adds Qt), and every generator change is judged by
measurement rather than by ear alone.

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
| `bitcomposer/packs/` | one module per style pack: its voices, their registry entries and its `PACK` habits |
| `bitcomposer/melody.py`, `harmony.py`, `bass.py`, `arp.py`, `drums.py` | the parts |
| `bitcomposer/registers.py` | the register plan: where the chord, the lead and the counter-line sit, placed once per song |
| `bitcomposer/theory.py`, `structure.py`, `names.py` | scales and chords, song forms, titles |
| `bitcomposer/pattern.py`, `it_format.py` | channel layout, note writing, echo planning; the `.it` writer |
| `bitcomposer/cli.py` | the command line; its parser is also the player's list of compose settings |
| `bitcomposer/player/` | the player: `engine.py` (playlist, playback, auto-generate, the prune and KEEP), the Qt window (`qml/Main.qml`, `backend.py`, `app.py`), `openmpt.py` and `audio.py` (libopenmpt and the sound output), `mpris.py` and `mediakeys_win.py` (media keys), `autostart.py`, `desktop.py` (the Linux menu entry), `update.py` (the release check and UPDATE) |
| `tools/analyze.py` | measures written files (the regression harness behind the tests) |
| `tools/make_logo.py` | writes the README logo from the icon and the bundled font |
| `tools/windows/` | the Windows build: PyInstaller launchers, the icon and version-details makers, the Inno Setup installer and its privacy page |
| `docs/` | ANALYSIS, ROADMAP, PORTABILITY; the listening page (`index.html`, `tracks/`, `player/`), served by GitHub Pages |
| `tests/` | one module per area, sharing `support.py` |

Adding a pack: its module in `bitcomposer/packs/`, registered in
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
5. Commit, push to main, wait for CI (tests on every Python) and the Windows
   build to go green on that commit.
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
