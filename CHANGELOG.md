# Changelog

## Unreleased

- FFVI pack rebuilt from the game's sound chip. 82 SPC snapshots decoded (BRR), 71 unique samples profiled (steady harmonics, centroid, attack, decay, loop), every one matched to the game's documented instrument table by its exact BRR size, and traced to the voices that play it (sounding pitch, envelope, echo); every recipe targets a measured shape and names its instrument. The bank as it is: strings 1 in 54 of 82 banks (brighter than ours was, a strong fourth partial, a 180 ms swell); a dark synth lead in 28 (Locke, Returners, Cyan, the Prelude); flute 2 played in chords in 29; the trumpet, in chords as often as alone; the Battle theme's distortion guitar; trombone, oboe, pan flutes (Terra's and Cyan's), flute 1, cello, choir, the Opening's pipe organ, the Decisive Battle rock organ, the Aria's soprano; piano, harp (a dull pluck, the Prelude's arpeggio), picked string, acoustic guitar, tubular bell, xylophone; a looped bass guitar; and the kit (68 ms kick, 125 ms snare, hats, cymbal, 130 Hz timpani, wood block). The eight borrowed snes voices and the invented horn, clarinet, contrabass, music box and pizzicato are gone: 29 own voices. Echo as the snapshots have it: on in every song, the 80 ms slap favoured, feedback 0.55-0.7 (new pack habit `echo_feedback`), repeats under their source. Survey tools in `~/diags/bitcomposer/ffvi-spc/tools`; nothing from the game is copied.
- One SOUND picker: a sound is a palette (chip, genesis, snes) or a style pack (ffvi, mana, evermore, megamanx), the packs being snes narrowed to one score. `--sound` on the CLI, one combo in the Windows window and one row in the widget's COMPOSE tab replace the STYLE + PACK pair, where a pack chosen earlier silently overrode a preset's palette and a pack under genesis was accepted and then switched to snes without a word. `composer.resolve_sound` reduces any (style, pack, sound) to a consistent pair; `--style` and `--pack` still work. Left to chance, a song now draws its sound with the four packs together weighing as much as plain snes (before, each pack landed about one song in sixteen). Widget presets name a sound; a saved STYLE/PACK pair folds into SOUND once.
- Intro templates: the intro was the one section with nothing drawn in it (bass and a two-note pulse arp fading up over the whole home progression, in every song of every pack). A song now draws one of four openings (`structure.INTROS`: arp bed, riff vamp, drum pickup, pad + hook) and its length (four or eight bars) from its own stream, weighted by the pack (`intro` habit); each part enters on the bar the template says, the fade-in only where the opening swells, the arp figure is drawn, a riff keeps vamping instead of dropping to steady, and the pad opening states the hook over sustained harmony. Everything after the intro is byte-identical to before, except the handoff bar.
- Mega Man X variety: a library of seven one-bar bass riffs (`bass.RIFFS`, one drawn per song from its own stream, pack weights `riffs`), three chug harmony rhythms (`chug_sync`, `chug_offbeat`, `chug_gallop`), power chords only under the voices a pack names (the chug) with real chords under the pad and brass, brass stabs counting as contrast in the instrument picker, and the pack's draws rebalanced (major keys and medium tempo up, the guitar lead down, eighth and dotted echoes back). Over sixty seeds the harmony now draws eight modes instead of four dominated by two, the bass four styles and seven riffs instead of one.
- Layout: `samples.py` is a package (`dsp`, `chip`, `snes`, `genesis`, the registry), each style pack is one module under `bitcomposer/packs/` holding its voices and habits, and `composer.py` is split into `builder`, `instruments`, `echo` and `mix`; the tests are one module per area. Mechanical moves only: twenty baseline songs across palettes and packs are byte-identical before and after.
- Palette pass: the ensemble chorus (FFVI strings and contrabass, Mana glass pad, Evermore pads and drone, Mega Man X lead guitar) no longer combs; the dry tone leads at 80% with the two detuned copies at different offsets, so the fundamental's share of power swings by under 15 points across the loop instead of 60-90. The flute, whistle, pan flute and horn gain a little second and third partial.
- Level: the module's mix volume is written at 128 (was 80) and every channel volume carries a master gain of 1.25, taking files from about −27 LUFS to about −20 with true peaks a decibel clear of full scale; balance and dynamics unchanged.
- Windows: `bitComposer.exe` (a tkinter window: palette, pack, echo, energy, tempo, count, folder, Generate) and `bitcomposer-cli.exe` (the CLI), built single-file by a GitHub Actions Windows job and attached to each release as `bitComposer-windows.zip`; `bitcomposer-gui` console script; pyproject version synced to 0.8.0.
- Pack voices: the packs' lead, harmony and bass pools hold only their own voices, with borrowing kept where it is the game's sound (FFVI flute and choir, Mana flute and mallets, Evermore flute and strings); Mega Man X borrows nothing. The instrument picker gains a contrast rule for every palette: when lead, harmony and arp all sustain and the harmony is not a pad, the harmony is redrawn as a struck or pad voice (over 200 draws, no all-sustaining trio remains). `samples.STRUCK_PRESETS` records the classifier's verdict per preset so the picker can ask without rendering.

## 0.8.0 — 2026-10-15

Style packs: an instrument set paired with the arrangement habits of the scores it imitates. Four packs, each reviewed by ear against plain snes on comparison pages, plus the engine pieces they needed and the fixes the reviews turned up.

- Style pack `megamanx` (Mega Man X), designed from the game's own SPC sample bank: a driven, chorused lead guitar, a chugging rhythm guitar, a dry pulse synth, synth brass, a string pad, a soft lead, a snapping synth bass and a tight kit, all synthesised to the measured shapes; habits: fast tempos, intense energy, minor keys, stab and rhythmic harmony on power chords (new habit `power_chords`: root, fifth, octave), a new `riff` bass style (a one-bar root / octave / fifth riff), busy drums, no swing, broken-octave and gallop arps, a pulse-synth counter-line half the time, and the game's echo: a new `slap` delay (48 ms, written as a tick delay under a row) with bounce stereo.
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
