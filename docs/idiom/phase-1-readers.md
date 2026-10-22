# Phase 1: the readers

Planned in detail 2026-10-20. See `../IDIOM.md` for what it serves and the
rules it keeps.

## Goal

Before any table is read from them, each reader (the beat and bar, the key
and mode, the chords, the roles and the tune, the form, the drums) is
scored on ground truth it was not tuned on, fixed where it fails, and the
stage 4 counts are run again, so the plan rests on what the music does and
not on what the readers do to it.

## Starts from

The readings of the 39 games (stage 1); the stage 4 counts and their
"what looks wrong" (`../TRANSLATOR.md`); the beat marks (43 songs) and
form marks (36) already made by ear; the decoder, proven against the
emulator's own output to 0.45 dB at the median over 1836 songs
(`drivers/`), which makes that output the arbiter of what was played.

## Three kinds of ground truth, and what each can judge

Each reader is judged by the source that shares nothing with it.

| source | judges | cannot judge |
|---|---|---|
| **An independent decode** (VGMTrans, below): the sequence data a driver plays, read to MIDI by code that shares nothing with the emulator or the readers | the tempo as written and the beat the composer counted in (so the tempo-octave); the loop's end and start; every note's onset and written pitch, hence the tuning; written lengths against played ones | bars and meter (not in the data), key, chords, parts, which voice is the tune, what a drum is |
| **Songs with known answers**: the generator's own songs, whose key, scale (the modes included), chords, sections, tune and drum pieces are known from their plan | the key and mode reader, the chord reader, the form reader, the roles, the drum namer, each with recall and precision | the decoding (the songs are not played through the SNES chip), and anything the games do that the generator does not: a floor, not a pass |
| **The ear**, three pages built like the Ear Check and Form Check pages | where the harmony changes (the chord rate, without naming a chord); which voice carries the tune, and where it passes; what a drum sound is | a chord's name, a key |

The emulator's audio arbitrates when the independent decode and the
readings disagree about a note: the audio has it or it does not. The ear
arbitrates the felt beat: a composer who wrote at double tempo wrote a
beat the listener does not clap, and both readings are kept with a note
that says so.

### The independent decode

VGMTrans reads the sequence formats of most of the 39 games' drivers
(Nintendo's N-SPC, Square's AKAO and Suzuki, Rare's, Konami's, Capcom's,
Hudson's, Chunsoft's, Neverland's, Software Creations'), not all (Factor
5's, Ocean's, NCS's, Quest's and Rainbow Arts' have no reader there). It
converts a song's loop by playing it through a set number of times rather
than marking it: converted with no repeat, the MIDI ends where the song
jumps back, which is the loop's end; converted with one repeat, the tail
past that point is the written notes from the loop's start again, and
aligning the tail with the body gives the start exactly. Its shell build
runs without a desktop. Built from source on the machine that holds the
games, for checking only, never shipped.

Where it reads fewer of the 39 than hoped, or misses a driver family that
matters, games it does read are added to the validation set from their
SPC sets: the readings are driver-agnostic, and a game need not join
`drivers/` to serve here.

## The steps

1. **The survey.** Build VGMTrans; run every song of the 39 games through
   it; record which games and which songs convert, and which do not; learn
   the shell's commands and the loop-repeat setting. A table per game:
   songs, converted, failed, the reader it used.
   *Produces:* the coverage table; MIDIs with no repeat and with one, kept
   with the readings on the machine.

2. **The decode comparison.** A harness (the standard library's MIDI
   parsing is a page of code) that, per song, matches the MIDI's notes to
   the readings' notes by onset and compares: the tempo (written against
   read, and whether they differ by exactly two); the loop's end and start;
   onsets (the share of written notes with a decoded note within a
   tolerance); pitch (the share agreeing, after one constant offset per
   sample, and the offsets themselves, which are the tuning check over
   every covered game); written lengths against played ones (kept as a
   measure for the values vocabulary rather than scored). Every
   disagreement classified: ours, theirs, or a real ambiguity, with the
   emulator's audio as the arbiter for notes.
   *Produces:* a per-game table of each measure; the list of
   disagreements with their class; the tuning offsets.

