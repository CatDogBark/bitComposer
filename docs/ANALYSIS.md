# bitComposer — Generation Quality Analysis

**Started:** 2026-09-04, on commit `548eef1` (last code change 2026-03-11).
Kept since as the record of every measured pass, through 1.0.0 (§2e,
2026-10-18).
**Method:** seeded songs parsed back from `.it` and measured with
`tools/analyze.py`; levels and pitches by rendering one part alone through
libopenmpt (§4). The first analysis used 8 songs (`-s 1..8`).

The first analysis's headline: **the output is not limited by algorithmic sophistication.
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

## 2b. Tier 0 results

Fixed on branch `tier0-fixes`; baseline preserved at tag `pre-tier0`.

20 seeds, default settings, drum hits per bar:

| | before | after | healthy range |
|---|---|---|---|
| kick | 0.77 | **2.88** | 2–4 |
| snare | 0.44 | **1.67** | ~2 |
| hat | 1.95 | **6.59** | 4–8 |

6 seeds per form, `--harmony-voicing full`:

| form | order reuse | melody uniqueness | motif reuse | voicings |
|---|---|---|---|---|
| standard | 6.4 → **19.3** | 100 → **66.0** | 20.5 → **70.9** | 4.0 → **6.5** |
| aaba | 4.5 → **15.7** | 99.3 → **43.2** | 24.5 → **81.6** | 2.3 → **4.0** |
| rondo | 0.0 → **14.2** | 100 → **71.3** | 19.3 → **64.5** | 3.3 → **5.8** |
| short | 0.0 → 0.0 | 99.0 → **77.8** | 22.9 → **55.1** | 2.8 → **5.2** |
| linear | 0.0 → 0.0 | 99.3 → 97.9 | 24.2 → 24.7 | 2.3 → **4.0** |

`linear` is deliberately almost unchanged — it is through-composed, so it
*should* not repeat. That it held still while every other form moved is the
check that the reuse change is targeted rather than a blanket flattening.

Voice motion between consecutive patterns fell 4.4 → 2.6 semitones, i.e. the
harmony now steps rather than leaping between root positions.

Seeded output remains byte-identical run to run.

## 2c. Tier 1 results

**Date:** 2026-10-13. Released as v0.3.0. Twenty seeds, default settings,
measured with `tools/analyze.py` and decoded through libopenmpt for levels.

| metric | Tier 0 (Sep 4) | before this pass | after | note |
|---|---|---|---|---|
| `odd_row_pct` | 0.6 | 3.2 | **8.1** | 16th-note figures in the melody templates |
| `distinct_ioi` | 10.2 | 8.4 | **11.8** | more rhythmic variety |
| `distinct_voicings` | 1.6 | 3.2 | **4.5** | two chords per pattern, borrowed chords |
| `order_reuse_pct` | 3.3 | 5.4 | **7.5** | orphan copies gone |
| `motif_reuse_pct` | 48.3 | 58.8 | 59.2 | held |
| patterns / orders | 25.6 / 24.7 | 27.4 / 26.0 | 27.4 / 30.0 | every pattern in the file is now played |
| kick / snare / hat per bar | 2.88 / 1.67 / 6.59 | 2.83 / 1.68 / 7.45 | 2.64 / 1.54 / 6.96 | unchanged within seed variance |
| peak level | — | −6.0 to −7.5 dBFS | −6.0 to −8.7 dBFS | SNES palette ~2 dB quieter |

Seeded output is byte-identical run to run; 25 unit tests in `tests/` cover
determinism, format, tempo, the arrangement thresholds above, every option
combination, loop seams and pattern operations.

### What changed

**Harmonic rhythm.** Each pattern carried one chord for four bars, so a
four-chord progression took sixteen bars to come round. Patterns now hold a
chord timeline; with per-section odds (verse 0.5, chorus 0.55, bridge 0.6)
the back two bars move to a related chord — the next one in the progression
anticipated, the plagal neighbour, or the dominant of the current chord.
Melody, harmony, bass and arp all follow the timeline, and the melody
resolves onto a chord tone at each change.

