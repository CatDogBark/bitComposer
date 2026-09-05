# BitComposer — Generation Quality Analysis

**Date:** 2026-09-04
**Analyzed commit:** `548eef1` (last code change 2026-03-11)
**Method:** 8 seeded songs (`-s 1..8`), parsed back from `.it` and measured with
`tools/analyze.py`.

The headline finding: **the output is not limited by algorithmic sophistication.
It is limited by three defects that silently gut the arrangement.** Any work on
smarter generation — statistical or neural — should come *after* these are fixed,
because none of them are things a model can compensate for.

---

## 1. Baseline measurements

Eight songs, default settings, seeds 1–8:

| metric | mean | what it means |
|---|---|---|
| `order_reuse_pct` | **0.0** | fraction of the order list that replays an earlier pattern |
| `mel_uniq_pct` | **99.0** | fraction of melody patterns that are unique |
| `odd_row_pct` | **0.3** | onsets landing on an odd row (16th-note syncopation) |
| `offgrid_pct` | 37.0 | onsets not on a multiple of 4 rows |
| `motif_reuse_pct` | 18.7 | repeated 4-gram interval sequences in the melody |
| `distinct_voicings` | **0.9** | distinct chord interval-stacks per song |
| `harm_static_pct` | **100.0** | harmony voices that never change pitch within a pattern |
| `distinct_ioi` | 10.4 | distinct melodic inter-onset intervals |
| `n_fx` | 2.9 | distinct IT effect commands reaching the file (D, G, H) |

Per-channel density for seed 4 (104 bars of music):

```
melody:  167 notes  = 1 per 10.0 rows
 harm1:   28 notes  = 1 per 59.4 rows
  bass:  400 notes  = 1 per  4.2 rows
   arp:  640 notes  = 1 per  2.6 rows
  kick:   39 notes  = 1 per 42.7 rows
 snare:   12 notes  = 1 per 138.7 rows
   hat:   80 notes  = 1 per 20.8 rows
```

The busiest drum pattern in the entire song (`|` = barline, `+` = quarter note):

```
      |...+...+...+...|...+...+...+...|...+...+...+...|...+...+...+...
kick  X-------------------------------X-------X-------X-------X-------
snare --------------------------------------------X-------X-------X---
hat   X-------X---------------X-------X-------X---------------X-------
mel   X----X----X-X-X---X-----------------X---------X-X-X---X---------
bass  X---X---X---X---X---X---X---X---X---X---X---X---X---X---X---X---
arp   X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-
```

Two full bars with one kick and no snare, under a non-stop arpeggio. That is the
texture of the whole track.

---

## 2. Tier 0 — bugs

These are defects, not design choices. Each is cheap to fix and each one is
individually audible.

### 2.1 The drum grid is stretched 4× — the rhythm section is effectively missing

`pattern.py` → `generate_drums()`:

```python
rows_per_step = rows // 16   # = 4
```

The 16-step templates in `theory.py` are unmistakably authored as **one bar of
16th notes**: "Standard rock" is kick on 1/2/3/4, snare on 2 and 4, hats on 8ths.
Expanding them at 4 rows/step spreads that single bar across all four bars of the
64-row pattern, so everything plays at quarter speed:

- kick → once per bar
- snare → downbeat of bars 2 and 4 (not a backbeat at all)
- hats → quarter notes

Measured consequence: **39 kicks and 12 snares across 104 bars.** A snare every
8.7 bars. The `DRUM_PATTERNS_BUSY`, "Double-time" and "Funky" templates are
indistinguishable from the sparse ones, because all of them are reduced to
quarter-note soup.

**Fix:** treat the 16 steps as one bar (1 row per step) and tile the pattern 4×
across the 64 rows. The swing offset in `apply_drums_to_pattern()`
(`row % 8 == 4`) assumes the stretched grid and must be rescaled with it.

### 2.2 Nothing in the song ever repeats

`composer.py` caches generated patterns as:

```python
cache_key = (section, chord_idx)
```

Section keys are `chorus1`, `chorus2`, `chorus3` — *distinct keys*. So every
chorus is freshly re-rolled with a new melody, a new random register, and new
everything. Measured: **order-reuse 0.0% on all 8 songs; 99% of melody patterns
unique.** A 24-order song uses 26 distinct patterns.

This also means the **rondo form's documented behaviour does not happen**. The
README promises "main theme returns between contrasting sections"; in practice
`theme1`, `theme2` and `theme3` are three unrelated pieces of music.

This is the deepest reason the output sounds like noodling rather than a song:
there is no hook, because the hook never comes back. `melody.py` compounds it —
`_generate_melody_phrased()` re-rolls `register` per pattern, so even a shared
motif lands in a different octave each time it appears.

**Fix:** key the cache by section *type* so repeated sections share patterns, and
opt out deliberately (a variation, not a re-roll) where contrast is wanted.

### 2.3 Harmony is a pitch metronome

`harmony.py` picks one `base_note` per voice and then retriggers *that same
pitch* every `interval` rows for the whole pattern. Measured: **100% of harmony
voices are static within a pattern, in every song.** Combined with `build_chord()`
only ever emitting root position, that yields the measured 0–2 distinct voicings
per song. No voice leading, no inversions, no movement.

