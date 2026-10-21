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

Where it stands (2026-10-20): the harmony half of "from the readings",
counted. `python -m bitcomposer.translate.vocab --db PATH`
(`translate/vocab.py`) prints two tables over a database's songs: how one
chord moves to the next, as Roman numerals in the song's key with the
chord's shape kept (I -> IV, ii7 -> V7, bVII -> I), counted once and in
the beats the chord moved to is held, by mode (the numerals mean
different degrees in major and minor), with the moves by degree alone
under each; and the voicings over the chord spans: which of the chord's
tones the bass, harmony, accompaniment and arp sound, the spread, the
lowest note's tone (the inversion), which tone each part holds (the
melody and counter-line too) and where the melody sits. Each song counts
once through, to its loop, from the spans that fit (0.6: fewer than half
a triad's tones sounding reads under it); a pitch sounds in a span when
its notes cover a quarter of it, a struck note heard for an eighth at
least (FFVI's accompaniment keys off in a fifth of a beat). Songs in free
time, with no key, or mostly silent or unfit are left out. FFVI:

| | FFVI |
|---|---|
| songs counted | 67 of 82 (13 in free time, 2 mostly silent) |
| chord spans, once through | 3929 (2100 of them a beat long) |
| moves, major keys / minor keys | 1308 in 26 songs / 2465 in 41 |
| distinct moves, shape kept | 620 / 963 (the most counted, IV -> I, 2 %) |
| moves by degree alone | IV -> I 7 % / 5 %, I -> IV 6 % / 5 %, V -> I 3 % / 3 % |
| moves to the same root's other shape | 14 % / 11 % |
| chords held most, major | I, IV, vi, I5, iii, V |
| minor | i, I5, VI, VII, iv, IV5, III |
| the chord's tones sounding | root, third and fifth 29 %; root and fifth 19 %; the root alone 7 % |
| the lowest note | the root 44 %, the fifth 23 %, the third 14 %, a sus tone 4 %, the seventh 7 %, none of the chord's 8 % |
| pitches sounding a span | 4 [2-5] |
| spread without the bass (semitones) | 12 [4-27] |
| the bass on the root / fifth / third | 53 % / 19 % / 12 % of its beats |
| the melody on a chord tone | 65 % of its beats (the fifth 25, the root 22, the third 18) |
| the melody above the chord's top (semitones) | 1 [-11-11] |

What they say: FFVI's harmony moves between I and IV and to the relative
minor far more than from V to I, in both modes, and its minor is the
natural minor's (VI and VII major, v as often as V): modal, not the
harmonic minor's cadences. Its chords are open: a bare fifth or a root
alone in a quarter of the spans (the 1576 "5" shapes of stage 1), the
bass on the root half its time and on the fifth a fifth of it, the upper
parts within an octave at the median. The moves with the shape kept are
spread thin (the top at 2 %): the chord reader changes chord every beat
over half the time, so passing chords are moves too, and the habit shows
by degree alone; a vocabulary would draw the degree moves and the shapes
apart. What looks wrong: the bass is read octaves low in 29 songs (its
median pitch at MIDI 20 to 29; Dancing Mad's parts at 2, 3 and -19: a
sample's tuning read at a sub-harmonic), so the spread with the bass (31
semitones) and the melody above the bass (34) are not to be believed;
moves to the same root's other shape (I -> I5 -> I) are a held chord
split when its third drops out, not harmony; VII -> biiidim and I -> i in
major are the key or chord reading; and the melody sits at the chord's
top, inside it a quarter of the time, because the accompaniment and
counter-line are read as high as it. Rhythm, melody and drum patterns are
the next slice.

Where it stands (2026-10-20), the rhythm half: `python -m
bitcomposer.translate.rhythm --db PATH` (`translate/rhythm.py`) prints
three tables over the same songs, once through. Each part's rhythms bar by
bar: its voices' onsets together (a chord struck in three voices is one
onset) on the song's grid, drawn four characters a beat, counted per meter
with the share of the part's bars each covers and the songs it is heard
in; with them, how dense each part plays and where its onsets fall (on the
beat, an eighth, a sixteenth, a triplet, finer). The bass's figures, its
rhythm with each note's chord tone in its place (the chord from the chords
table), and the drums', which sound plays where: the readings keep a hit's
sample, not what it is, so a sound is named by how the game plays it over
all its songs (six hits a bar or more where it plays, the hat; of the rest,
landing on the bar's first beat more than on its backbeats, the kick, the
other way the snare), and the sounds are listed with their profiles. The
melody's moves from note to note by size and direction, and its notes'
lengths, the time to the next note on the song's grid. Only bars of the
song's meter count: a bar of another length is a grid section restarting
where its timing slipped (stage 1's known gap). FFVI:

| | FFVI |
|---|---|
| songs counted | 67 of 82, the harmony's; 1824 bars of 2343 (519 of another length than the song's meter, 211 of them in Dancing Mad's three readings) |
| meters | four beats in 63 songs, three in 4 |
| onsets a bar | bass 4.4, accompaniment 7.5, arp 10.5, counter-line 4.6, melody 3.9, drums 8.0, held harmony 0.9 |
| off the eighths / of those on a triplet | bass 25 % / 42 %, accompaniment 35 / 29, counter-line 26 / 46, melody 23 / 28, drums 41 / 31 |
| as stage 2 counts them (the median song) | 28.7 % / 20.8 % (stage 2: 30 / 19) |
| the bass's bars (301 patterns) | a whole note 13 % (31 songs), rest 13 %, four quarters 5 %, eighths 5 %, two halves 3 %; the 8 patterns heard in five songs or more cover 41 % of its bars |
| the accompaniment's | eighths 16 % (18 songs), sixteenths 8 %, quarters 6 %, rest 7 %, a whole note 4 % |
| the melody's | rest 21 % (45 songs), a whole note 8 %, quarters 5 %, eighths 4 %; 26 patterns in five songs or more cover 59 % |
| the harmony's / the drums' | a whole note 50 % / sixteenths 10 %, rest 14 % |
| bass figures | the root held a bar 10 % (25 songs), the fifth held 2 %, the third held 1 %, root eighths 2 %; a root an octave up in 20 % of bars, a non-chord tone in 21 %; the bass moves: a repeat 43 %, a step 23 %, a fourth 11 %, a third 8 %, a fifth 5 %, an octave 2 % |
| drum sounds (32 samples) | 6 hats (six to twelve hits a bar; the most used in 19 songs), 10 kicks (one 4.1 a bar in 14 songs, one 1.6 a bar and two beats long in 21), 13 snares (one 2.8 a bar in 12 songs, 54 % of its hits on the off-eighths), 3 others |
| drum figures (302 in the bars of four) | rest 13 %; a kick alone on the downbeat 3 % (11 songs); every other figure in one to three songs |
| melody moves (8874 notes) | a step 57 %, a third 19 %, a repeat 8 %, a fourth 7 %, a fifth or more 8 %; up and down alike |
| melody lengths | an eighth 33 %, a sixteenth 31 %, a beat 14 %, a triplet eighth 8 %, two beats 4 %, longer 6 %; the note sounds for 0.87 of it, a quarter detached |

What they say: FFVI's rhythm is written in plain values. The bass holds
the root for a bar, or walks it in quarters and eighths, an octave up in a
fifth of its bars; the accompaniment keeps eighths or sixteenths; the
melody moves by step in eighths and sixteenths, up as often as down,
sounding most of each note; the held harmony is whole notes. What falls off
the eighths is mostly sixteenths, and the bass's and counter-line's
triplets are the songs in twelve-eight. The drums are thin: a hat keeping
time, a kick on the downbeat the one figure many songs share, the rest
each song's own. The patterns are spread thin as the chord moves were (the
top rows of each table are one song's ostinato, which the songs column
shows), so a vocabulary would weigh patterns by the songs they are heard
in, not the bars. Against stage 2: the same songs give 30 % and 19 % their
way, so the counts agree; the difference is notes at no volume, which
stage 2 counts, and a song with nothing off the eighths, which it counts as
none on a triplet. The melody's steps agree with stage 2's 58 %. Stage 2's
3.6 drum hits a bar counts every bar of every song, with the 22 without
drums; here it is 8.0 onsets a bar in the bars of the songs that have
them. What looks wrong: in 11 of the 19 songs with a snare it lands between
the beats more often than on them (Battle Theme, Fanfare, Techno de
Chocobo, The Decisive Battle, Blackjack among them), with the bass and the
melody on the beat as often as off: the backbeat written on the off-eighth,
or the beat read half a beat off its phase, or at half the felt tempo (The
Decisive Battle at 104, Blackjack at 72); to be checked by ear before drum
figures are drawn from, since a bar read at twice its length also turns
eighths into sixteenths, and a third to a half of the hats' hits fall on
sixteenths or finer. A fifth of the bars are of another length than the
song's meter, the grid restarting at section joins, worst in Dancing Mad
(211 of its 275 bars), which also spreads the patterns thin. The melody
rests in a fifth of its bars, and in 14 songs in a third or more: the tune
passes to a voice read as counter-line or accompaniment, so the melody's
counts are its one voice's. The bass's chord tones and moves, and which
voice is the bass, wait on the bass fix: the waltzes' basses read at MIDI
24 to 27, and the bass sits on a non-chord tone in a fifth of its bars,
more than passing notes explain if its pitch is off by other than octaves.

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
