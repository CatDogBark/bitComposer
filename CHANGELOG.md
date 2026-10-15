# Changelog

## Unreleased

- Style pack `evermore` (Secret of Evermore): warm and dark ensemble pads, a drone, a breathy flute, an "oo" choir, tubular bells, frame drum, brushed snare and a soft click; habits: slow tempos, chill energy, minor keys, linear forms, sustained harmony, a new `drone` bass style (one held note per chord, sliding between roots), sparse drums with a 40% chance of no kit at all (new pack habit `drumless`), wet centred echo on a quarter or dotted-eighth delay (packs can now weight `echo_delay` and the song form).
- Style pack `mana` (Secret of Mana): celesta, kalimba, steel drum, wind chimes, whistle, pan flute, a glassy chorused pad, and a hand-percussion kit (conga on the tom slot, shaker as the hat, tambourine as the open hat, woodblock as the rim); habits: major and pentatonic keys, pulse / rhythmic / stab harmony, octave and walking bass, light swing, bouncy arp figures (packs can now weight `arp.FIGURES`), kick and snare trimmed back.
- Arp echo: only the arp's accented steps are sent, and the arp send tapers with tempo (full to 130 BPM, gone by 170), so a fast pizzicato arp no longer turns into a stream of ticks between the plucks.
- Echo stereo: the "spread" mode (every repeat hard on the far side of its part) is replaced by "centre" (repeats under their source). A copy arriving a quarter second late from another direction was heard as a second player coming in late rather than as a room.
- Style packs (`--pack`, `bitcomposer/packs.py`): an instrument set paired with the arrangement habits of the scores it imitates. First pack `ffvi`: string section with ensemble beating (a long loop carrying sharp and flat copies that beat at 1.6 Hz), horn, trumpet, oboe, clarinet, piano, music box, pipe organ, bowed basses, and an orchestral kit (timpani on the tom slot, bass drum, orchestral snare, suspended cymbal); habits: ostinato (3+3+2) and pulse harmony modes, a horn counter-line in 60% of chorus and bridge patterns, timpani rolls into choruses, slower tempos, no swing, hats trimmed, a wetter and wider echo. Half of snes songs draw a pack when `--pack random`; the song message names it. Widget: PACK picker in the COMPOSE tab.

## 0.7.0 — 2026-10-15

Echo release: the SNES echo rebuilt in three stages, each reviewed by ear on a comparison page, plus the arp loudness fix and the motif grammar. Modules are now 19 channels; the companion player's mixer follows the file's layout.

- SNES echo, stage three: each song draws its own echo from a dedicated stream, so the arrangement never moves when the options change: delay as a beat fraction weighted by tempo (eighth, dotted eighth, quarter), feedback 0.3–0.6, wetness (light / normal / wet), and a stereo mode where repeats bounce between sides or spread wide on the far side of the part (pan per tap via an Xxx effect). Sends open in intros, bridges and outros and pull back in the chorus. `--echo-delay`, `--echo-stereo`; the settings are written into the song message.
- SNES echo, stage two: the harmony and arp are sent too, at their own levels (0.3 and 0.35 of the part against the lead's ½), on return channels of their own; the module is 19 channels and its song message carries a `layout:` line naming every channel's role. Returns carry the source's fades so a stab's echo decays like the stab. `--echo-wet light|normal|wet` scales every send. Companion: the daemon answers `GetLayout`, the widget's mixer builds its faders from it, folds every return into one ECHO bus fader (expand for LEAD / HARM / ARP) scaled against the written mix, and the COMPOSE tab gains ECHO and WET pickers.
- Arp loudness: a struck voice on the arp (bell, e-piano, marimba, pizz, harp, chip and genesis plucks) is normalised on its first 150 ms, so every arp voice hits at the same level; the SNES bell arp comes down 7 dB and the spread across SNES arp voices goes from 8.6 dB to 4.2 dB. Lead, harmony and bass samples are unchanged. The per-palette arp trims are gone; only the genesis PSG square keeps one.
- SNES echo, stage one: three repeats on a dotted eighth, each half the last and darker through a lowpass (separate two-pole 4, 2 and 1 kHz copies of the lead sample), ending where the source note ends; only held notes and phrase endings are sent, so fast runs stay dry. Measured over 20 seeds: 70% of lead notes sent, echo channels 2 dB lower against the melody than before.
- Echo by palette: left to chance, 70% of snes songs get the lead echo and chip and genesis never do (neither the NES nor the YM2612 had an echo unit); `--echo on` still forces it anywhere.
- Motif grammar: motifs are built from cells (steps, neighbours, repeats, thirds, short runs) with a leap allowed only to launch a phrase and always answered by a step; tension tones resolve; the rhythm is held as the phrase's identity; half of phrases take the period form (cell, answer, cell again, closed answer). Motifs draw from their own random stream. Over 20 seeds: stepwise intervals 57% to 69%, leaps 16% to 13%, bars keeping the previous bar's rhythm 27% to 35%.

## 0.6.0 — 2026-10-14

Composition release: the melody and form passes, each reviewed by ear on a comparison page before merging.

- `--keys home` pins every section to the home key, for loops that must sit still or for A/B tests of other changes.

- Form pass: every section ends on a cadence, the last two bars moving to the dominant of what follows with the bass walking up into it (pattern joins resolving V to I: 18% to 33% over 20 seeds); choruses and bridges move to the relative key or the subdominant instead of the old one-semitone lift; a two-bar harmonic rhythm (two chords per pattern, eight-bar sections) on some songs, more often at fast tempo.
- Melody phrase engine: each pattern is a four-bar sentence (statement, sequence a step up, development carrying the climax, cadence on a held note), chord tones on strong beats, leaps answered by steps, question phrases ending off the root and answers on it, register driven by section energy so choruses lift. Over 20 seeds: chord tone on strong beats 61% to 77%, held phrase endings 5 to 7.4 rows, climax position 0.35 to 0.49.
- The melody and counter-melody draw from their own random stream, so melody changes no longer shift the rest of the arrangement.

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