3. **Songs with known answers.** Sixty generator songs across its scales
   (every mode it has, pentatonics included), all twelve keys, its five
   forms, with and without drums, across bass styles and harmony modes;
   their answers taken from the plan (the key, the scale, the chord on
   every beat, the section boundaries in bars, the tune channel, the drum
   channels), read through the same path `against.py` uses, and each
   reader scored: tonic and mode (a parent-key reading counted as its own
   kind of miss), chord per beat, part starts within a bar, the tune voice
   per bar, each drum piece.
   *Produces:* recall and precision per reader, with the misses listed by
   kind.

4. **The ear's pages and their scoring, agreed before the first tap.**
   - *Chord Change Check.* Twelve songs, chosen to cover: games the
     independent decode reads and games it does not; songs the chord
     reader changes chord in most and least; songs read as modal and as
     plainly major or minor; slow and fast; two whose beat is already
     marked. The listener taps when the harmony changes; no chord is named.
     Six of the twelve are the development set, on which the counting
     level (the beat, the half bar, the bar, or the root-motion rule below)
     is chosen; the other six are held out and give the score. A tap and a
     read change match within half a beat, the taps shifted by the
     listener's reaction (0.12 s, as the Form Check page found). Scored:
     precision, recall, and the rate ratio (read changes a bar over tapped
     changes a bar).
   - *Tune Check.* Ten songs where the melody voice rests in a third of its
     bars or more (the readings name fourteen in FFVI alone) and others
     from games where a counter-line is read. The full song plays; a
     button per voice (each with a solo to hear it by, named by number, the
     reader's guess hidden until the marks are saved); the listener holds
     the voice carrying the tune, switching as it passes, and "none" where
     no tune plays. Scored per bar: the reader's tune voice against the
     marked one, over bars where a tune is marked.
   - *Drum Name Check.* Forty drum samples drawn at random over the 39
     games with probability by how often they are hit, each played three
     times as the game plays it (its pitch, its length, its spacing) and
     once in its song with the voice soloed; named kick, snare, closed hat,
     open hat, cymbal, tom, other, or unsure. Scored as a confusion matrix
     against the namer; kick, snare and hat the headline. The namer's
     rule was set with the generator's kits and a look at the most played
     samples in view, so this draw is the first held-out test it gets; if
     the rule changes on it, twenty fresh samples score the change.
   The marks stay on the machine with the beat and form marks; the scores
   are recorded here.

5. **The fixes, as the scores demand,** each landed with its score before
   and after on every ground truth above and on the beat and form marks
   already made (a fix that moves a heard song from right to wrong is a
   regression unless explained):
   - *The key and mode.* The parent scale from the pitch-class content, as
     now; the tonic from emphasis (the loop's landing, the bass's most held
     pitch class, the phrases' final notes, the first chord); the mode as
     the parent scale rotated to the tonic; numerals named from it.
     Pentatonic and ambiguous tunes report the parent scale and tonic and
     say so.
   - *The chords.* A harmonic-rhythm layer over the beat-level spans: a
     change where the bass and the accompaniment's root moves, not where a
     melody's passing note shifts the match; the level the development set
     chooses. The beat-level spans are kept as data.
   - *The tune.* One line across the voices that carry it, bar by bar, the
     counter-line and accompaniment joining where the melody voice rests
     and the Tune Check says they carry it.
   - *The drums.* The namer re-judged on the forty; the rule changed only
     where the matrix says, and re-scored on fresh samples.
   - *The bars at section joins.* The decode's tempo events say whether a
     grid restart sits on a real tempo change (then it is the music) or
     not (then the reader slipped); the second kind fixed where the cause
     is found, the first kind kept and counted.
   - *The songs in free time.* Measured on their own: how many per game,
     their density, held notes, drums and dynamics, reported as the
     ambient and cinematic share rather than dropped in silence.

6. **The counts again.** The 39 games read with the fixed readers; the
   stage 4 counts, the comparison and the shared-or-own table run again;
   `../TRANSLATOR.md`'s Stage 4 numbers refreshed with what moved and why;
   the shared-vocabulary hypothesis kept or dropped on the new table.

Steps 1 to 3 run unattended and in parallel once the machine has the build
tools; step 4 needs the listener for about an hour, its pages and scoring
written first; step 5 waits on 2 to 4; step 6 on 5.

## Where it stands

**Steps 1 and 2 (2026-10-20): the independent decode, surveyed and compared.**
VGMTrans (its shell build, `tools/vgmtrans_batch.py`) reads 1581 of the 1836
songs: 33 of the 39 games in full or nearly (EarthBound's 57 unread are its
jingles and sound-effect pieces), none of the six whose drivers it has no
reader for (Cybernator, Secret of Evermore, Jurassic Park 2, Ogre Battle,
Rendering Ranger, Super Turrican 2). Its shell exports with no loop repeat
by default (the loop's end); a second build with one repeat gives the
loop's start by alignment. `tools/decode_check.py` matches each MIDI to the
decoder's notes under a piecewise time map (the two decodes' clocks differ
by parts in ten thousand, one slips a note now and then, and a song dumped
mid-way has no played intro) and to the readings. What it found, over the
1468 songs both sides read:

- **The notes.** Counting a written note the decoder plays as a pitch
  change under a held note (a slur), the decoder has every written note in
  every game: the median song matches 1.00 in 29 games and 0.93 to 0.99 in
  the rest. Strictly by key-on, three drivers play most written notes
  legato (DKC 0.32, Super Mario World 0.36, Pilotwings 0.16, the last two
  from sets dumped mid-song), which the values vocabulary will have to
  know: a slurred run and a held note are the same key-on.
- **The pitch, and the tuning fix.** Over the pairs no pairing doubt
  touches, the written pitch and the played agree after one whole-semitone
  offset per sample in 1.00 of notes in 24 games, 0.98 in FFVI, and the
  tuning check it was for holds: no sample's offset sits off a whole
  semitone where the decode is right. Four readers disagree by several
  semitones on some notes (Konami's games 0.68 to 0.86, Hudson's 0.69,
  Rare's DKC 0.23, Super Mario World 0.50); the emulator's own output,
  tapped at the disputed notes, sounded the decoder's pitch in 44 of 45 it
  could measure. Those readers drop transposition the drivers apply;
  VGMTrans's pitch is not ground truth there.
- **The tempo.** Two readers emit one default tempo for a whole game
  (Kirby Super Star 125 in 58 of 69 songs, Pilotwings 73 in all 21), so
  the written tempo is a measure only where the reader has one. Over the
  rest, the read tempo is the written one or exactly twice or half it in
  79 % of songs; a compound against a simple level (4:3, 3:2, 3:4, the
  triplet ambiguity the tap rounds met) in 11 %; and "other" in 10 %, of
  which 104 of 129 are songs with over 15 % of written onsets off the
  read grid: the swung and shuffled songs the beat reader follows loosely
  (Donkey Kong Country, Super Mario World, Yoshi's Island). The written
  onsets fall on the read grid's beats, sixteenths or triplets in 90 % or
  more of notes in 25 games. Where both are clean the ratio sits at 1.000;
  Super Mario World's reader runs 1.8 % fast against the emulator.
- **The loop.** Where the read loop's length matches the written (744 of
  the 923 songs a loop is read in), the read cut sits on the composer's
  jump in 321, a whole number of bars from it in 100 (the same loop cut
  elsewhere), and **a fraction of a bar off in 317**: composers jump on a
  bar line, so the readings' bar phase is wrong in those songs, which the
  tap rounds could not see (they checked the tempo and the bar's length,
  not where the one falls). The reader misses 177 loops the composer
  wrote, 43 of them under its four-bar floor, and reads a different length
  in 123 (Axelay's Bravo: a 5 s repeat for a 32 s loop).
- **Written lengths against played.** The played note runs 0.9 to 1.0 of
  the written in most games (the drivers' gate), 1.3 to 1.4 in Rare's and
  Capcom's, 1.9 in Dragon Quest V: the values vocabulary reads the written
  value through the driver's gate, not the key-off.
- **The sets.** Super Mario World's and Pilotwings' SPC files were dumped
  mid-song (the written intro never plays, and the written start aligns
  with the played song 3 to 20 s in), which their form and loop readings
  inherit.

What the readers need from this, in order: the bar phase (step 3 below)
and the loop reader (the composer's jump as ground truth on hundreds of
songs); the beat grid where the jump falls (step 3's finding); the
swung grid; a convention for the compound-against-simple level, where the
written tempo says what the composer counted. The tuning and the decoder
need nothing. The MIDIs and the comparison stay on the machine with the
readings; the tools are in `tools/` (on the phase's branch until its PR).

**Step 3 (2026-10-21): the bar phase, from the composers' jumps.**
`tools/bar_phase_check.py` scores where each composer's loop jump falls
in the read bar, the games split in two by a fixed hash of the game's
name: a development half to tune on, a held-out half to score. Before:
right (on the line, or a pickup a beat before it) in 57 % of the
development half's 300 steady songs and 67 % of the held-out's 589, a
half bar off in 20 % and 16 %. A first fix, the bar from where the bass
lands on a new pitch class, gained on the development half alone (63 %;
held-out 67 %, 26 songs fixed and 22 broken) and was withdrawn. The data
was then asked which beat-level signs sit on the downbeat at all
(`~/diags/bitcomposer/idiom/downbeat_features.py` and `downbeat_combo.py`,
on Ragnarok beside the readings): over the 580 songs in 4/4 whose jump
lands on a read beat, accents by level put 30 % of their mass on the
composer's beat (chance 25 %), the bass's onsets 34 %, its pitch-class
changes 41 %, the chord reader's changes 36 %, a note held two beats or
more 58 %, one held the whole bar 65 %, and where the song starts
repeating itself (the form reader's own machinery, at beat resolution)
57 % over every repeat weighted by its length and 63 to 73 % for the
loop's second pass. Weights fitted over all 28 signs on the development
half overfit (72 % there, 66 % held-out); a fixed five-sign rule (the
loop's second pass, repeats by length, whole-bar notes, long notes, the
accents) scores 74 % on the held-out half (84 % with a pickup) against
the readings' 64 % (75 %), and a two-level table (the downbeat's share,
the rest spread evenly) the same as the full one. That rule is
`translate/phase.py`, run after `beat.rebar`, the phase set once a song.
Re-read: development 71 % (a half bar off 8 %), held-out 76 % (9 %);
on the line alone 53 to 59 % held-out; 102 held-out songs fixed, 46
broken; every game gains but two (Mega Man X 62 to 38 % on 13 songs,
DKC3 56 to 50 % on 18); the 41 tapped beats unchanged (40 right). The
jumps that land a beat *before* the read line grew (78 to 100 held-out):
a loop that starts on a pickup, or a repeat found a beat late; only a
listener's downbeats can tell them apart, so a short tap round (the one,
on the chord and tune sets' songs, about fifteen minutes) is proposed
before the pickup is scored either way.

Found on the way: in 36 to 41 % of the steady songs the composer's jump
is not on a read beat at all (within 0.2 beat). In over half of those,
two or more voices start together at the jump (within 60 ms), so the
jump is a real onset the grid has no beat on: a syncopated song's beat
locked a sixteenth off (The Decisive Battle), a half-tempo grid on the
off-beats, and the grid's section joints, which drop or shift a beat
(948 joints of 2.0 beats and 1364 of 1.25 to 1.75 over the 1836 songs;
songs with five joints or more have their jump off the beat twice as
often as songs with none, 48 % against 28 %). The rest fall at a rest
or mid-phrase. This is the beat reader's next item, ahead of the swung
grid; the verdicts above exclude these songs.

On the chord check, the two songs marked so far calibrate the taps.
Hyrule Field's changes sit on its bar lines (the bass's roots, one a
bar); the raw marks sit 0.28 s after the nearest line on average, with a
spread of 0.17 s, so a mark is moved 0.25 s earlier and matched within
0.35 s, in seconds rather than the half beat proposed, since the hand's
jitter does not scale with the tempo. With that, Hyrule Field: the
readings' changes on bar lines match 23 of 24 marks (F1 0.96), every
read change F1 0.70 (the reader changes twice a bar, 1.96 against the
1.00 heard). Kefka (marked "hard", from the harmony voices alone): 13
marks over 59 s, mostly one every two bars; the reader makes 3.6
changes for each heard, F1 0.43 over every change and 0.52 on bar lines
(`~/diags/bitcomposer/idiom/chord_score.py`).

**Step 4 (2026-10-21): the chord changes, against the listener's marks.**
All twelve songs are marked (the page's collection `chordtaps1`, kept as
`~/diags/bitcomposer/idiom/chords/heard-chords.json` on both machines
with `chord_review.py`, `chord_score.py` and `chord_eval.py` beside it):
Kefka twice, the second pass counting, marked "hard"; three songs with
no change heard at all (Underground Castle, Harid's Theme, Welcome to
Your Sanctuary: "the same chord with things happening on top"). Against
the notes themselves (the bass's most-sounded pitch class a bar and the
chordal voices' pitch set, `note_changes.py`), the marks are confirmed
in eight songs (F1 0.89 to 1.00), half caught in the one fast song
(Gourmet Race, 169 BPM, a change every bar or two: the limit of tapping
at speed), and differ in Harid's Theme and Hall of Collosia, where the
listener hears a stable ground under moving lines, and in Kefka, where
the marks fall half a bar from the read bar lines. The taps run 0.25 s
late with a 0.17 s spread on Hyrule Field and about 0.4 s late on slow
songs with soft attacks, so a mark is moved 0.25 s earlier and matched
within 0.5 s. The beat-by-beat reader against those marks: F1 0.53 on
the development six, 0.25 on the held-out six, making 1.4 to 39 times
the changes heard (it relabelled on each note of an arpeggio, each step
of a bass figure, and each time the texture thinned or filled; a chord
that stopped and restarted counted twice). The reader is rewritten bar
by bar (`harmony.chords`): a new chord where the bass settles on another
root or the chordal voices' set changes by half, a bar with nothing
tonal carrying the chord on, each span's chord the best shape on its
pooled pitch classes with the bass's root preferred, a span with no
chordal voice an implied chord (`Chord.stated`, the "no stated harmony"
texture: 204 of the 1622 songs on a beat have no voice read as harmony,
arpeggio or accompaniment). Tried on the development half and dropped:
hysteresis on the bass root (settled Harid's riff, broke Crateria's
alternation through a pitch the two chords share), the bass alone
deciding where it sounds (lost Gourmet Race), half-bar spans (Kefka
0.11 to 0.50, but Harid's and Collosia's changes doubled). Result:
development F1 0.65, four of six at 0.75 or better (Kefka 0.17 and
Harid 0.00 the misses); **held-out F1 0.85, five of six at 0.75 or
better** (Underground Castle, Still of the Night, Crateria, Psycho Spin
and Sanctuary at 0.95 to 1.00; Hall of Collosia 0.12, its arpeggio sets
changing 28 times where four changes are heard, and no bass voice read).
The exit criterion is met on five of the six. Over the collection the
median root changes a bar falls from 1.45 (857 of 1136 steady songs over
one a bar) to 0.52 (quartiles 0.30 to 0.71, none over one), which
retires the handoff's "twice a bar everywhere" as a reader artifact,
and with it the chord-rate and pitch-class-count rows of the
shared-or-own table until they are counted again. Open: inner-voice
motion over a static bass (Harid, Collosia), Kefka's half-bar offset
(the downbeat round will say whether it is the bar's phase), the
counting level for fast songs, and the role reader finding no bass in
Collosia or Still of the Night.

**Step 5 (2026-10-22): the tune's carrier, against the listener's marks.**
All ten songs are marked (the page's collection `tunemarks1`, kept as
`~/diags/bitcomposer/idiom/tune/heard-tunes.json` with `tune_check_db.py`,
`tune_rules.py` and `voice_features.py` beside it). Two have no tune at
all: Jungle (drums, bass and noises where a tune would be) and Toughness
(a distorted layer that the rip set's own "Noiseless" variant removes;
our render matches Game Music Emu's within 2 dB in every band, so it is
the song, not the emulator). One is a tune harmonized in a second voice
(Yoshi's Island's Overworld, voices 1 and 6 striking together on 71 % of
their notes, a sixth apart); one passes the tune between voices (Escargo
Express: a fast plinking voice all through, a pair in thirds taking the
lead two bars in four); one has its tune in the bass for its first 24 s
(Top Gear's Title). The reader's melody voice was the marked carrier in
20 % of the bars a carrier was marked in: three times it had chosen a
voice with a handful of notes in the whole song (Super Mario World's
Overworld, Escargo Express, Celes's intro voice), elsewhere a quiet high
line under a louder one, and once the louder twin of an echo pair the
listener named by the quieter (Gang-Plank Galleon's voice 6 repeats voice
2's every note 150 to 200 ms later at a third of its level, missed by an
echo rule asking for one delay to 4 ms). Changes, in `roles.py`: a melody
candidate must have a note on a quarter of the song's beats, at a quarter
of the loudest pitched voice's level, with its median below C6 (Jungle's
noises sit above); its variety is weighed by the square root of presence
times level and held back over two notes a beat (figuration); none
passing, no melody. The echo detector allows a 30 ms wobble with a focus
test, refuses a voice that repeats itself at the delay (a pumping bass,
every eighth) and keeps only the quieter of a mutual pair. Result, on the
same ten songs: **89 % of marked bars** (422 of 473; the 85 % criterion
is met on the set the rule was built from, so a fresh ten is needed
before it counts), the "no tune" bars read as no melody in 104 of 158
(both tuneless songs whole; the interludes inside songs need a carrier
that varies in time), the chord and bar-phase scores unchanged, the 41
tapped beats 40 right as before. Misses: Escargo Express (the hocket:
its constant voice is a quarter the level of the others and fails the
loudness gate), Top Gear's bass intro, and 72 songs of the collection
(4 %) with no melody voice. Found on the way: which voices the beat is
read from moves its level and its grid in dozens of songs (48 to 91
changed, a tapped song lost and one song fallen to free time, when the
echoes the looser rule finds were left out of the beat), so the beat
keeps the old 4 ms rule for leaving an echo out and the parts use the
better one; the self-repeat refusal alone still changes 15 songs' tempo
or meter. Open: a carrier that varies in time (the plan's composite
line), the harmonized second voice as a role of its own, the tune in the
bass, and the beat's dependence on which voices it is read from.

**Step 6 (2026-10-22): the drum names, against the listener's.** All
forty sounds named (the page's collection `drumnames1`, kept as
`~/diags/bitcomposer/idiom/drums/heard-drums.json` with `drum_score.py`
and `drum_namer.py` beside it); four set aside where the voice plays
several drums in the clip and the listener named the clip as a whole
(Boss Battle, Cotton Island, Final Battle, Stage 9), a flaw of the page,
which marked the sample's own hits but asked about "the sound". Of the
thirty-six, he named a kick, snare or hat in fourteen, a tom in four, a
cymbal in three, and "something else" in fifteen, with notes: bells, a
whistle, a horn, an alarm, a shaker, a washboard, a cowbell, electronic
noises, and one silence (the Noiseless Toughness rip mutes the voice; the
sample is one empty block). So a third of the samples drawn as drums are
no drums: the drum role takes any voice playing one or two pitches a
sample, sound effects and one-note instruments with it. The namer as it
was agreed with his kicks, snares and hats in 64 % by the sound and 43 %
by how the sample is played; it refused snares with a little pitch
(three), had no tom and no cymbal, and called nine of his non-drums hats.
The rule is rewritten (`drums.name`, the play no longer consulted): a low
sound is a kick, a tom (centroid under 500 Hz, ringing past a thud) or a
deep snare; noise with a body a snare, or a rim when over within 50 ms;
bodiless noise a closed hat, a gated snare when dark, an open hat or a
cymbal by its ring; a plainly pitched tone held or looped no drum
("none"); a pitched tone with a body a snare. Against the generator's own
kits, whose names are known: 50 of 51 (the chip crash, a bright 0.18 s
burst, reads as a hat). Against the ear: **his kicks, snares and hats
agreed in 12 of 14 (86 %)**, the four toms all, one cymbal of three (the
other two are bright bursts ringing under a quarter second, hats by
every measure), and of his fifteen non-drums the namer says other or
none for six, hat for five, snare for two, tom for one; over all
thirty-six classes agree in 22 (61 %). The 85 % criterion is met on the
set the rule was built from, so a second draw is needed before it
counts. `PIECES` gains tom and cymbal (the packs' toms and crashes named
as such, the figures' letters t and c). Open: a second draw, by the ear's
classes; the drum role sweeping in sound effects; a bright short burst
the ear calls a cymbal and the measures a hat; a "shaker" and a "rim"
class if the kit wants them.

## Exit criteria, with the tolerances proposed before scoring

- **Tempo:** the read tempo equals the written one, or exactly twice or
  half it (which is said), in 95 % of covered songs read on a grid;
  the rest listed with their class.
- **Loop:** the end within a beat and the start within a bar of the
  decode's, in 90 % of covered songs with a loop; the rest listed.
- **Notes:** 98 % of written notes matched by a decoded note within 20 ms;
  of those, 99 % agreeing in pitch class after one constant offset per
  sample; every sample whose offset is not a whole number of semitones
  listed (the tuning check).
- **Key and mode (known answers):** the tonic right in 95 % and the mode in
  90 % across the modes; on the games, the change reported, no target.
- **Chord changes (the six held-out songs):** F1 of 0.75 or better and a
  rate ratio between 0.8 and 1.25 at the level the development set chose.
- **The tune (ten songs):** the reader's voice agrees with the marked one
  in 85 % of bars where a tune is marked.
- **Drums (forty samples):** 85 % agreement on kick, snare and hat; the
  matrix recorded whatever it says.
- **Every reader scored,** the numbers in this file; **what is excluded
  reported per game,** the free-time songs measured; **the shared-or-own
  table re-read** and the hypothesis kept or dropped on it.

A tolerance missed is not a reason to lower it: the miss is recorded and
the reader fixed, or the plan says why the reader cannot be fixed yet and
what that costs the tables that depend on it.

## What the listener is asked for

About an hour, in three sittings if preferred: the chord-change taps
(twelve songs, each once through), the tune marks (ten songs), the drum
names (forty short clips). Each page saves as it goes, as the earlier
pages did. Nothing else in the phase needs an ear.

## Open questions

- Which songs the independent decode converts cleanly, and what its shell
  exposes beyond MIDI (the parsed events would give loop points and track
  order directly).
- Answered in step 4: the bar is the harmony's counting level, read from
  the bass's root and the chordal set; the half bar only arises in Kefka,
  which may be its bar phase.
- What to do with the 222 songs the beat reader follows loosely: scored
  separately, since a loose grid rounds nothing.
- How much of the drum namer's rule survives the forty.
- Whether the free-time songs are a vocabulary of their own, which phase 3
  decides from what step 5 measures.
