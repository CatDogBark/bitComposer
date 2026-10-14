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
| `bitcomposer/theory.py` | scales, chord tables, progressions, drum templates |
| `bitcomposer/melody.py`, `harmony.py`, `bass.py` | the parts |
| `bitcomposer/samples.py` | every instrument, including the SNES palette and BRR model |
| `bitcomposer/composer.py` | arrangement: structure, chord timeline, palettes, echo |
| `bitcomposer/it_format.py` | the Impulse Tracker writer |
| `tools/analyze.py` | standalone .it parser and metric harness |
| `companion/` | optional Linux/KDE Plasma 6 player (daemon, widget, scripts) |

## Style

Match the surrounding code. Comments explain *why* — most of them record a
defect that was measured and what the fix changed, so the next reader does
not re-break it.
