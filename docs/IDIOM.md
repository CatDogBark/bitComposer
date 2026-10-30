# The idiom: the generator learns to write from the readings

Agreed 2026-10-20. `TRANSLATOR.md` carried the translator through its
stages: the readings (1), a thin pack (2), the PACKS panel (5), and the
vocabulary counted (4). What those counts said about the generator's own
writing is the reason for this plan, which takes over from stage 3's
second half (the generator writes voices) and stage 4's (the vocabulary
the generator draws from). It is laid out in phases, each planned in
detail only when it is reached, from what the one before found.

## What the counts say about the generator

Stage 2 showed that a pack carries a game's sound: the samples, the
envelopes, the echo. The gap is the writing. Stage 4 measured the writing
of Final Fantasy VI, of 39 games, and of the generator, with the same
readers, and the generator's distance from FFVI turned out to be its
distance from SNES music as a whole, in the same places. Those places are
not weights; they are the assumptions the writing is built on, which are a
textbook's, where the games' are not:

| the generator writes | the readings show |
|---|---|
| Harmony: four-chord loops from a table (`theory.py`), a chord a bar or two, the cadences of the book | half of FFVI's parts sit on one or two chords, the rest are each part's own sequence; the chord moves between I and IV and to the relative minor far more than from V to I, in the natural minor; the cadence lives at the loop (V to I in 18 % of loops, 4 % of parts) |
| Phrases: a sentence or a period (`melody.py`): the answer in the same rhythm, the repeat, the cadence, the peak placed late | three four-bar phrases in four are new against the one before, 7 % answered, 6 % repeated (the generator answers 28 %); the peak falls in the first quarter in 43 %; the arch is one phrase in twenty |
| Values: four rows a beat (`pattern.py`), templates in quarters and eighths; nothing can fall on a triplet | the melody 32 % sixteenths, 8 % triplet eighths, a quarter of its notes detached; 29 % of onsets off the eighths (the generator: 70 to 75 % of melody notes a beat or longer, none on a triplet, every note held to the next) |
| Bass: steady, walking, octave, drone, riff | 4.5 onsets a bar, a step in 24 % of its moves, a passing tone in 23 % of its bars, an octave in 7 % (the generator half the onsets and 18 to 30 % octaves) |
| Voicing: full or thin, power chords by habit | bare fifths in 24 % of spans (the generator 45 %), the chord spread over 28 semitones (21 and 14), the melody at the chord's top |
| Arrangement: an arp in every song, a counter-line by chance | an arp in 5 songs of 69, a counter-line in 51; the tune passes between voices |
| Drums: grooves from a library, one figure in half the songs | a hat keeping time and a cymbal on the downbeat are the figures many songs share; the rest are each song's own |
| Length: 129 to 160 s once through | 70 s |

So the change is to the grammar, not to its weights: the generator's
writing for SNES packs is to be induced from the readings. The chip and
Genesis palettes keep their path, byte for byte, and the built-in SNES
packs sound as they do until moving them over is chosen.

## Decided (2026-10-20)

- **The writing, not the knobs.** A new way of writing for SNES packs,
  learned from the readings, behind the same `compose_song`; the current
  writing stays for everything else.
- **Tables, not a model.** The vocabulary is conditional tables read from
  the readings (whole-bar rhythms per part, bass and drum figures, chord
  sequences by part, voicings, phrase shapes, form, arrangement) that the
  writing draws from with the song's seed. Every table can be printed and
  argued with. A learned sequence model was considered and set aside: it
  needs a dependency the player cannot carry, 1836 songs is few enough to
  memorise tunes, and nothing in it can be read, tuned by rule or checked
  by ear.
- **The idiom, never a tune.** Rhythms, figures, chord sequences and
  voicings are taken as patterns; the melody only as statistics (its moves,
  values, contours, ends and relations). A test fails any generated
  four-bar phrase whose rhythm and intervals match a game's.
