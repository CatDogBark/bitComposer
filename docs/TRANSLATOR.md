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
- The generator writes in voices (stage 3), as many as the arrangement is
  best with (2026-10-20): off the hardware, the SNES chip's eight are not a
  rule for generated songs. Songs converted from SPC files keep the game's
  voices one to one, and with them its sound.
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

Where it stands (2026-10-19): read, kept and printed by
`python -m bitcomposer.translate`, all 1836 songs of the 39 games in under
a minute from their played notes. Checked by ear, on 21 games, not FFVI
alone:

- The beat and bar, tapped on 43 songs: of the 41 the listener was sure
  of, 40 read as heard (a clean double or half agreeing where the listener
  did not tell them apart); the other is read from its notes, which the
  taps drifted from. A grid holds most songs; a loose beat (an onset envelope and
  dynamic-programming beats) those no grid holds, a swing off the
  triplet or notes placed by hand.
- Form, marked on 24 songs of 18 games (twelve of them twice, the second
  time at the scale of sections): the loop is read as heard in 22 of 23; of the part
  starts marked, 73 % to 86 % are read, and of those read, 56 % to 85 %
  were marked (parts and sections both kept).
- Known gaps: a grid section restarting where its timing slipped can
  leave a half bar (Fourside); a tune that comes back re-arranged is read
  as new; a long stretch of new material may stay one part; a loose song's
  loop (Snakey Chantey) is missed; keys and the counter-line role are
  rough, and are to be checked as stage 2 needs them.

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

Where it stands (2026-10-19): `python -m bitcomposer.spc --pack OUT
FOLDER` makes FFVI's pack from its 82 songs in about a minute: 22 samples
(six a part at most, and a kit of kick, hi-hat and snare) and the habits
above, with how often a song has no drums (`drumless`, 0.37), which the
readings give as straight. `python -m bitcomposer.translate FOLDER
--against PACK` measures songs composed with a pack beside the songs read
(`translate/measures.py`, the yardsticks from notes): 20 from each pack
against the 69 FFVI songs read on a beat, medians:

| | FFVI | hand-made `ffvi` | imported |
|---|---|---|---|
| tempo (BPM) | 85 | 123 | 96 |
| an arp | in 5 songs of 69 | in every song | in every song |
| drum hits a bar | 3.6 (none in 22 songs) | 10.7 | 9.4 |
| onsets off the eighths | 30 % | 7 % | 5 % |
| of them, on a triplet | 19 % | 0 | 0 |
| pitch classes a beat under the melody | 3.5 | 2.6 | 2.1 |
| melody bars heard before | 29 % | 54 % | 44 % |
| the melody's range (semitones) | 13 | 10 | 9 |
| length, once through (s) | 70 | 129 | 160 |

The pack moves what a pack can say toward the game (the tempo, songs
without drums, the game's own sound); the rest is the generator's own
writing, the same under either pack: an arp in every song, no triplets,
few notes off the eighths, thinner chords, tunes that repeat more and
range less. That is stages 3 and 4, as planned, not more habits. The
harmony moves less under the imported pack (0.16 notes a beat a voice,
against 0.88 and FFVI's 0.98): the hand-made pack draws its harmony
modes, and the imported one has none to draw (no classifier for them, as
above). What the readings contradict in the hand-made pack is in the
packs table of `drivers/snes/README.md`. Listened (2026-10-20): decent
for a thin pack, the game's sound in it; the arrangement is where the
gap is, which is stages 3 and 4. Saving each import's readings in the
database waits for them.

## Stage 3: the generator writes voices

One way of writing music for both directions: the translator reads voices,
the generator writes them, and one back end makes the module.

- **A score of voices.** The generator's parts (melody, harmony, bass, arp,
  counter-line, drums) given to voices, each note the decoder's kind: a
  sample, a pitch, volumes, an envelope (ADSR or GAIN), whether it sends to
  the echo. How many voices is the arrangement's, not the hardware's: a
  generated song is not held to the SNES chip's eight (a drum kit can take
  a voice a sound, a chord a voice a tone), while a converted song keeps
  the game's own voices. The cost to weigh is IT's 64 channels: every
  voice is a channel, and the echo's repeats share what is left (six
  voices sending get about nine repeats each; sixteen about three).
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
user's data folder.

Where it stands (2026-10-20): the player's PACKS tile opens it
(`packs/library.py` under it). IMPORT reads a game's SPC files, from its
set (a zip; an .rsn, .rar or .7z unpacked by 7-Zip or unar, found on the
machine, never shipped: `translate/archives.py`) or from its folder (that
folder's own), in a process of its own, the songs read shown as they go; ADD brings in an exported
pack (one zip file) or a pack file; each pack has USE (it joins SOUND),
its voices by part, the kit and what is left out (a click plays a voice
in its part's register and says which parts the readings found it in,
in how many songs, how many notes; MOVE TO puts it elsewhere), RENAME,
EXPORT and DELETE. Importing a game again starts it fresh; to keep your
changes, export the pack first. IMPORT needs the emulator, and says so
without it: the Windows build carries it, and on a pipx install GET THE
EMULATOR adds it (`bitcomposer[import]`, from PyPI), which UPDATE then
keeps current. On Windows the executable runs IMPORT's worker itself.

## Later

Packs by composer or driver (queries over the database); Genesis, through
VGM logs, into the same translator; MPTM output for timing finer than
IT's ticks.

## To settle as we go

- **Where the database lives**: settled (2026-10-20): the user's data
  folder, with the packs (`~/.local/share/bitcomposer`, or
  `BITCOMPOSER_DATA_DIR`).
- **Tuning to taste**: settled (2026-10-20): only in the pack. Importing
  again starts fresh; EXPORT keeps a pack as it is, ADD brings it back.
