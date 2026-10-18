# Contributing

bitComposer is small on purpose: the generator is pure Python with no runtime
dependencies (the player adds Qt), and every generator change is judged by
measurement rather than by ear alone.

## Before you open a pull request

1. Run the tests:

   ```bash
   python3 -m unittest discover -s tests -v
   ```

2. If you touched anything in `bitcomposer/`, generate a fixed batch before
   and after your change and paste both analyzer tables in the PR:

   ```bash
   for s in $(seq 1 12); do python3 -m bitcomposer.cli -s $s -d /tmp/before; done
   python3 tools/analyze.py '/tmp/before/*.it'
   ```

   `docs/ANALYSIS.md` explains what the columns mean and why ear-checking
   alone has repeatedly missed real defects here.

3. Keep seeded output deterministic. If your change alters what a seed
   produces, say so; that is fine, silently breaking it is not.

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
| `bitcomposer/theory.py`, `structure.py`, `names.py` | scales and chords, song forms, titles |
| `bitcomposer/pattern.py`, `it_format.py` | channel layout, note writing, echo planning; the `.it` writer |
| `bitcomposer/cli.py`, `gui.py` | the command line and the small tkinter generate window |
| `tools/analyze.py` | measures written files (the regression harness behind the tests) |
| `tests/` | one module per area, sharing `support.py` |
| `bitcomposer/player/` | the player: the engine, the Qt window (`qml/Main.qml`, `backend.py`, `app.py`), MPRIS, start at login, the menu entry, updates |

Adding a pack is one file in `bitcomposer/packs/` plus its name in the CLI
and in the player's SOUND row (`bitcomposer/player/qml/Main.qml`). Moving code between modules must keep generation
byte-identical: write twenty seeds before, twenty after, compare the files.

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
4. Regenerate the listening page (`docs/index.html`, `docs/tracks/`) if the
   sound changed, so the page people hear is the release.
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

A pre-release tag (`v1.0.0rc1`) goes through the same path. PyPI lists it
as a pre-release that `pip` and `pipx` only install by exact version, so it
proves the pipeline without becoming anyone's default.
