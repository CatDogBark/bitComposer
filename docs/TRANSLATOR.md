# The translator: a plan in stages

Agreed 2026-10-19. Step 4 of `SPC-IMPORT.md`, in detail:
from a game's SPC files to a pack the generator composes with.

## Where it starts

- **Notes, per voice.** The SNES chip decoder (`bitcomposer/spc/notes.py`)
  gives every note a voice, a sample, a pitch, volumes, an envelope and its
  echo. The converter plays them back within 0.45 dB of the emulator at the
  median, over 1836 songs (`drivers/`).
- **What drivers do.** `tools/spc_check.py traits` measures clocks,
  envelopes, echo and density. Each song's conversion is scored too, which
  says how far its notes can be trusted.
- **What a pack can say.** The pack format (`PACKS.md`): a palette, voices
  per role, and habits as weighted draws from the generator's own
  vocabulary (tempo slow/medium/fast, harmony mode stabs/sustain/chugs,
  bass style steady/walking/riff, arp figures, drum density, echo).
- **How the generator writes.** Sample mode, a fixed channel for each role,
  an echo of its own (repeats on beat fractions, darkened copies), envelopes
  baked into the samples. The converter writes the other way: instrument
  mode, a channel per SNES voice, the SNES chip's own echo and envelopes.
- **How generation is judged.** `tools/analyze.py` reads the generator's
  modules by its channel layout (`ANALYSIS.md`).

## Decided (2026-10-19)

- One pack per game; packs by composer or driver later, from the database.
- The readings go in a SQLite database (Python's own `sqlite3`, no new
  dependency) on the user's machine, never in the repository: a game's
  notes are its music and its samples are its files. The repository holds
  the schema and the code; `drivers/` stays the record of aggregates.
- The command line first; the player's PACKS panel after.
- What the translator measures does not depend on the generator's
  vocabulary: readings are the music as played (notes on beats, chords,
  roles, form), so any vocabulary can be made from them.
- The first pack is thin, in today's format, to run the whole chain; the
  vocabulary is then made anew from what the readings show, and that is
  the plan's main work (stage 4), not guessed before the readings exist.
- The generator writes in voices (stage 3), as many as a setting says:
  eight for the SNES palette, as the hardware had, more possible later.
- A new vocabulary serves imported packs first; the built-in packs sound
  as they do until moving them over is chosen.
- Final Fantasy VI first, checked against the hand-made `ffvi` pack.

## Stage 1: readings

A song's music, measured and stored, read from its decoded notes.

- **The store.** A new package, `bitcomposer/translate/`, with the
  database: songs (snapshot hash, game, composer, driver, length, clock,
  conversion score), samples (by their BRR data's hash, the WAV on disk),
  voices and their roles, notes (start and length in beats, pitch, volume,
  sample, envelope; one compact block per voice) and features (a song, a
  measure, its value, and whose: the soundtrack's or the generator's). Keyed
  by the snapshot and the translator's version, so only what changed is
  read again.
- **Beat and bar.** The tempo from note onsets on the driver's clock (the
  beat from their periodicity, weighted by accent: the drums, the bass);
  the bar and its downbeat from repetition; swing from long-short offsets.