**Harmonic vocabulary.** Progression entries can carry a chromatic shift, so
major now has I–♭VII–IV, I–♭VI–♭VII, II (V/V) and III (V/vi); natural minor
gained i–VI–III–VII, the Andalusian i–VII–VI–V and a borrowed major V.
`major_pentatonic` had been falling back to the natural-minor table, which
indexed degrees 5 and 6 past the five-note scale and put minor triads on a
major scale; it has its own progressions now.

**Melody rhythm.** Six 16th-note templates (dotted-eighth push, anticipated
third beat, pickups, flams) join the eight even-grid ones, and motif
variation can nudge a note by a single row.

**Sound: SNES palette.** `--style snes` previously meant "square and triangle
waves without FM" — a NES/Game Boy sound. The SPC700 was a sample player:
short 8–16 kHz BRR samples with loop points, through a hardware echo. The new
palette renders 21 voices that way — strings, brass, choir (formant-weighted,
so they chipmunk with pitch like the real thing), flute, organ, e-piano,
bell, marimba, pizzicato, harp, three basses, an orchestra hit and a gated
drum kit — at 16 kHz with attack-then-loop sustain, run through a BRR codec
model (all four SPC700 prediction filters, 4-bit residuals, per-block shift)
for the grain. The old waveform set is now `--style chip`.

**Levels.** Every tonal preset is normalised in `samples.generate_instrument`
so the channel mix means the same thing whichever voice a song drew.
Sustaining voices (loop as loud as the attack) are scaled so their loop sits
at `LOUDNESS_TARGET` RMS, which is where the SNES strings, organ and brass
already were, so a chip square comes down ~6 dB and the FM lead ~5 dB.
Struck voices (plucks, bells, e-piano, pizz, harp, marimba: loop region
under 0.8× the strike, or no loop at all) carry their energy in the attack,
and the loop rule leaves them at their natural peak-capped level. On the arp,
where every note is a strike, that left the SNES bell 7 dB over the pizz, so
the arp's sample is scaled on the RMS of its first 150 ms to `STRIKE_TARGET`
instead; the spread across the five SNES arp voices went from 8.6 dB to
4.2 dB and the per-palette arp trims went away. Leads and harmony keep the
natural level: a struck lead lives on its decay, and its attack is already at
full scale, so nothing could give back what the strike rule took. The one
trim left is the genesis PSG square as an arp, a held tone among strikes.

**Style packs.** The FFVI sound is as much habit as timbre: ostinato
strings under a brass melody, a horn answering the lead, timpani into
the chorus. So a pack (one module in `bitcomposer/packs/`) pairs voices per role with weighted
draws for the composer's habits (tempo, energy, scale family, harmony
voicing and mode, bass weight and style, drum density and swing, echo
chance, wetness and stereo), a counter-line voice and chance, orchestral
fills and channel trims. Anything a pack does not weight is drawn the
plain way, so a pack is a narrowing, never a new engine. A pack's lead,
harmony and bass pools hold only its own voices (a Mega Man X song that
drew a plain synth lead, organ and slap bass sounded like neither), and the
picker refuses three sustaining voices in overlapping registers: with no
struck voice among lead, harmony and arp and no pad-like harmony, the
harmony is redrawn from the pool's struck or pad voices. Two harmony
modes arrived with it: `ostinato` restrikes the chord tones on a 3+3+2
cell, `pulse` on straight eighths with the upper voices between the
beats. The string section is a long loop (160 periods plus the attack)
carrying the tone and copies one cycle sharp and flat over the loop, so
it beats at about 1.6 Hz and stays seamless.

