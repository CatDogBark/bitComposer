# The translator: a plan in stages

Agreed 2026-10-19. Step 4 of `SPC-IMPORT.md`, in detail:
from a game's SPC files to a pack the generator composes with.

What follows stage 4, the generator learning to write from the readings,
is planned in phases in `IDIOM.md` (agreed 2026-10-20), which takes over
from stage 3's second half and stage 4's; the stages below stand as the
record of what was built and found.

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
  offset taken out (FFVI's instruments sit 8 cents flat together). The
  tuning is the sample's cycle (`spc/tuning.py`): a loop holding whole
  cycles pins it down, but a cycle is rarely a whole number of samples, so
  the shortest whole-sample lag the loop repeats at is followed down to the
  fraction of it the wave repeats at (fixed 2026-10-20: FFVI's bass loops
  hold 28 cycles of 169.14 samples and read at every 1184, seven cycles;
  four of its samples read 5 to 17 times low, their notes named wrong, and
  its most played bass an octave low). A one-shot is measured 50 ms in,
  or further along a long one where two later places agree and each
  repeats better (a struck tone's pitch falls through its attack), and a
  shorter period is judged on the wave smoothed to its low harmonics, the
  ones a pitch is heard by. Over the 39 games, 103 of 1736 samples moved,
  all but one by a whole ratio (28 by octaves, 71 by 3 to 71), and the
  songs whose bass's median pitch sat under MIDI 30 fell from 434 to 235
  of 1500.
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
  Considered (2026-10-20), not chosen: OpenMPT's MPTM format, should
  generated songs outgrow IT. It holds 127 channels (sixteen voices
  sending would get about seven repeats each), more samples and a finer
  tempo, but plays only where libopenmpt does (the player and the web
  player do), where an IT file plays nearly everywhere. So the score of
  voices does not assume a format: once this stage writes real
  arrangements, the channels they need with their echo are counted, IT
  stays the default, and MPTM is only for a song that does not fit, if
  any.
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
| chord spans, once through | 3926 (2096 of them a beat long) |
| moves, major keys / minor keys | 1272 in 25 songs / 2495 in 42 |
| distinct moves, shape kept | 600 / 899 (the most counted, IV -> I, 2 %) |
| moves by degree alone | IV -> I 6 % / 6 %, I -> IV 5 % / 5 %, V -> I 3 % / 4 % |
| moves to the same root's other shape | 14 % / 12 % |
| chords held most, major | I, IV, I5, vi, iii, V |
| minor | i, I5, VI, VII, iv, IV5, III |
| the chord's tones sounding | root, third and fifth 29 %; root and fifth 20 %; the root alone 8 % |
| the lowest note | the root 46 %, the fifth 23 %, the third 14 %, a sus tone 5 %, the seventh 8 %, none of the chord's 5 % |
| pitches sounding a span | 4 [2-5] |
| spread, the bass to the top / without the bass (semitones) | 28 [10-36] / 8 [3-19] |
| the bass on the root / fifth / third | 55 % / 22 % / 12 % of its beats |
| the bass's median pitch, over the 75 songs with one | MIDI 36 (E2; 11 songs under 30, the lowest 11) |
| the melody on a chord tone | 64 % of its beats (the fifth 25, the root 22, the third 17) |
| the melody above the lowest note / the chord's top (semitones) | 30 [19-38] / 2 [-10-11] |

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
apart. The first count (2026-10-20) had the bass octaves low in 38 songs
(its median pitch at MIDI 20 to 29, Dancing Mad's parts at 2, 3 and -19):
six samples' tuning read at a multiple of their cycle, two of them an
octave and four by 5 to 17 (the pitch bullet of stage 1). Read again, the
bass sits at E2, two samples moved an octave and four moved by more
(their notes' names with them: Mt. Koltz, Shadow, Mog, Strago, Dancing
Mad's third part and one unnamed track changed key, their chords with it,
and a sixth of the counted songs' chord beats moved, most in the songs
those samples carry); the sample that read 5 times low left the bass
part for the accompaniment, arp and melody it plays at MIDI 49 to 63; the
bass part moved to another voice in 11 songs, and in 14 a low string or
piano voice within three semitones of the bass joined it as a second
bass; the beat, bar and tempo of every song held. What still
looks wrong: a song's loop moved a bar in 7 songs, read from the notes'
self-similarity; moves to the same root's other shape (I -> I5 -> I) are
a held chord split when its third drops out, not harmony; VII -> biiidim
and I -> i in major are the key or chord reading; and the melody sits at
the chord's top, inside it a quarter of the time, because the
accompaniment and counter-line are read as high as it. Rhythm, melody
and drum patterns are the next slice.

Where it stands (2026-10-20), the rhythm half: `python -m
bitcomposer.translate.rhythm --db PATH` (`translate/rhythm/`) prints
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
where its timing slipped (stage 1's known gap). FFVI, counted after the
bass tuning fix of stage 1 (2026-10-20; what the fix moved is at the end):

| | FFVI |
|---|---|
| songs counted | 67 of 82, the harmony's; 1827 bars of 2348 (521 of another length than the song's meter, 227 of them in Dancing Mad's five readings) |
| meters | four beats in 63 songs, three in 4 |
| onsets a bar | bass 4.5, accompaniment 7.1, arp 10.6, counter-line 4.6, melody 3.9, drums 8.0, held harmony 0.8 |
| off the eighths / of those on a triplet | bass 23 % / 47 %, accompaniment 36 / 30, counter-line 25 / 46, melody 24 / 33, drums 41 / 31 |
| as stage 2 counts them (the median song) | 28.7 % / 20.8 % (stage 2: 30 / 19) |
| the bass's bars (307 patterns) | a whole note 12 % (28 songs), rest 9 %, four quarters 8 %, eighths 7 %, two halves 2 %; the 10 patterns heard in five songs or more cover 36 % of its bars, the rest apart |
| the accompaniment's | eighths 14 % (16 songs), sixteenths 7 %, quarters 5 %, rest 9 %, a whole note 5 % |
| the melody's | rest 21 % (45 songs), a whole note 8 %, quarters 5 %, eighths 3 %; 24 patterns in five songs or more cover 36 %, the rest apart |
| the harmony's / the drums' | a whole note 50 % / sixteenths 10 %, rest 13 % |
| bass figures | the root held a bar 9 % (23 songs), the fifth held 1 %, the third held 1 %, root eighths 2 %; a root an octave up in 17 % of bars, a non-chord tone in 23 %; the bass moves: a repeat 40 %, a step 24 %, a fourth 10 %, a third 7 %, an octave 7 %, a fifth 4 % |
| drum sounds (32 samples) | 6 hats (six to twelve hits a bar; the most used in 19 songs), 10 kicks (one 4.1 a bar in 14 songs, one 1.6 a bar and two beats long in 21), 13 snares (one 2.8 a bar in 12 songs, 54 % of its hits on the off-eighths), 3 others |
| drum figures (294 in the bars of four) | rest 12 %; a kick alone on the downbeat 2 % (11 songs); every other figure in one to three songs |
| melody moves (8880 notes) | a step 57 %, a third 18 %, a repeat 9 %, a fourth 7 %, a fifth or more 8 %; up and down alike |
| melody lengths | an eighth 31 %, a sixteenth 32 %, a beat 14 %, a triplet eighth 8 %, two beats 4 %, longer 5 %; the note sounds for 0.86 of it, a quarter detached |

What they say: FFVI's rhythm is written in plain values. The bass holds
the root for a bar, or walks it in quarters and eighths, an octave up in a
sixth of its bars; the accompaniment keeps eighths or sixteenths; the
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
(227 of its 367 bars), which also spreads the patterns thin. The melody
rests in a fifth of its bars, and in 14 songs in a third or more: the tune
passes to a voice read as counter-line or accompaniment, so the melody's
counts are its one voice's. What the bass fix moved, against the first
count (the same day, before it): the bass's octave moves rose from 2 % to
7 % and its repeats fell from 43 % to 40 % (the samples read octaves low
had hidden the octave bass), its walks grew (four quarters 5 % to 8 %,
eighths 5 % to 7 %) and the whole note shrank (13 % to 12 %, 31 songs to
28); the bass on a non-chord tone stayed at 21 % to 23 % of its bars, so
that is the chord reading or passing tones, not the tuning; the melody's,
the drums' and the accompaniment's counts moved by a point or two, the
held harmony's onsets a bar from 0.9 to 0.8.

Where it stands (2026-10-20), the generator against FFVI: `python -m
bitcomposer.translate.against --db PATH --against ffvi --against
PACK.json` (`translate/against.py`) composes stage 2's songs (20 a pack,
seeds 1 to 20) and prints the harmony and rhythm tables with the game's
beside them, each table's rows the top ones of every column. A composed
song's parts are its channels' (the generator knows them; its drums come
named), its three harmony channels told apart as the reader tells a game's
voices (held chords, struck ones, an arp, a counter-line, by roles.py's
rules in their order, since the counter-line takes a harmony channel the
song does not record); its chords and key are read from its notes as
FFVI's are, not taken from its plan, so a difference in the tables is the
music's and not the reader's; a note's loudness is what the player sets
(the volume column or the sample's default, the sample's global volume,
the channel's), the loudest pitched note's 1, as a decoded note's is; its
grid is the one it writes on (sixteenths and triplets) and it counts
whole, having no loop. Its key is one for the song, as FFVI's: a chorus or
bridge the generator moved to another key gives numerals in the key read,
as a FFVI modulation does. The key read is the generator's home key in 9
and 10 songs of 20, and in 8 and 5 the key its scale's notes spell (a
mixolydian or dorian tune read as the major a fifth or a tone off, a
phrygian as the minor a fourth up: the profile knows major and minor
only), which FFVI's modal tunes get alike. The imported pack's 20 were
composed from a copy of its `pack.json` named `ffvi_imported`: the pack
file loader takes no space or capital in a name, and the import had been
given "FFVI imported". FFVI, the hand-made `ffvi` pack and the imported
one, the rows that differ, the largest and most audible first:

| | FFVI | hand-made `ffvi` | imported |
|---|---|---|---|
| the melody's lengths: a sixteenth / an eighth / a beat or longer | 32 % / 31 % / 27 % | 0 / 15 / 75 | 0 / 18 / 70 |
| the melody on a triplet eighth / detached | 8 % / 27 % | 0 / 4 % | 0 / 5 % |
| the melody's moves: a step / a repeat / a fifth or more | 57 % / 9 % / 8 % | 49 / 18 / 5 | 48 / 19 / 6 |
| onsets off the eighths, and of them on a triplet: bass / accompaniment / melody / drums | 23 % 47 / 36 30 / 24 33 / 41 31 | 1 0 / 18 0 / 10 0 / 28 0 | 4 0 / 11 0 / 10 0 / 37 26 |
| onsets a bar: bass / accompaniment / melody | 4.5 / 7.1 / 3.9 | 2.9 / 4.7 / 2.6 | 2.1 / 1.2 / 2.6 |
| the bass moves: a repeat / a step / a fourth / an octave | 40 % / 24 / 10 / 7 | 53 / 8 / 4 / 18 | 31 / 9 / 5 / 30 |
| the bass's bars: the root held / the root on one and three / on a non-chord tone | 9 % / 1 % / 23 % | 8 / 10 / 4 | 25 / 3 / 4 |
| the held harmony's bars: a chord struck / resting | 50 % / 33 % | 27 / 69 | 23 / 74 |
| chords held, major: I / I5; minor: i / I5 | 18 % / 7; 15 / 15 | 6 / 10; 6 / 12 | 7 / 11; 7 / 15 |
| chord shapes read: major / minor / bare fifth / sus4 | 29 % / 21 / 24 / 7 | 16 / 14 / 46 / 12 | 21 / 14 / 44 / 12 |
| the chord's tones sounding: root, third and fifth / root and fifth with another / root and fifth | 17 % / 9 / 11 | 10 / 24 / 6 | 13 / 13 / 12 |
| the harmony on a non-chord tone / the arp on the third | 8 % / 25 % | 23 / 14 | 14 / 16 |
| spread, the bass to the top: three octaves and more / under one; semitones | 31 % / 27 %; 28 | 9 / 27; 21 | 5 / 43; 14 |
| pitches sounding a span | 4 [2-5] | 4 [2-5] | 2 [1-4] |
| the accompaniment's commonest bars | eighths 14 % (16 songs), sixteenths 7 %, quarters 5 % | one syncopation 40 % (8 songs), eighths 24 %, rest 31 % | halves 41 % (12), a whole note 22 %, rest 35 % |
| the arp | in 5 songs, 10.6 a bar | in every song, 3.8 a bar, a quarter of its bars in quarters | in every song, 3.3 a bar |
| the counter-line | in 51 songs, 4.6 a bar | none read | none read |
| the drums' bars resting / the commonest figure | 13 % / one song's, 3 % | 19 % / kick on one and three, snare on three, hats in eighths, 6 % (9 songs) | 34 % / the same, 1 % |
| the melody above the chord's top (semitones) | 1.7 [-10-11] | 6 [0-12] | 6.6 [0.5-12] |
| chord moves by degree, major: IV -> I / I -> IV / I -> VI / V -> I | 6 % / 5 / 4 / 3 | 5 / 4 / 1 / 3 | 4 / 3 / 2 / 5 |
| the lowest note: the root / the fifth / the third | 46 % / 23 / 14 | 49 / 22 / 11 | 53 / 23 / 13 |

What they say: the generator's writing differs from FFVI's most in its
values. FFVI's melody moves in eighths and sixteenths, with triplets, by
step, sounding most of each note and cut short of a quarter; the
generator's moves in beats and longer, never a sixteenth or a triplet,
repeats a note twice as often, and holds every note to the next. Nothing
the generator writes falls on a triplet (the imported pack's swung drums
apart) and little off the eighths. Its bass repeats or bounces the octave
(the octave bass) where FFVI's walks by step and fourth through passing
tones, and plays half as often; so does its accompaniment, in one
syncopated figure or in halves where FFVI keeps eighths and sixteenths.
Its chords change every two or four bars (the held harmony rests in
seven bars of ten, the tonic is a chord held in a twelfth of its beats
against a sixth) and read as bare fifths half the time, their third
faint; its parts sit within two octaves where FFVI spreads a third of its
spans over three, and the imported pack's songs sound two pitches a
span. It writes an arp in every song and no counter-line the reader
finds, and its drums keep one figure in half the songs. Alike: the
inversions, the bass on the root or fifth, the degree moves' order (IV
and I to and fro ahead of V to I, in both modes), the melody's thirds and
fourths. What a pack could change, as habits: the bass's bounce and
repeats (`bass_style`), the accompaniment's one figure and the chords'
holds (`harmony_mode`), the pitches a span (`harmony_voicing`), the bare
fifths where `power_chords` asks for them, the drums' rests and swing
(`drumless`, `drum_density`, `drum_swing`), the arp's presence and
figures. What needs the generator's writing (stages 3 and 4): the
melody's values (sixteenths, triplets, dotted figures, notes cut short),
the bass's passing tones and its density, a chord a bar, chord tones
spread over three octaves with the third sounding, a counter-line as a
part, drum figures of each song's own, anything on a triplet. What not
to trust: the key read for the generator's modal scales shifts those
songs' numerals (the degree table is like for like with FFVI's modal
tunes, and neither is the composer's numeral); the chord shapes depend on
the parts' loudness (every note at one level, the bare fifths fall from
46 % to 41 % and 44 % to 38 %, still far from 24 %: the generator's bass
and arp sit on root and fifth and its harmony pad plays 2.6 times under
its bass); a composed note's length runs to its cut or the next note, a
decoded note's to its key-off, so "detached" is a different measure on
the two sides and the generator's struck samples decay unmeasured; the
rule that names FFVI's drum sounds names the generator's crash a kick
and its toms and open hat snares, so FFVI's 10 kicks and 13 snares may
hold crashes and toms; the generator's harmony channels are told apart
by the reader's rules, so a pulse figure reads as an arp in two songs,
and no channel reads as a counter-line though the generator writes one
in some chorus and bridge patterns.

Where it stands (2026-10-20), drums by sound: `python -m
bitcomposer.translate.drums --score`, and `--db PATH --spc DIR`
(`translate/drums.py`), name a drum sample from the sample itself, and the
rhythm counts and the comparison take the names when the game's SPC files
are given (`--spc DIR`, the game folders' root or one game's folder;
without them a sound is named by how it is played, as before, and the
table says so). The measure is four numbers from the sample as the game
plays it (at the pitch it plays it most, where its notes name one; a
looped sample repeated as long as the game holds it): the share of its
power under 200 Hz, the share under 1 kHz, its periodicity (the best
normalised autocorrelation of its first 64 ms past the first zero crossing:
a tone near one, noise near nought) and how long it rings (to 40 dB under
its peak), with its centroid for brightness; the spectrum is of its first
128 ms, by an FFT written on the standard library's complex numbers. The
rule: power mostly under 200 Hz is a low drum, a kick when its centroid
sits under 93 Hz, a tom when it holds a pitch, a deep snare when it is a
noisy thud above the kick's range (Seiken Densetsu 3's, Top Gear's); noise
(periodicity under 0.5, or a hiss centred over 5 kHz, since a looped hat
repeats and reads periodic) is a cymbal when it rings 0.6 s, a click when
it is over in 50 ms, a snare when a fifth of its power sits under 1 kHz, a
closed hat when it has no such body and is over in 100 ms; a tone with a
body under 200 Hz is a snare (FFVI's snare is one, a shell with its
rattle), without one another sound (a rim, a block, an orchestra hit, a
pitched instrument played as percussion). Four cases the sound leaves open
are settled by where the game hits the sample, and only those: a low drum
between 93 and 200 Hz holding no pitch (a short kick reads high: Donkey
Kong Country 2's), a kick when it lands on the beats more than between
them; a hiss over 5 kHz with a little body, a hat when it plays off the
beat more than on; a bodiless burst ringing between 0.1 and 0.4 s (an open
hat, a snare without a body, or a cymbal cut short: the built-in packs'
snares are gated noise, told from their open hats by length alone), a
cymbal when it lands on the first beat most, a snare on the other beats,
else a hat; and noise ringing 0.4 to 0.6 s (a cymbal, or a snare with its
room), a snare when it lands on the backbeats more than on the first.
Why these: brightness and length, the pack kit's measures, tell a kick
from a hat but not a snare from an open hat, nor a hat loop held long from
a cymbal; the body under the hiss and the periodicity carry the rest.
Checked: the generator's own named drums (the three palettes' and the four
built-in packs' kits, 51 samples) come out as they are in 49 without being
told, the two missed the chip palette's crash and open hat, bursts of 0.18
and 0.11 s that read as a snare; in the comparison, with the play, 6 of 6
of both packs' kits (the imported pack's snare slot holds FFVI's open hat,
which `pack.py`'s kit picked by brightness; left as it is, the pack format
being out of this slice). FFVI: 23 of its 32 drum samples change name,
carrying 8102 of 14150 hits: by play 10 kicks, 13 snares, 6 hats and 3
others, by sound 2 kicks, 7 snares, 6 hats and 17 others. The snare the
game plays most (19 songs, 9.6 hits a bar, Terra's march) had read as a
hat for its density, and so had the second snare (a looped noise with a
body, Battle Theme's voice 5); Battle Theme's voice-6 open hat (270 ms of
bodiless noise, 54 % of its hits on the off-eighths) had read as the
snare, as the ear said; the cymbal (a looped wash held two beats, in 21
songs) had read as the kick for landing on the downbeat; and 14 one-song
samples that are pitched instruments the roles read as drums (looped
tones at 300 to 1000 Hz) go from kick and snare to another sound. The drum
figures again: the rest, 12 % (24 songs), and the cymbal alone on the
downbeat, 3 % (11 songs: the "kick alone on the downbeat" of the table
above), are the figures many songs share; every other figure is one to
three songs' own, the snare's now showing its marches in eighths and
triplets. The comparison's drum rows change on FFVI's side only: the
generator's drums come named. Over the 39 games, 798 of 804 drum samples
are named by their sound (the rest are silent, the voice playing the SNES
chip's noise generator over them): 63 kicks, 179 snares, 103 hats, 459
others. What looks wrong: most of the others are pitched instruments in
voices the roles read as drums, one song each (stage 1's gap), but among
the most played are tuned percussion keeping time at 9 to 17 hits a bar
(Lufia II's, Chrono Trigger's, Ogre Battle's, Seiken Densetsu 3's) that
the rule names nothing better than another sound; a dull 60 ms noise with
a body that keeps the eighths in 63 Donkey Kong Country 2 songs reads as a
snare; and a looped bodiless noise rings as long as its note, so a hat
loop held long reads as a cymbal.

Where it stands (2026-10-20), the 39 games: `python -m
bitcomposer.translate.games --db PATH` (`translate/games.py`) prints, per
game, the headline numbers of the two counts, each once through: the
tempo, the share of songs in minor, how often the chord changes (fit chord
spans a bar), the share of spans read as a bare fifth, IV -> I and V -> I by
degree alone, the bass walking by step against bouncing octaves, the
share of pitched onsets off the eighths and of those on a triplet (the
median song), the melody's sixteenths, triplet eighths, notes a beat or
longer and steps, the drums' onsets a bar, the share of songs without
drums and the share swung (the off-beat past 0.6 of the beat); with the
songs counted and left out, and the bars of another length than the
meter. Then each number's spread over the games (the middle half's width
against the median, each game once) and what the driver and the
first-listed composer explain of it (the share of the variance between
games their group means take, over the games sharing one, against the
median of 200 shufflings of the labels). The database is all 1836 songs of
the 39 games read with this code, 1469 counted (214 in free time, 153
mostly unfit or silent). The spread:

| | median over the 39 | middle half | lowest / highest | spread | shared or own |
|---|---|---|---|---|---|
| tempo (BPM) | 113 | 91 to 127 | Jurassic Park Part 2 62 / Kirby Super Star 165 | 0.32 | shared |
| songs in minor | 51 % | 41 to 63 | Super Mario World 23 / Axelay 89 | 0.43 | mixed |
| chords a bar | 1.9 | 1.8 to 2.2 | Jurassic Park Part 2 1.3 / Soul Blazer 2.6 | 0.22 | shared |
| bare fifths, of spans | 28 % | 23 to 32 | Dragon Quest V 9 / Uniracers 46 | 0.32 | shared |
| IV -> I, of degree moves | 6 % | 5 to 8 | Pocky & Rocky 3 / Jurassic Park Part 2 11 | 0.32 | shared |
| V -> I | 4 % | 3 to 5 | Super Metroid 2 / Lufia II 8 | 0.16 | shared |
| the bass by step | 20 % | 14 to 24 | Kirby Super Star 10 / Dragon Quest V 33 | 0.50 | mixed |
| the bass by octave | 6 % | 4 to 8 | Uniracers 0 / Top Gear 34 | 0.37 | mixed |
| onsets off the eighths | 38 % | 33 to 46 | Lufia II 20 / Donkey Kong Country 3 58 | 0.35 | mixed |
| of them on a triplet | 17 % | 10 to 24 | Top Gear 0 / Plok 35 | 0.79 | own |
| the melody's sixteenths | 43 % | 34 to 51 | Super Turrican 2 10 / Top Gear 77 | 0.38 | mixed |
| its triplet eighths | 3 % | 2 to 6 | Uniracers 0 / Cybernator 18 | 0.41 | mixed |
| its notes a beat or longer | 23 % | 17 to 27 | Top Gear 6 / Super Turrican 2 38 | 0.44 | mixed |
| its steps | 44 % | 35 to 51 | Top Gear 14 / Romancing SaGa 3 65 | 0.35 | mixed |
| drum onsets a bar | 8.0 | 7.2 to 9.1 | Super Ghouls'n Ghosts 0 / Pocky & Rocky 11.7 | 0.24 | shared |
| songs without drums | 28 % | 13 to 41 | Uniracers 0 / Super Ghouls'n Ghosts 100 | 1.00 | own |
| songs swung | 18 % | 13 to 25 | Final Fantasy VI 3 / Pilotwings 40 | 0.66 | mixed |

What SNES music shares: the harmony. The chord changes about twice a bar
in every game (1.3 to 2.6), a quarter of the spans are bare fifths (23 to
32 % in the middle half, Dragon Quest V's 9 % and Uniracers' 46 % the
ends), and the cadences are the same everywhere: IV -> I or I -> IV leads
in 34 of 39 games (Dragon Quest V and Super Mario World put V -> I first,
at 7 and 5 %; Pocky & Rocky VII -> I, Super Metroid IV -> bII, Uniracers
IV -> VI), with V -> I at 2 to 8 % and never the habit the textbooks would
make it. The drums
play at 7 to 9 onsets a bar wherever a song has them, and the tempo's
middle half is 91 to 127. The melody's steps (44 %) and the inversions are
alike too. What a game makes its own: the grid and the kit. Triplets are
Plok's, Bahamut Lagoon's, ActRaiser's and EarthBound's (28 to 35 % of
their off-eighth onsets) and absent from Top Gear, Lufia II and Kirby
Super Star (0 to 5 %); whether a game writes songs without drums at all
runs from none (Uniracers, Mega Man X 3 %, Axelay 5 %) to most (ActRaiser
65 %, Super Castlevania IV 78 %, Dragon Quest V 86 %, Super Ghouls'n
Ghosts every song, no voice of its reading as drums); swing from FFVI's 3 % of
songs to Pilotwings' 40 %; the bass walks by step in Dragon Quest V,
Donkey Kong Country 2 and Soul Blazer (28 to 33 % of its moves) and
bounces octaves in Top Gear and Super Bomberman 4 (29 to 34 %), where
most games keep both under a tenth; the melody's values run from Super
Turrican 2's long notes (10 % sixteenths, 38 % a beat or longer) to Top
Gear's (77 % sixteenths). Minor keys, bare fifths and the melody's range
of values sit between. Composer or driver: the composer, as far as the
data can tell. The driver explains only the bare fifths and V -> I (0.41 and 0.47
against 0.22 and 0.23 by chance), the share off the eighths (0.66 against
0.22), the melody's steps and the swing (0.45 and 0.51 against 0.21 and
0.23), over the 26 games sharing one (13 of them Nintendo's N-SPC, which range from 27 to 47
% off the eighths and from 0 to 31 % on triplets among themselves); the
first-listed composer, over the 9 games that share one (Nobuo Uematsu's
Final Fantasy IV and VI, Hiroki Kikuta's Secret of Mana and Seiken
Densetsu 3, Koji Kondo's Super Mario World, Zelda and Yoshi's Island, Dave
Wise's two Donkey Kong Countries), explains the tempo, the mode, the chord
rate, the fifths, the share off the eighths and on triplets, the melody's
long notes and steps, the drumless songs and the swing (0.53 to 0.88
against 0.31 to 0.39). The plainest
case is Uematsu's two games on two drivers (FFIV's own and akao): tempo 86
and 85, off the eighths 31 and 29 %, on a triplet 21 and 21, sixteenths
34 and 32, a beat or longer 30 and 26, steps 53 and 57, swung 7 and 3;
nearer each other than either is to any N-SPC game, or than Kikuta's two
are (whose Seiken Densetsu 3 drums at 11.5 a bar against Mana's 7.5). The
composer's share is read from few games and nine pairs would settle it
better; but nothing here says the driver sets a habit beyond what its
composers happened to write. The generator against all 39, the same
comparison over the whole database (`--db games.db --spc ~/data/spc`), 20
songs a pack as before: the games' counts sit where FFVI's did, and the
generator's distance is the same. The melody's lengths over the 39: a
sixteenth 44 %, an eighth 27 %, a beat 11 % (FFVI 32 / 31 / 14; the
generator 0 / 15 / 35), a triplet eighth 4 %, detached 30 % (the
generator 4 %); off the eighths, the median song 38 % (FFVI 29) against
the generator's 7 and 5 %, and 19 % of those on a triplet (FFVI 19)
against none; the bass 5.6 onsets a bar (FFVI 4.5) against 2.9 and 2.1,
by step 20 % (FFVI 24) against 8 and 9, by octave 8 % (FFVI 7) against 18
and 30, on a non-chord tone in 28 % of its bars (FFVI 23) against 4; the
accompaniment 7.5 a bar in eighths or sixteenths (13 and 11 % of its
bars) against 4.7 and 1.2 in one syncopation or in halves; the chord
spans sounding four pitches [3-6] over 29 semitones, three octaves and
more in 37 % of spans (FFVI 31 %), against 21 and 14 semitones and 9 and
5 %; bare fifths 27 % of spans read (FFVI 24) against 46 and 44; and the
degree moves in the same order on both sides, IV and I to and fro ahead of
V -> I. The drum figures across the games are even thinner than FFVI's
(the rest 8 %, hats in eighths 3 % in 34 songs, the cymbal alone on the
downbeat in 106 songs at 1 %, every other figure under 2 %) against the
generator's one figure in half its songs. So what the FFVI comparison
said of the generator's writing holds for SNES music as a whole, not for
one game. Quality: the 367 songs left out are EarthBound's above all (97
of 206: its jingles and its free-time pieces), Secret of Evermore's (29
of 72), Super Metroid's (17 of 36, its ambient music), Chrono Trigger's
and Kirby Super Star's (18 and 19); 222 counted songs were followed
loosely on no grid, 38 of Donkey Kong Country 2's 87 and 36 of Donkey
Kong Country 3's 68 (their swung and shuffled rhythms; loose songs give
the off-eighths and triplet shares as read, a grid's rounding not
applied), and a fifth of the bars of Final Fantasy IV and VI, Romancing
SaGa 3, ActRaiser and Top Gear are of another length than the meter (the
grid restarting at section joins: Dancing Mad's five parts carry 227 of
FFVI's); Top Gear (7 songs) and Uniracers (10) sit at the ends of several
columns on few songs. What it means for the vocabulary: one shared
vocabulary, with per-game weights, not a vocabulary per game, composer or
driver. The habits a vocabulary is made of are the same across the 39
(the chord rate, the open voicings, the modal cadences, the drum density,
the melody's steps: the shared rows), so one table of chord moves,
voicings, rhythms and figures drawn from all 39 games would be the SNES
chip's own idiom and fuller than any one game's (FFVI's moves and
patterns were spread thin at 2 to 3 % a row; the 39 together give the
shared rows weight); what a game makes its own is which rows it draws
and how often (its grid: triplets, swing, sixteenths; its kit and whether
it plays; its bass's walk or bounce; its mode), which per-game weights
over the shared tables carry, as the thin pack's habits already do for
the tempo, the mode and the drumless share. A pack by composer, as the
plan has it for later, would be the same weights counted over that
composer's games, and the evidence above says those weights travel with
the composer across drivers; a pack by driver would not add a habit the
composers' do not already hold.

Where it stands (2026-10-20), progressions by part and the melody's
phrases, the last two items of "from the readings": `python -m
bitcomposer.translate.phrases --db PATH` (`translate/phrases.py`; `--games`
for the 39, `--against PACK` for the generator, `--heard JSON` for the parts
marked by ear; `games.py` and `against.py` take `--phrases`) prints two
tables over the harmony counts' songs that have a form read. The parts are
the form reader's (stage 1, the form table's parts: a phrase, a short one
played again two parts), a part repeating an earlier one left out of the
progressions. The chord reader changes chord every beat over half the
time, so a progression counted beat by beat is buried in passing chords;
each half bar (a bar of three whole) takes the fit chord sounding most of
it, the one sounding first at a tie, which keeps the chords on the strong
beats: in FFVI's parts the half bar keeps 63 % of the beat-level moves
and the bar 40 %, the bar losing the change on the third beat. The chords
are named by degree alone (I, IV, bVII: the shapes were spread thin, and
I, I5 and Isus4 are one chord held with its third coming and going). A
part's progression is its chords through its bars with runs merged, and
where they repeat a cycle (I IV V I IV V I) the cycle; with it the
three-chord runs, the part's first and last chord, its cadence (V -> I,
IV -> I, bVII -> I with the natural minor's VII -> I, another chord to I,
a half cadence on V, elsewhere, one chord), what the song loops back on
and how often the chord changes in the part's first bar, its middle bars
and its last. The melody's phrases are the part, and four and two bars
cut from its start; the tune is the melody voice's line, and where that
voice rests through a phrase the counter-line's stands in (FFVI's tune
passes to it; the accompaniment does not stand in, its line being the
chord's top), a phrase with neither left out and the shares said. The
contour is from the mean pitch of the phrase's thirds by time (an arch
where the middle sits two semitones over both ends, a valley under, rising
or falling where the ends differ by two, level otherwise), the peak the
first highest note placed in the phrase's quarters, the range the highest
to the lowest; the first note and the end note (the note held longest in
the last bar, since a phrase's last notes are mostly the pickup into the
next: counted as the last note, Terra's phrases ended on their upbeat and
a phrase ended on the tonic 18 % of the time, not 21) are named against
the key and the chord at their onset; and against the phrase before it in
the song a phrase is repeated (three quarters of its notes match in place
and pitch), moved up or down (they match shifted by one interval, a
semitone's drift allowed for a diatonic sequence), answered (the rhythm
matches, the tune not) or new. FFVI, 66 songs of 82 (13 in free time, 2
unfit, 1 with no form read), 349 parts, 269 of them new and with a chord:

| | FFVI |
|---|---|
| a part is built on | one chord 16 %, 2 to 4 chords 36 %, 5 to 8 19 %, more 28 % |
| the progressions counted most, major (86 parts, 24 songs) | VI 3 %; I VI, V, I IV, III, I bVI, I 2 % each (2 to 3 parts each) |
| minor (183 parts, 42 songs) | I 14 % (25 parts in 16 songs), I IV 4 % (8 parts in 8 songs), IV 3 %, IV I 3 %, I VI 2 %, IV VI 2 %, I #IV 2 % |
| three-chord runs, major / minor | I IV I, I bVII I, IV I IV 2 % each / I IV I, I VI I, IV I IV, I bII I 2 % each |
| a part begins on | I 41 %, IV 17 %, VI 11 %, III 10 %, VII 6 %, V 5 % |
| ends on | I 37 %, IV 16 %, V 12 %, VI 12 %, III 6 % |
| its cadence | IV -> I 9 %, V -> I 4 %, bVII -> I 4 %, another chord to I 9 %, half (on V) 11 %, elsewhere 46 %, one chord 16 % |
| the song loops back (57 songs) | V -> I 18 %, IV -> I 9 %, another to I 14 %, the same chord 19 %, elsewhere 37 %; onto I 60 %, IV 16 % |
| chord changes a bar: the part's first bar / middle / last | 2 [1-3] / 1.5 [1-2.3] / 2 [1-2]; the last bar changes more than the middle in 39 % of parts, less in 45 % |
| phrases: the part / 4 bars / 2 bars | 349 / 636 / 1115; from the melody 74 / 76 / 70 %, the counter-line 12 / 12 / 14, resting 14 / 12 / 16 |
| contour (4 bars) | falling 28 %, rising 24, level 33, valley 9, arch 5 (the part: valley 12, arch 6) |
| the peak in the first / second / third / last quarter (4 bars) | 43 / 20 / 19 / 18 % |
| range, semitones: the part / 4 bars / 2 bars | 13 [8-18] / 10 [7-15] / 8 [5-12]; within a fifth 22 / 31 / 44 %, over an octave 55 / 38 / 23 |
| starts on the key's 1 / 3 / 5 / another degree / off the scale (4 bars) | 23 / 16 / 18 / 30 / 13 % |
| ends on | 21 / 15 / 17 / 30 / 17 % (the part: 26 / 18 / 16 / 25 / 15) |
| starts on the chord's root / third / fifth / another tone (4 bars) | 26 / 18 / 26 / 28 % |
| ends on | 23 / 18 / 28 / 31 % |
| a phrase ending a part ends on the tonic / one inside a part / the song's last before its loop (4 bars) | 24 % / 18 % / 25 % |
| against the one before (4 bars) | repeated 6 %, moved up or down 2 %, answered 7 %, new 74 %, the first 12 % |

What they say: FFVI's parts are not built on progressions. A part sits
on one chord or two in half the cases (I alone in 25 minor parts of 16
songs, I and IV to and fro in 8 songs), and the rest is each part's own
sequence, the cycles no more shared than the chord moves were (3 parts at
the top in major); the three-chord runs that recur are I IV I and IV I IV,
I VI I in minor and I bVII I in major, the pendulum of stage 4's first
count, with I bII I the Neapolitan colour. A part begins on I in two of
five and ends on I in little more than one of three, and the cadence is
mostly none: a part ends on IV, VI or V as often as it closes, and when it
closes, IV -> I and another chord to I twice as often as V -> I; the half
cadence on V is one part in nine. The song's loop is where FFVI cadences:
V -> I in 18 % of loops against 4 % of parts, and the loop lands on I in
three songs of five. The chord does not speed up into a part's end: the
last bar changes as the middle does, and the first bar more (its first
chord counts). The melody's four-bar phrases fall as often as they rise
and sit level a third of the time, the arch (the textbook phrase) one in
twenty: the peak is in the first quarter of the phrase in 43 % of them,
and in the part's phrases the valley (high at both ends, low between)
outdoes the arch two to one. The range is an octave in four bars and over
one in the part, a fifth in two bars. The tune starts and ends on the
chord's root or fifth more than its third, and on the key's tonic a
quarter of the time at either end; a phrase ending a part ends on the
tonic in 24 %, one inside a part in 18 %, so the tonic closes a part
little more than it closes a phrase, and the song's last phrase before
the loop no more. Phrases are new against the one before three times in
four; the ones heard again are repeated outright (6 %) or answered, the
same rhythm with another tune (7 %, Terra's consequent among them), and
the sequence (the same shape moved up or down) is rare, 2 % at four bars
and 5 % at two. Over the 39 games, 1307 songs with a form read, the
shared rows are the harmony's again: a part on four chords or fewer (46
%, 40 to 54 in the middle half), ending on I (33 %, 29 to 38), V -> I (4
%, 3 to 7; Super Mario World 14 and Dragon Quest V 13 the ends, as in the
moves table), bVII -> I (3 %), the chord rate into the end (38 % of parts
change more in their last bar everywhere), and the melody's contours
(rising 26 %, falling 26 %, the peak in the second half 40 %, the range
12 semitones, all within 0.35). What a game makes its own is whether its
phrases come back: repeated 6 % at the median but 0 in Pilotwings and 23 %
in Top Gear, answered 6 % but 0 in Super Turrican 2 (every phrase new) and
22 % in Soul Blazer (Seiken Densetsu 3 16, Secret of Evermore 17, Zelda
17), spreads of 0.76 and 0.82; and between, the half cadence (Bahamut
Lagoon 5 % to Romancing SaGa 3 24), a part beginning on I (Cybernator 11
to Top Gear 55), a phrase ending a part on the tonic (Ogre Battle 9 to
Super Mario World 42), the level phrases (Cybernator 11 to Donkey Kong
Country 3 52) and the arch (2 to 16). The composer explains the cadences
(V -> I 0.67, bVII -> I 0.78, the half cadence 0.64 against 0.29 to 0.34
by chance), the level phrases (0.62), and whether phrases repeat, move or
are new (0.68, 0.70, 0.80), as it explained the grid and the kit; the
driver only a part ending on I (0.47), the half cadence (0.40) and the
range (0.39). The generator against FFVI, the same comparison with
`--phrases` (a composed song's parts are read by the same form reader
over its notes placed in time, since its plan records its sections' kinds
but not their lengths; the reader cuts 164 and 183 parts from 131 and 132
planned sections, a four-bar pattern a part): its parts are built on as
many chords as FFVI's (one chord 17 / 13 %, two to four 35 / 34) and
change chord at the same rate into their end, but begin on I in a quarter
against two fifths and on V in 15 % against 5, end on V in 29 / 25 %
against 12 and on I in 20 / 21 % against 37, so the half cadence is one
part in four (25 / 20 %) against one in nine, and bVII -> I is 1 % against
4. Its four-bar phrases are level in 38 / 45 % against 33, their peak in
the last quarter in 6 / 8 % against 18, their range 7 semitones against
10, their end on the chord's root or fifth in 55 / 67 % against 51 and on
the tonic when ending a part 16 / 18 % against 24; and the generator
answers: 28 / 32 % of its phrases keep the one before's rhythm with
another tune against FFVI's 7, and 1 / 0 % repeat it against 6. So what a
pack could set: the chord a part opens and closes on and the loop's
cadence (begins on I, ends on I, V -> I at the loop, not the half
cadence), the phrase's range and where its peak falls, and that phrases
come back repeated as often as answered; what needs the generator's
writing (stage 4's next slice) is a tune that rests in bars the
counter-line carries (none read in its songs), phrases that return across
a part (a four-bar phrase repeated within the part is 6 % of FFVI's and 1
% of its own), and an end note held on the tonic. How far the form
reader's parts can be trusted for this: over the 23 songs marked by ear
with their parts (12 marked by bar on the bar lines of the time, 11 in
seconds), the reader's part starts agree within three quarters of a bar
with 73 % of the marked ones (68 of 93) and 65 % of its own are marked
(104 read; the 12 marked again at the scale of sections against its
sections: 76 % and 57 %), the loop within a second in all but three
(Athletic and Kakariko Village a bar or two off, Snakey Chantey's not
read); counted on the marked parts instead of the read ones, those 23
songs give 84 parts against 104 and the headline numbers move by five
points or fewer (a part on four chords or fewer 41 to 37 %, begins on I
32 to 37, ends on I 33 to 29, V -> I 7 to 4, the half cadence 12 to 15,
a phrase ending a part on the tonic 35 to 30, repeated 5 to 8, answered 8
to 10, new 85 to 81) except the chord rate into the end (29 to 41 % of
parts change more in their last bar), which depends on which bar the part
ends in; so the shares above hold within a few points, the part count
runs a fifth high, and anything that turns on a part's last bar is the
roughest. What looks wrong: a part cut by the reader where the repeats
cut, not where the harmony closes, leaves a cadence "elsewhere" (46 %)
that an ear would place a bar on; the phrases are cut four bars from the
part's start, so a part read a bar late shifts every phrase and its
pickup lands in the phrase before (the held end note mends the end, not
the start); a part of 30 bars (Terra's last) is one "phrase" at the part
scale, so the four-bar rows are the ones to draw from; the ends off the
scale (17 %) are the key read for modal tunes and the melody's chromatic
passing notes as much as the tune; "level" takes a tune circling a note
within two semitones, and a tune in sixteenths that rises and falls
within each third reads level too; and the counter-line stands in for a
resting melody as one line, which is right where the tune passes to it
and wrong where it is a countermelody under a rest, which the readings
cannot tell apart.

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
VGM logs, into the same translator; MPTM output for converted songs, for
timing finer than IT's ticks and more echo repeats (for generated songs,
stage 3 says when).

## To settle as we go

- **Where the database lives**: settled (2026-10-20): the user's data
  folder, with the packs (`~/.local/share/bitcomposer`, or
  `BITCOMPOSER_DATA_DIR`).
- **Tuning to taste**: settled (2026-10-20): only in the pack. Importing
  again starts fresh; EXPORT keeps a pack as it is, ADD brings it back.
