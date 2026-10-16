# Contributing

bitComposer is small on purpose: pure Python, no runtime dependencies, and
every generator change is judged by measurement rather than by ear alone.

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
| `bitcomposer/cli.py`, `gui.py` | the command line and the Windows window |
| `tools/analyze.py` | measures written files (the regression harness behind the tests) |
| `tests/` | one module per area, sharing `support.py` |
| `companion/` | the Plasma widget, the daemon and the scripts |

Adding a pack is one file in `bitcomposer/packs/` plus its name in the CLI
and widget choices. Moving code between modules must keep generation
byte-identical: write twenty seeds before, twenty after, compare the files.

## Style

Match the surrounding code. Comments explain *why* — most of them record a
defect that was measured and what the fix changed, so the next reader does
not re-break it.