**Packs from the banks.** An SPC snapshot carries the whole sound chip, so a
pack can be built from measurement rather than memory. The method, first
used for Mega Man X and then FFVI: decode every snapshot's BRR directory,
deduplicate samples across the set by their PCM, profile each (steady-state
harmonics on a loop-aligned window, centroid, attack and decay, loop length),
then trace it through the voice registers of every snapshot it sounds in
(sounding pitch from the pitch register, ADSR, echo bit, volume) to learn
its role. The DSP registers give the echo outright. FFVI: 82 snapshots, 71
unique samples, of which eight tiny loops are the driver's fixed set; the
other 63 each matched one row of the community's documented instrument
table by BRR size to within two bytes, which settled every identity (the
song-based guesses had the choir and pipe organ swapped, and the game's
most-used lead is a synth, not a horn). The table is the FF6 hacking
community's BRR sample list (ff6hacking.com wiki, `ff3:ff3us:music:
brrsamples:ff6`; see ROADMAP "Pack revisions" for the links). Secret of
Mana has no such table: its 69 snapshots gave 166 directory entries, of which
the ones that sound reduce to about thirty instruments, named by measured
character and the role the voice registers show (a soft flute in 44 banks,
strings in 43, choir in 28), with the fan soundfont's vocabulary as the
guide; the echo there is a one-row delay (96 and 176 ms), feedback 0.31,
wet. Secret of Evermore streams a small set per song (131 samples over 72
snapshots, about thirty recurring); William Kage's named rips settled seven
by exact length, the rest are by character, and the DSP registers showed the
echo off in two thirds of the snapshots and light where on, so the pack's
"wet" habit was wrong: Evermore's space is in its long swells and textures.
Mega Man X, re-checked the same way: 20 of its samples matched Kage's rips,
and the by-ear pass had the arp voice (the overdrive guitar), the soft lead
(the organ), the bass (slap bass) and the "string pad" (a distortion guitar
with a 155 ms swell) under the wrong names, while the real strings, in every
bank, were missing. The shapes were right; the names and the gaps were not. Every snapshot runs 80 ms of echo
with feedback 0.64 and a flat filter, both sides the same sign, strings and
leads sent, bass and kit dry. Each recipe in the pack states the profile it
targets and a matcher (`tools/match.py` in the diag dir) prints ours beside
it; the sustaining voices land within a few points on every partial.

**Level.** The mix was tuned for balance with the overall level never
revisited: files averaged −27 LUFS, ten dB under anything streamed and
four under broadcast. The module's mix volume is now written at 128 (it
was 80) and every channel volume carries a master gain of 1.25
(`composer.MASTER_GAIN`); over eighteen seeds across the palettes that is
about −20 LUFS with the loudest song's true peak a decibel under full
scale. No limiter or compression: the dynamics (an 11 LU range on some
songs) are left alone, and the players' gain (bitComposer's player has one
with a soft limiter; XMPlay amplifies) covers the rest.

**Chorus.** Every ensemble voice (`_ensemble_voice`: the FFVI strings and
contrabass, the Mana glass pad, the Evermore pads and drone) and the Mega
Man X lead guitar carried their chorus as equal detuned copies summed
with the tone. Measured by rendering each voice at the three pitches the
melody sounds at (midi 60, 72, 83, which at the time sounded an octave
below their labels, 131, 262, 495 Hz: the note-conversion error fixed in
§2e) and watching the fundamental's share of power across
four windows, that construction is a comb: once per beat cycle the copies
sit in antiphase to the tone and the odd partials cancel, so the share
swung by 60-90 points. The dry tone now leads at 80% (`ENSEMBLE_DRY`)
with the two copies a cycle sharp and two cycles flat, never in antiphase
together; the swing is under 15 on every voice. The flute, whistle, pan
flute and horn, the only leads under 1.4 times the fundamental, gained a
little second and third partial.

**Echo.** Modelled on what the SNES echo unit produced rather than how it
was wired: three repeats on a dotted eighth (3, 6 and 9 rows), each half
the level of the last (−6, −12, −18 dB), each playing a lowpassed copy of
the lead sample (two-pole at 4, 2 and 1 kHz) so the repeats darken as they fade,
the way the hardware's filter did on every feedback pass. The copies are
separate samples (`samples.echo_variant`), since a tracker has no send
effects; `pattern.plan_echo` places the taps on the return channels,
lets the louder win where two land together, ends each copy where its
source note ended, and carries the source's effect column (fades,
vibrato) under the copy so a stab's echo decays like the stab. Unlike the
hardware, which echoed everything a voice played, the lead sends only held
notes (≥ 4 rows) and phrase endings (a rest of ≥ 2 rows follows), about
70% of lead notes, so fast runs stay dry. The hardware had one on/off bit
per voice; here each part has its own send (`composer.ECHO_SENDS`): lead
at ½, harmony at 0.3 and arp at 0.35 of the part, repeats below 8%
dropped, drums and bass dry. Returns live on seven channels (lead 2,
harmony 3, arp 2; `pattern.CH_ECHO_ALL`, 19 channels in all) and the song
message carries a `layout:` line naming every channel's role so a player's
mixer (bitComposer's own does) can fold them into one ECHO bus. Measured on four SNES songs: returns sit
6 dB under the lead, 12–14 dB under the harmony and 9–11 dB under the
arp; all returns together 2–6 dB under the melody.

Each song draws its own echo from a stream of its own (`song_salt ^
0xEC40`, so the arrangement never moves when the echo options change):
the delay as a beat fraction weighted by tempo (eighth, dotted eighth or
quarter; fast songs favour the longer ones), feedback 0.3–0.6, a wetness
(light 25% / normal 50% / wet 25%, `--echo-wet` overrides), and a stereo
mode (`--echo-stereo`); a fourth delay, "slap", is 48 ms under a row (the
Mega Man X echo, read from the game's DSP registers: 48 ms, feedback 0.53,
inverted sides) written as an SDx tick delay on the copy's note row.
"bounce" alternates sides per tap, "centre" puts
every repeat under its source, the way the hardware's two-sided echo read
(a one-sided "spread" mode was tried and heard as a second player coming
in late, so it went). Pans are written per tap as an Xxx effect on the
copy's note row, so taps sharing a channel can still bounce. Every send
is scaled by section (`ECHO_SECTION_GAIN`): opened in intros, bridges and
outros, pulled back to 0.7 in the chorus where the arp and harmony fill
the space. The arp sends only its accented steps (strong and normal) and
its send tapers with tempo, full to 130 BPM and gone by 170: at 180 BPM a
dotted-eighth repeat of an eighth-note pizzicato landed one row after
every pluck and the arp became a stream of ticks (Veiled Meridian).
The drawn settings are written into the song message
("echo: dotted delay, feedback 0.45, bounce, wet"). Left to chance, 70%
of snes songs get the echo and chip and genesis never do (neither chip
had an echo unit); `--echo` overrides. The player's mixer reads the
channel roles from the `layout:` line, so it follows whatever the composer
writes.

**Bugs fixed on the way.**

- Chorus modulation shifted chord roots a semitone but not the scale, so the
  melody sat a semitone under its own harmony for every modulated chorus.
- Intro "fade-in" wrote volume slide-ups onto notes already at full volume,
  making the intro louder than the song; fade-outs were undone by each
  note's volume column. Both now scale the volume columns and slide held notes.
- Harmony `sustain` mode decayed at 2 per tick — a pad died in six rows and
  the mode was indistinguishable from stabs. Decay is now per voicing, with a
  fine per-row slide for sustain.
- `silence_inactive_channels` deep-copied a pattern per order slot to add a
  cut, leaving unplayed orphan patterns and defeating order-list reuse. Cuts
  are written in place.
- Single-cycle waveforms were six cents sharp (integer period at 44.1 kHz
  reported as 44100 Hz); every sample now reports the exact rate its period
  implies.

**Still open as of 0.3.0** (most of it since done — see §2d): the learned-model
roadmap in §5; drums were template-driven with no ghost notes; the arp had one
figure per song; no per-section instrumentation plan beyond the layer map.

---

## 2d. Composition passes — 0.5.0 to 0.9.0

**Dates:** 2026-10-14 and 2026-10-15. Eight passes, each developed on a
branch, measured over twenty seeds with `tools/analyze.py` (levels by
rendering one part alone through libopenmpt), and reviewed by ear on a
comparison page (same seed, old against new, with the parts not under
review held identical) before merging. Every one was approved; two were
tuned by ear afterwards (arp levels, metallic hat).

| pass | what changed | metric | before | after |
|---|---|---|---|---|
| Arp figures (0.5.0) | eleven one-bar figures with accents, verse/chorus/bridge figures per song, climb on alternate bars, weak steps dropped under a busy lead, SNES 7th/9th colour | distinct arp figures per song | 49.5 (velocity jitter) | 6.3 (real recurrence) |
| | | arp velocity levels | 28.1 | 10.8 |
| Release envelopes (0.5.0) | sustain loop + decaying tail per family, note-off endings | audible tail after a note is let go | 0–20 ms | strings 460, brass 220, flute 120, organ 60 ms |
| Groove drums (0.5.0) | four-bar phrases (main, alt, lift), velocity tiers, ghosts on a rim, whole kit, fills by context, bridge drops | distinct bar patterns per song | 5.2 | 12.4 |
| | | bars repeating the previous | 60% | 12% |
| | | kick / snare velocity levels | 1 / 1 | 3 / 4 |
| Melody phrases (0.6.0) | four-bar sentences (statement, sequence, climax, cadence), chord tones on strong beats, leaps answered, register from energy, own random stream | chord tone on beats 1 and 3 | 61% | 77% |
| | | phrase-final note held (rows) | 5.0 | 7.4 |
| | | position of the highest note | 0.35 | 0.49 |
| Form (0.6.0) | section cadences with bass pickups, relative/subdominant key plan, two-bar harmonic rhythm | pattern joins resolving V→I | 18% | 33% |
| | | mean song length | 224 s | 173 s |
| Motif grammar (0.7.0) | motifs from cells (steps, neighbours, repeats, thirds, runs), leaps only to launch a phrase and answered by a step, tendency tones resolve, period and sentence forms, own random stream | stepwise intervals | 57% | 69% |
| | | leaps (5+ semitones) | 16% | 13% |
| Equal loudness (0.7.0) | sustaining voices normalised by loop RMS, struck voices on the arp by their first 150 ms; bass volume-column bug fixed | spread across the five SNES arp voices | 8.6 dB | 4.2 dB |
| | | SNES bell arp vs drums | −6.2 dB | −13.6 dB |
| Style packs (0.8.0) | ffvi, mana, evermore, megamanx: voices per role plus weighted habits; drone and riff bass, power chords, ostinato / pulse harmony, slap echo, sustaining-arp rule, struck-voice strike normalisation; Mega Man X designed from the game's SPC bank | arp vs melody, Mega Man X pulse arp | +4 to +6 dB | −1.6 to +0.3 dB |
| Packs from the banks (0.9.0) | every pack's voices profiled from its SPC snapshots and named by the community's tables and rips (FFVI 35, Mega Man X 23, Mana 25, Evermore 22 own voices; borrowing gone); echo per pack from the DSP registers (Evermore's turned mostly off); one SOUND picker; drawn intro templates; Mega Man X riffs, chugs, power chords; the rhythmic strum as a tick delay | FFVI horn-named synth lead, Evermore's wet echo, identical intros | n/a (voices, not levels) | n/a |
| SNES echo (0.7.0) | three fading, darkening taps sent per note from the lead, lighter sends from harmony and arp on returns of their own, per-song delay / feedback / wetness / stereo drawn from an own stream, section gain, 19 channels | lead notes sent | 100% | 70% |
| | | returns vs source (lead / harmony / arp) | −5 dB / none / none | −6 / −13 / −10 dB |
| | | all returns vs melody (six songs) | about −5 dB | −0.3 to −5.2 dB |
| Harmony rework (1.0.0, 2026-10-17) | two or three real voices (the J arpeggio retired), a voicing rule that keeps the chord's colour tone, stab length from the voice's measured attack with no volume slide, registers per family with the top voice under the lead's lower quartile, level per family measured through ebur128 and the harmony channels 25 → 9, hits under 200 ms written up, the counter-line on its own channel and level | harmony hits vs lead, momentary loudness 95th pct, eight songs | −5.5 to +5.5 dB | −4.4 to −12.2 dB |
| | | strings stab audible length (Strike of the Factory) | 260 ms (slide) | 736 ms (hold) |
| | | J-arpeggio notes across the set | 71 | 0 |

Two lessons from the reviews are worth more than any number:

- **Hold everything else still.** The melody draws from its own random
  stream, seeded from the pattern's content seed, so the parts after it do
  not move when it changes; the drum pass rendered its "old" side by
  degrading the new engine on the identical tune. Without that, an A/B
  compares two songs, not one change.
- **The comparison player must not lie.** Two `<audio>` elements kept in
  step by seeking the muted one re-buffered every half second and made the
  old side stutter through three reviews. Both clips now decode into
  buffers on one audio clock and the switch is a gain change.

**Still open after 0.9** (see `ROADMAP.md`): arp register motion beyond the
octave climb, chip chord stabs, per-section instrumentation, pad colour and
the learned-model items. The FFVI set became a pack (0.8.0, rebuilt from the
game's bank in 0.9.0); Metroid was dropped, Evermore covering its ground.
`--keys home` pins every section to the home key for loops and A/B tests.

---

## 2e. Toward 1.0.0 — the release listen

**Dates:** 2026-10-17 and 2026-10-18. After 0.9.1, every sound was heard
end to end on a release page, and what the listen turned up was mostly
engine-wide rather than per pack. Each finding was measured on the part
rendered alone before anything changed, the same way as §2d.

| fix | what was wrong | measured before | after |
|---|---|---|---|
| Note conversion | `midi_to_it_note` subtracted 12, believing IT's C-5 was MIDI 72; IT note 60 plays a sample at its C5Speed, where our samples carry middle C. Every tonal part sounded an octave below its label, and the registers had been tuned by ear around the error | label 60 played at 130.8 Hz; the harmony's lowest voice at 39-41 Hz in every sound, under the bass | label 60 at 261.6 Hz; bass medians 78-107 Hz, harmony 160-370 Hz, arp 270-340 Hz |
| Bass floor | bass windows set in label space without the pattern's octave shift; "deep and heavy" at 16 Hz, octave-bounce and driving styles a twelfth under that | a sixth to a half of bass notes under 33 Hz, down to 13 Hz (Northern Dawn's slap bass at 29 Hz, a blown speaker by ear) | windows in MIDI (heavy E1-D#2), a floor at E1 on every written bass note |
| Harmony mode and voice | a rhythmic harmony mode (chug, pulse, ostinato) could land on a slow-attack voice (strings, pad, choir) | 18 of 60 Mega Man X seeds; Northern Dawn: 264 of 266 chord notes shorter than the strings' 96 ms swell | none where the pool has a fast voice |
| Song length | a short form at speed, or a long form repeated at a slow tempo | 3 in 10 songs under 1:30 (43 s at worst), 2 in 10 over 3:00 (up to 6 min) | every song 75-210 s, the median unchanged at 2.1 min |
| Brass harmony | a lone harmony voice was always arpeggiated with the J effect; on bright brass that is a rasp, twelve times a second on Northern Dawn | brass harmony at 160 Hz alone (the games stab theirs at 250-580 Hz) | the J arpeggio only on pad, strings, choir and organ; brass a fifth higher and 3 dB under a pad |
| Lead register | the conversion fix raised the lead an octave while bass and harmony were re-derived downward; by ear, piercing | lead medians 523-640 Hz | placed once per song by `registers.py`: medians 415-480 Hz, the lead under the chord's top voice in 0-18% of rows |
| Harmony rework | see the §2d table | | |

The lesson of the week: **a constant error tuned around by ear hides
itself.** The octave offset had been there since the first version; every
register had been set to sound right on top of it, so nothing sounded
wrong until a part was measured in hertz against what the games play.

**Still open at 1.0.0** (`ROADMAP.md`): the loudness spread across songs
(7.6 dB, following the kit's hits per second times tempo), the melody's
register per pack by ear, the orchestra hit's use, the brass on Northern
Dawn ("manageable, still off"), and the next packs.

---

## 3. Tier 1 — design ceilings (as found on 2026-09-04)

Not bugs, but hard limits on how good the output can get. Items marked ✔ were
lifted by the commits of 2026-09-04 and the Tier 1 pass in §2c.

- ✔ **Rhythm is locked to an 8th-note grid.** All eight `RHYTHM_TEMPLATES` in
  `melody.py` use even offsets only; **0.3% of onsets land on an odd row**. No
  syncopation finer than an 8th, no triplets, no dotted rhythms, and no
  anticipations — pushing a note a 16th ahead of the beat is the single most
  effective "musical" device that is entirely absent.
- ✔ **Arp and bass never rest.** `bass.py` → `generate_arpeggio()` writes a note
  every 2 rows for all 64 rows regardless of style or section energy. 640 arp
  notes vs 167 melody notes: the arp is the densest thing in the mix and it never
  breathes. `generate_bass()` has the same unconditional-loop shape.
- ✔ **Tiny harmonic vocabulary.** 2–4 progressions per scale, all four chords long,
  all diatonic. `CHORD_INTERVALS` defines `7th`, `sus4`, `dim` and `aug` but
  `PROGRESSIONS` uses only `major`, `minor` and `power` — the others never reach
  output. No secondary dominants, borrowed chords, modal interchange, or pedal
  points. Game music leans heavily on ♭VI/♭VII and sus resolutions; none present.
- ✔ **3 IT effects out of ~30.** Only D (volume slide), G (portamento) and H
  (vibrato) reach the file. Missing the ones that define the idiom: **Jxy
  arpeggio** (the classic single-channel chord), **Qxy retrigger**, **SDx note
  delay** (flams, humanisation), Oxx sample offset, and panning. `FX_TREMOLO` is
  imported into `composer.py` and never used.
- ✔ **Dead code.** `theory.passing_chord()`, `theory.get_chord_for_degree()` and
  `theory.note_from_name()` have zero references.
- ✔ **Orphaned patterns.** `silence_inactive_channels()` deep-copies patterns and
  appends them, leaving the originals unreferenced in the order list — files
  carry more patterns than they play (26 patterns for 24 orders in seed 1).
- ✔ **No tests and no regression harness** before this document; nothing indicated
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
stretch survived nine commits and a full README write-up, and the octave
error of §2e every version until 1.0.

**One part alone.** Levels and pitches in §2c-2e come from rendering a single
part: in a copy of the file, set every other channel's volume in the header
to zero (byte `0x80` + channel), render through libopenmpt (the player's
`bitcomposer.player.openmpt` binding does it), and measure the result:
ffmpeg's `ebur128` for loudness, a pitch track for register. The
comparison pages used for the by-ear reviews live outside the repository.

---

## 5. Roadmap for smarter generation

Ordered by return on effort. The important claim is that **steps 1–2 must precede
step 3**: a learned model cannot fix a stretched drum grid or a chorus that never
repeats, because those are arrangement-layer facts, not note-choice facts.

1. ✔ **Fix Tier 0.** Cheap, deterministic, individually audible (§2b).
2. ✔ **Lift the Tier 1 ceilings** that are pure code: 16th-note rhythm templates and
   anticipations, arp/bass rests tied to section energy, extended chord types and
   secondary dominants, and the J/Q/SDx effect vocabulary (§2c, §2d).
3. **Corpus statistics — no neural net.** Train n-gram / Markov tables on real
   chiptune (NESMDB, ~5k NES songs already symbolic; or the Modland module
   archive). Learn chord-transition probabilities, melodic interval distributions
   conditioned on scale degree and chord tone, and real rhythm-template
   frequencies. A few hundred lines, trained offline, shipped as a JSON table —
   **this preserves the generator's zero-dependency property** (the player
   has Qt; the generator still needs nothing). Best
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
   3–4 and cheap. (Song titles no longer need it: `names.py` builds them
   from the song's scale, sound, energy and tempo.)