It is also nearly inaudible — 28 harmony note events across 104 bars in seed 4.

---

## 3. Tier 1 — design ceilings

Not bugs, but hard limits on how good the output can get.

- **Rhythm is locked to an 8th-note grid.** All eight `RHYTHM_TEMPLATES` in
  `melody.py` use even offsets only; **0.3% of onsets land on an odd row**. No
  syncopation finer than an 8th, no triplets, no dotted rhythms, and no
  anticipations — pushing a note a 16th ahead of the beat is the single most
  effective "musical" device that is entirely absent.
- **Arp and bass never rest.** `bass.py` → `generate_arpeggio()` writes a note
  every 2 rows for all 64 rows regardless of style or section energy. 640 arp
  notes vs 167 melody notes: the arp is the densest thing in the mix and it never
  breathes. `generate_bass()` has the same unconditional-loop shape.
- **Tiny harmonic vocabulary.** 2–4 progressions per scale, all four chords long,
  all diatonic. `CHORD_INTERVALS` defines `7th`, `sus4`, `dim` and `aug` but
  `PROGRESSIONS` uses only `major`, `minor` and `power` — the others never reach
  output. No secondary dominants, borrowed chords, modal interchange, or pedal
  points. Game music leans heavily on ♭VI/♭VII and sus resolutions; none present.
- **3 IT effects out of ~30.** Only D (volume slide), G (portamento) and H
  (vibrato) reach the file. Missing the ones that define the idiom: **Jxy
  arpeggio** (the classic single-channel chord), **Qxy retrigger**, **SDx note
  delay** (flams, humanisation), Oxx sample offset, and panning. `FX_TREMOLO` is
  imported into `composer.py` and never used.
- **Dead code.** `theory.passing_chord()`, `theory.get_chord_for_degree()` and
  `theory.note_from_name()` have zero references.
- **Orphaned patterns.** `silence_inactive_channels()` deep-copies patterns and
  appends them, leaving the originals unreferenced in the order list — files
  carry more patterns than they play (26 patterns for 24 orders in seed 1).
- **No tests and no regression harness** before this document; nothing indicated
  whether a change made the music better or worse.

---

## 4. Measuring changes

`tools/analyze.py` is self-contained (stdlib only, no dependency on the generator
itself) and scores a batch of `.it` files on all the metrics in §1:

```bash
python3 -m bitcomposer.cli -s 1 -o /tmp/out/s1.it
python3 tools/analyze.py '/tmp/out/*.it'          # batch metric table
python3 tools/analyze.py --grid /tmp/out/s1.it    # tracker-style pattern dump
```

Grade generator changes against these numbers on **fixed seeds**, before and
after. Ear-checking alone has repeatedly missed the defects above — the drum
stretch survived nine commits and a full README write-up.

---

## 5. Roadmap for smarter generation

Ordered by return on effort. The important claim is that **steps 1–2 must precede
step 3**: a learned model cannot fix a stretched drum grid or a chorus that never
repeats, because those are arrangement-layer facts, not note-choice facts.

1. **Fix Tier 0.** Cheap, deterministic, individually audible.
2. **Lift the Tier 1 ceilings** that are pure code: 16th-note rhythm templates and
   anticipations, arp/bass rests tied to section energy, extended chord types and
   secondary dominants, and the J/Q/SDx effect vocabulary.
3. **Corpus statistics — no neural net.** Train n-gram / Markov tables on real
   chiptune (NESMDB, ~5k NES songs already symbolic; or the Modland module
   archive). Learn chord-transition probabilities, melodic interval distributions
   conditioned on scale degree and chord tone, and real rhythm-template
   frequencies. A few hundred lines, trained offline, shipped as a JSON table —
   **this preserves the project's zero-runtime-dependency property.** Best
   quality-per-effort on the list.
4. **A small conditioned transformer.** ~5–20M parameters over a note-event
   vocabulary, trained on the same corpus. Condition it on chord, section type and
   bar index and use it for the *melody line only* — keep structure, repetition
   and arrangement in deterministic code, since long-range form is exactly what
   small models are worst at.
5. **A local LLM as arranger, not note-generator.** Ask for a style brief → JSON
   (key, scale, progression set, form, instrument palette, energy curve,
   per-section texture plan) that drives the existing engine. Small typed output
   where musical world-knowledge helps and validation is trivial. Orthogonal to
   3–4 and cheap. Would also produce real song titles instead of
   `BitComposer - C Dorian`.

### Training hardware

Model training is **not** intended for the dev laptop (Precision 5750, Quadro RTX
3000 Max-Q, 6 GB VRAM — enough to *run* a small model, tight for anything else).
Available instead:

- **TESLA GPU box — 24 GB VRAM.** Existing AI training procedures already
  developed on this machine; the intended target for steps 3–4.
- **Ragnarok — GeForce 5080.**

Both are far more than a symbolic music model needs (these are megabyte-scale, not
gigabyte-scale). VRAM is not the constraint; corpus preparation is.
