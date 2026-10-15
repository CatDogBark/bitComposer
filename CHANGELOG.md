# Changelog

## 0.5.0 — 2026-10-14

Arrangement release: everything here was reviewed by ear on A/B comparison pages before merging.

- Drums rebuilt as grooves: four-bar phrases with an alternate bar and a lift, velocity tiers, ghost notes on a rim sample, open hat, toms and crashes in the grooves, a fill library sized by what comes next, bridge drop-outs, hats thinned above 140 BPM. Over 20 seeds: distinct bar patterns 5 to 12, repeated bars 60% to 12%, kick and snare velocity levels 1 to 3 and 4, open hat and toms from nothing to regular.
- Release envelopes: every sustained voice gets a sustain loop and a decaying tail, and notes end with note-off instead of a hard cut, so strings, pads, brass, leads and basses each die away at their family's pace.
- Arpeggios are figures: eleven one-bar shapes with accents and rests, a verse, chorus and bridge figure per song, climbing on alternate bars, thinning under a busy lead. SNES arps carry the chord's 7th or 9th from the scale.
- `docs/ROADMAP.md`.

## 0.4.0 — 2026-10-13

First public release.

- Genesis palette rebuilt around the YM2612's feedback FM: buzzy saw lead, cutting lead, brass, pad, bell, arp blip, slap and sub basses, plus 8-bit DAC-style drums at 11 kHz and an occasional PSG square. The old two-operator presets sounded like a filtered triangle at sustain, i.e. like the chip palette.
- Chip palette gets role-specific voices: pulse leads, triangle or 12.5% pulse harmony, decaying pulse and triangle plucks for arps at a duty different from the lead's.
- Console output polish for all waveform and FM presets (low-pass, attack, settled loop) — they were raw full-bandwidth single cycles with no envelope.
- Sustain pads hold then fade instead of dying mid-hold; echo tails spill into the next pattern; swing follows the hat subdivision; gated snare has a decaying room; metallic hat tamed.
- Per-palette channel mix (chip arp 28).

- Output files are named after the song title (`Haunted Orchard.it`); `--name timestamp` keeps the old scheme, `--suffix` adds a marker.
- `python3 -m bitcomposer` works; packaging installs only the library.
- Companion player: titles in the playlist, music-folder line, KEEP for auto-generated tracks, persisted settings, gain control up to 3x with soft limiting, ~100 ms audio latency, AUTO button fixed, presets renamed (GOTHIC, FM DRIVE, FIGHT THEME).
- Docs trimmed for a public audience; MIT throughout.

## 0.3.0 — 2026-10-13

- `--style snes`: 21 sampled-style voices rendered at 16 kHz with loop points through a BRR codec model; strings, brass, formant choir, flute, organ, e-piano, bell, marimba, pizzicato, harp, three basses, orchestra hit, gated drum kit. The old waveform set is `--style chip`.
- Lead echo on two channels (`--echo`); output is 14 channels.
- Chord timeline: the back two bars of a pattern can move to a related chord. Borrowed chords and secondary dominants in the progression tables; pentatonic scales get their own.
- 16th-note melody rhythm templates.
- Seed-derived song titles and a song message (key, BPM, palette, form, seed).
- Fixes: chorus modulation moved chords but not the melody's scale; intro fade-in made the intro louder; sustain harmony died in six rows; orphaned patterns; six-cent tuning error.
- 27 unit tests (`python3 -m unittest discover -s tests`).

## 0.2.0 — 2026-09-04

- Tier 0 fixes from the generation-quality analysis: drum grid was stretched 4x, repeated sections never shared music, harmony never moved.
- Tempo derived from BPM; arp and bass rest on section energy; per-bar melody motifs; role-based panning; J/Q/SDx effects; 7th and sus4 chords.
- `tools/analyze.py` regression harness and `docs/ANALYSIS.md`.
- Companion player vendored with an installer.

## 0.1.0 — 2026-03-11

- Initial release: procedural melody, harmony, bass, arpeggio and drums written straight to Impulse Tracker `.it` files with synthesized samples.