- **Pitch.** Notes named from each sample's measured tuning, the game's own
  offset taken out (FFVI's instruments sit 8 cents flat together).
- **Harmony.** Chords from the notes sounding together on each beat; key
  and mode per section.
- **Roles.** Per voice and section, as the plan has them: drums (fixed-pitch
  or noise, on the grid), bass (the lowest sustained line), melody (the most
  varied, phrase-shaped line on top), harmony (what sounds under it), arp
  (fast repeated chord tones), counter-line. Each guess keeps its evidence,
  and a correction overrides it.
- **Form.** Repeated material, from the notes' self-similarity: the intro,
  the sections, the loop.

Check: a report per song from the command line (tempo, key, chords by
section, roles, form) for a dozen FFVI songs, read against what is heard;
songs whose conversion scores badly are marked and kept out of packs.

## Stage 2: a thin first pack

The whole chain, run once: the game's samples as voices, and only the
habits the readings give directly, in today's format. No classifiers built
for categories the plan is to outgrow.

- **Voices.** For each role, the samples the game uses most for it, written
  as WAVs (the loop kept, the SNES chip's interpolation in them, the pitch
  from the sample's tuning), each with a release family from its envelope
  and a volume. Most of a game's sound is here.
- **Habits.** The ones that map straight across, counted over the game's
  songs: tempo, scale family, echo (delay, feedback, wetness, from what the
  driver sets).
- **Measures in common.** The yardsticks of `ANALYSIS.md` computed from
  notes rather than from the generator's channel layout, so one set of
  measures reads the soundtrack's readings and the generator's songs alike,
  into the same table.
- **The command.** A folder of a game's SPC files in, `pack.json` and its
  WAVs out (`python -m bitcomposer.spc --pack DIR OUT`); `bitcomposer
  --pack-file` plays it as any pack file.

Check: songs from the imported FFVI pack and from the hand-made one, both
measured against FFVI's own songs, and listened to.

## Stage 3: the generator writes voices

One way of writing music for both directions: the translator reads voices,
the generator writes them, and one back end makes the module.

- **A score of voices.** The generator's parts (melody, harmony, bass, arp,
  counter-line, drums) given to voices, each note the decoder's kind: a
  sample, a pitch, volumes, an envelope (ADSR or GAIN), whether it sends to
  the echo. How many voices is a setting: eight for the SNES palette, as
  the hardware had, so an arrangement fits it the way a game's had to.
  More is possible later at a cost: every voice is a channel, and IT's 64
  leave the echo's repeats fewer to share (six voices sending get about
  nine repeats each; sixteen about three).
- **One back end.** The converter's stages after decoding (samples,
  instruments, the echo plan and its copies, the notes' placement, the
  master volume) take a generated score the way they take a decoded one.
  The echo becomes the SNES chip's own: a delay, a feedback, a filter, a
  send per voice.
- **Scope.** The SNES palette and SNES packs, built-in and imported. The
  chip and Genesis palettes keep their own path.

Check: chip and Genesis songs byte for byte the same; SNES songs change by
design, so the yardsticks before and after, the time a song takes, and a
listen before it ships. It changes how the built-in packs sound: a release
of its own.

## Stage 4: the vocabulary, made anew

The plan's main work: what a pack can say, designed from what the readings
show composers doing, and the generator taught to play it. Imported packs
use it first; the built-in packs move over only when chosen.

- **From the readings.** Chord voicings (which tones, how spread, which
  inversion, which voice takes which tone), how one chord moves to the
  next, progressions by section, rhythms per role and bar, the melody's
  intervals and phrase shapes, bass and drum patterns as played.
- **The pack format's second version.** Those tables as data, weighted
  (`bitcomposer_pack: 2`); the first version still read.
- **The generator.** Draws from them where a pack has them, its own rules
  elsewhere.

Check: the same distributions measured in generated songs against the
soundtrack's; the FFVI comparison again; listening.

## Stage 5: the player's PACKS panel

As `SPC-IMPORT.md` step 6: import a folder (progress while each song is
emulated), the role picker (hear each sample, see the translator's guess
and why, change it), USE, delete. The packs and the database in the
user's settings folder.

## Later

Packs by composer or driver (queries over the database); Genesis, through
VGM logs, into the same translator; MPTM output for timing finer than
IT's ticks; the emulator's wheels on PyPI, so others can import without
building it.

## To settle as we go

- **Where the database lives**: the settings folder (with the packs) or the
  user's data folder.
- **Tuning to taste**: a user's corrections (roles, voices, habits) kept in
  the database, so a pack can be made again from them, or only in the pack.