- **Match the spread, not the mean.** The games are a distribution, and a
  wide one: most figures are one song's own. The measure of the writing is
  that twenty songs differ from each other as twenty of the game's do, each
  committed to its own figures, not that each matches the average. Variety
  is measured beside fidelity, and the whole of a table is drawn from, with
  the seed, never its likeliest row.
- **Ground truth before interpretation.** No reader's output becomes a
  table until that reader is scored on something independent of it, on
  songs it was not tuned on.
- **One measurement path.** A generated song is read by the same readers
  as a decoded one, from the same kind of score, so a difference in a table
  is the music's and not the reader's.
- **Held-out likelihood is the referee.** Which shape a table takes (the
  half bar or the bar, patterns weighted by songs or by bars, one table for
  all games or one a game) is decided by which predicts songs it was not
  fitted on better, not by which tells the better story.
- **The score of voices comes before the tables** (stage 3's
  representation, phase 2): it gives one measurement path, frees the
  writing from the sixteen-row bar (the converter already places a note at
  any time), and makes substitution tests possible.
- **One shared vocabulary with per-game weights** is the working
  hypothesis, as stage 4 recommended, to be tested in phase 3 rather than
  assumed: the rows that came out shared across the games are the ones the
  chord reader interprets, and the rows that came out a game's own are the
  ones the notes show directly.
- Voices are the arrangement's, and MPTM is on hold, as `TRANSLATOR.md`
  records.

## What the counts cannot yet be trusted for

Stage 4's own "what looks wrong", gathered (the detail is there):

- The chord reader changes chord every beat over half the time, so the
  chord rate and the moves with the shape kept are partly its flicker; the
  half bar was chosen as the counting level by eye.
- The key reader knows major and minor only: a modal tune is read as its
  parent key, and every numeral in that song shifts with it.
- The form reader's part starts agree with the marked ones at recall 0.73
  and precision 0.65; anything that turns on a part's last bar is rough.
- The drum namer's thresholds were set on the samples it is scored on.
- The tune passes between voices, and the melody's counts are one
  voice's.
- 367 of 1836 songs are left out (free time, mostly unfit), the ambient and
  cinematic music among them, and the vocabulary so far does not know it.
- Two measures were taken differently on the two sides of the generator
  comparison (a detached note; the loudness the chord shapes depend on).

## Ground truth

- **An independent decode.** VGMTrans reads many SNES drivers' sequence
  data (AKAO, N-SPC and others) to MIDI: the written durations and rests,
  the tempo command, the loop points, the track order; nothing of it shared
  with the emulator or the readers. On the games it reads, the beat, loop,
  length and tune readings are checked against it. A program on the
  machine, for checking only, never shipped.
- **Songs with known answers.** The generator writes Dorian, Mixolydian and
  Phrygian scales, known chords, known forms and named drums; rendered and
  read back, they score each reader. A floor, since they are plainer than
  the games, not a pass.
- **The ear, for what only an ear settles,** each a page like the Ear
  Check and Form Check pages: when the harmony changes (tapped; no chord
  need be named), which voice carries the tune (the voices soloed), and
  what a drum sound is (samples soloed and named kick, snare, hat or other,
  drawn at random across the games and held out from the namer's tuning).
  The beat (43 songs) and the form (36) are marked already. The marks stay
  on the owner's machine with the readings; the repository holds the
  scores.

## The vocabulary's shape

What the tables are and what each is conditioned on, provisionally; phase
3 settles each by held-out likelihood. The tables as a pack keeps them
today, each with what it counts, what conditions it and what the writers
do with it, are listed in [idiom/VOCABULARY.md](idiom/VOCABULARY.md);
that list is kept current when a table is added or its counting changes.

- **Form:** the parts (how many, how long, which come back), where the song
  loops and what the loop lands on.
- **Harmony:** the chord sequence through a part by degree, conditioned on
  where in the part it falls (its first bar, its middle, its last) and at
  the loop; how often the chord changes; the voicing per role (which tones
  sound, the spread, the lowest tone).
- **Rhythm:** whole-bar patterns per part, by meter and tempo band,
  weighted by the songs that play them; the values within them (sixteenths,
  triplets, notes cut short).
- **Bass:** figures, the rhythm with each note's chord tone, conditioned on
  this chord and the next.
- **Drums:** figures per piece (kick, snare, hat, cymbal), a song drawing
  its few and keeping them.
- **Melody:** values and moves conditioned on the beat position and the
  chord tone, under phrase targets: the contour, where the peak falls, the
  range, the first and end note against key and chord, and the relation to
  the phrase before (new, repeated, answered, moved).
- **Arrangement:** which parts a song has (a counter-line in most, an arp in
  few), how many voices, each part's register, the tune passing between
  voices.
- **Weights:** per game over the shared tables where the hypothesis holds;
  a game's own table where it does not.

## How the writing is judged

1. **Held-out measures.** Tables fitted on some measures must move the
   others toward the game's; matching the fitted ones is tautological.
2. **The nearest game.** Each game as a vector of the headline numbers;
   songs written with a game's vocabulary should fall nearest that game
   more often than any other, and with another game's, nearest it.
3. **Substitution.** One part of a converted song replaced by the
   generator's writing for that song's chords and form, the rest as the
   game played it; measured, and listened to.
4. **Blind pairs.** A song of the game and a song written with its
   vocabulary, both through the SNES chip's sound: which is the game's. The
   share picked right, over versions.
5. **Variety.** The spread of twenty seeds against the spread of twenty of
   the game's songs, and a song's commitment to its own figures.
6. **No tune copied.** The four-bar check above, in the test suite.

## The phases

Each is planned in detail when reached, from what the one before found;
its exit criteria are the gate to the next.

1. [The readers](idiom/phase-1-readers.md): ground truth, the readers
   scored and fixed, the counts run again.
2. [The score of voices](idiom/phase-2-score.md): one representation for
   decoded and generated songs, through one back end and one set of
   readers.
3. [The tables](idiom/phase-3-tables.md): the vocabulary read from the
   readings, each table's shape settled by held-out likelihood; the pack's
   second format drafted.
4. [The writing](idiom/phase-4-writing.md): the generator writes for SNES
   packs from the tables, one part at a time, each judged before the next.
5. [Packs](idiom/phase-5-packs.md): the second pack format in the product,
   the PACKS panel importing into it, the built-in SNES packs if chosen.

## Rules of evidence

- A measure is defined, and what it means written down, before the
  generator's number for it is looked at.
- What is left out of a count is said, with how much, every time.
- A threshold or a table is judged on songs it was not fitted on.
- Both sides of any comparison go through the same path.
- A finding only a reader can see (a chord, a key, a part) is held more
  lightly than one the notes show directly (an onset, a length, a drum's
  sound), until the reader is scored.
- The ear settles what the readers cannot, and every rule change is
  rechecked against everything heard so far.
- The counts so far are a starting point, not a final truth; the tests and
  the data will change as the work teaches, and the changes are recorded.
- A writer is not patched past what its vocabulary says. When the
  written songs miss something the games do, the first question is
  whether the vocabulary has a word for it. If it does not (the theme, a
  part's second voice, the share of a tune's beats on the chord), the
  answer is a new unit counted from the readings and kept as a table,
  never a weight, a constant or a rule in the writer that steers a draw
  toward the effect. Where a word exists and the writer still misses, the
  fault is in how the tables are drawn from, and that is fixed as a fault
  (the smoothing that mixed every part's registers, the floor's invented
  bars). Where the choice between patching an existing vocabulary beyond
  what it was counted to say and counting a new one is open, it is put to
  the owner first and decided together; it is not made in the code
  (decided 2026-10-23, after the hook: weighting the urn's "earlier"
  draws toward the opening would have moved the number without naming
  the thing). The rules still standing are listed in
  [idiom/rules-to-words.md](idiom/rules-to-words.md), to be replaced in
  the owner's order.
