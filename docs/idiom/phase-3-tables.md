# Phase 3: the tables

Planned in outline (2026-10-20), in detail 2026-10-22 (below the outline).
See `../IDIOM.md`.

## Goal

The vocabulary read from the readings as tables the writing can draw from,
each table's shape chosen by how well it predicts songs it was not fitted
on, and the pack's second format drafted to hold them.

## Starts from

The readers as phase 1 leaves them; the readings of the 39 games read
again with them; the stage 4 counts as the first draft of what to count;
the score of voices (phase 2) as what the tables describe.

## Work, provisionally

In the order of least to most dependence on the readers: rhythm and values;
bass figures; drum figures by piece; voicings; harmony by part (after
phase 1's chord and mode fixes); phrases and form; arrangement.

For each table:

- **The unit:** a whole bar, a half bar, an event.
- **The conditioning:** the part, the meter, the tempo band, the position
  in the part, this chord and the next, the beat position and chord tone.
- **The weighting:** by the songs that play a pattern, not the bars (one
  song's ostinato is one vote).
- **The test:** held-out likelihood against the simpler and the richer
  alternative, and one shared table against one a game, the same way; the
  shape that predicts unseen songs best is kept, and the numbers are
  recorded.
- **The reading:** each table printed and read as music, so a table that
  predicts well but says something no composer would is caught.

Then the pack's second format, `bitcomposer_pack: 2`, holding the tables
beside the voices, with a pack written from FFVI and read back; and the
reference set for the tune-copy check (the games' four-bar phrases as
rhythm and intervals, kept on the machine).

## Produces

The tables for FFVI and for the 39 games; the likelihood table that
justifies each shape; the format 2 draft and a pack in it; the tune-copy
reference.

## Exit criteria

- Every table's shape recorded with its held-out likelihood against its
  alternatives.
- Shared or per game decided per table from the same numbers.
- A format 2 pack written from a game and read back; format 1 still read.
- The tables, printed, read as the music does to an ear that knows it.

## Open questions

- How fine the conditioning can go before the tables thin out: FFVI's 67
  songs against the 39 games' 1469.
- How per-game weights combine with shared tables in the draw.
- Whether the melody's statistics are enough to write from, or a
  phrase-level table of contours and relations is needed with them.
- What the free-time songs contribute, and whether they are a vocabulary
  of their own.
- Where a taste correction lives (`../TRANSLATOR.md`: only in the pack),
  and in what form when the pack is tables.

## Planned in detail (2026-10-21)

What phases 1 and 2 changed about this phase: the readers are measured, so
the line between the tables that can be counted now and the ones that
wait is known; the substitution harness exists, so a table can be heard
in a real song before anything is built on it; and the listener has said
that whole generated songs of the old generator are too much to project
the aim onto, so his ear is spent on one voice in a real song at a time.

### Two things first

- **The drum namer inside the role reader.** A voice whose samples the
  namer calls a drum piece (kick, snare, hat, tom, cymbal) is a drum voice
  however many pitches it plays; today a tom played at several pitches is
  the lowest tonal voice and takes the bass's role (the generator's songs,
  17 of 60). The sample is named once when a reading names its samples,
  from its PCM, and the name kept on the sample the readers see.
- **One readings database.** The 39 games read again with the readers as
  phase 1 leaves them (and the namer above), on Ragnarok, the database
  every table reads from; the product's own database is rebuilt the same
  way when the pack is written.

### The framework, before any table

`translate/tables.py`: a table is outcomes counted under a context, a
tuple of conditioning values, over songs. Each song votes once for each
distinct pattern it plays (one song's ostinato is one vote, as the plan
says). Probabilities are the counts smoothed and backed off to the next
coarser context, so a context seen in few songs leans on the broader one.
A table's score is the mean log-likelihood per unit (a bar, an event) of
the songs it was not fitted on, the games split into the development and
held-out halves by the hash phase 1 used, and the shapes compared for
each table are: the unconditioned; each conditioning proposed; one shared
table against one a game, the per-game table backing off to the shared.
The shape that predicts the unseen songs best is kept and the numbers
recorded here. Drawing from a table with a seed returns from the whole
distribution, never the mode, so what the writer plays stays as varied
as the games (the listener's standing worry), and the between-song spread
of what is drawn is measured beside the fit.

### The tables, in the order of least to most dependence on the readers

1. **Rhythm and values** (the beat and the roles). The unit is a bar's
   onset pattern for one part, the positions exact on the readings'
   twelfth-of-a-beat grid (sixteenths, triplet eighths and sixteenths,
   not the four-character drawing); a bar a part rests in is a pattern.
   Conditionings tried: the part and the meter; the tempo band (the games'
   tertiles); the previous bar's pattern of the same part (a first-order
   chain); the bar's place in its part (first, middle, last: this one
   leans on the form reader and is marked so); whether the chord changes
   in the bar (leans on the chord reader). Values: the melody's note
   lengths and how much of each sounds (detached or held), by position.
   Loose songs are counted apart and their share said.
2. **Bass figures.** The unit is the bass's bar as rhythm.py draws it:
   positions, the chord tone of each note (root, third, fifth, seventh,
   another), the octave mark. Conditionings: meter and tempo band; this
   bar's chord shape (major, minor, bare fifth) and whether the next bar
   changes chord; the song's own bass style, read from its bars (walking,
   pumping a root, octaves), as a conditioning against a per-song mixture
   (an open question below); the bass's register against the key as a
   habit per game. **Acceptance by ear:** a bass written from the FFVI
   table into Terra and two or three other FFVI songs, in place of theirs,
   heard against the originals; Terra with the old generator's bass was
   the listener's "awful", so this is the first test the new music takes.
3. **Drum figures by piece.** The unit is the bar's figure, each piece's
   positions, the pieces named by their sound. Conditionings: meter and
   tempo band; the song's density tier (hits a bar); the kit the song has
   (which pieces at all); the last bar of a part for fills (form). Acceptance
   as the bass's: a kit written from the table into a real song.
4. **Voicings** (vocab.py's counts, made tables): which chord tones sound,
   how spread, which part takes which tone, the inversion; conditioned on
   the chord's shape and the part; shared against per game.
5. **Harmony by part**, after the key check by ear: progressions as degree
   sequences through a part (phrases.py's), cadences and what the loop
   returns on, the harmonic rhythm from the bar-by-bar chord reader;
   conditioned on the mode (the scale reader's name, folded where the
   numbers say to) and the part's place in the form. **Gate:** a dozen
   songs with the tonic named by ear, the scale reader scored on them,
   before these tables are trusted.
6. **Phrases and form:** the melody's contours and relations, phrase
   lengths, the form's letters and lengths; these lean on the form
   reader's level, which the generator's songs (precision 0.46 on their
   sections) and the ear (0.69 to 0.80) both say is unsettled, so last,
   and with a short form-level ear round if the numbers call for one.
7. **Arrangement:** which parts play in which bars, voices a song, echo
   voices and doublings, the share of songs with no stated harmony and of
   songs without drums; mostly per game, read from the roles.

### The pack's second format, and the reference set

`bitcomposer_pack: 2` holds the tables beside the voices; a pack is written
from FFVI and read back; format 1 is still read. The tune-copy reference
(the games' four-bar phrases as rhythm and intervals) is kept on the
machine, never in the repository, for phase 4's check that the generator
writes the idiom and never a tune.

### The listening instrument

A Substitution Check page: a song plays, and each of its voices can be
switched between the original and the substituted rendering while it
plays, several songs on one page, so the listener compares one voice at
a time inside the real music (his suggestion). Each voice's two versions
are rendered as separate audio stems, aligned, and the page mixes them.
Built when the bass table has a writer to hear.

### Exit criteria

The outline's four, and: the bass and the drums written from their tables
pass the listener's ear in substitution (not mistaken for the generator's
old parts; "belongs" or "nearly"), and the key check by ear is done before
the harmony tables count.

### Open questions, added

- A song's own habit (its bass style, its density tier) as a conditioning
  value against a per-song mixture of patterns: which predicts held-out
  songs better, and which the writer can use.
- Whether the previous bar's pattern (a chain) or the bar's place in the
  part predicts rhythms better, and what each costs in table size.

## Record

### The drum namer inside the role reader (2026-10-21)

A reading names each sample by its sound as it names the samples
(`events.of_notes`: drums.measure on the SNES chip's interpolation of the
PCM at the voice's median pitch, then drums.name) and keeps the name on
the sample (`Sample.piece`; store schema 5, translator version 8). The
role reader's drum rule, now first: a voice whose notes sound on
drum-named samples (kick, snare, hat, tom, cymbal; BY_SOUND 0.8 of them)
and plays each sample at FEW_PITCHES (4) or fewer is a drum voice; one on
kick and tom samples only (LOW_PIECES) is a drum voice by sound only where
it sounds on under SPARSE (0.5) of the beats, as fills do, and a voice
playing on is left to the other rules, since a bass on a low sample passes
for a tom. What the two guards cost to learn: the first version made 728
bass voices drums and lost Psycho Spin's bass, its three chord changes
with it (chord check held-out 0.83 to 0.67); the pitch cap left 224; the
playing-on guard 128.

Against the phase 1 readings (attempt 13), 507 of 12,453 voice roles
changed. Bass to drums 128: 42 of them play throughout, kits on kick,
snare and tom samples the old rule had as the bass (Star Fox, Uniracers,
Lufia II's battles, Mega Man X's Chill Penguin), each song now with
another voice as its bass; the other 86 are sparse kick and tom fills.
Drums to bass 45, accompaniment to drums 52, harmony to drums 45, drums
to accompaniment 40, drums to harmony 37.

The checks: the tune's carrier 424 of 475 marked bars (89 %, unchanged);
chords held-out mean F1 0.83, five of six songs at 0.75 or better,
development 0.65 and four of six (both as phase 1 left them); bar phase
held-out 77 % (76 before); beats 40 of 41. The generator's known answers
through the score path (60 songs, seed 1): the melody channel read as the
melody in 60 of 60, the bass right in 58 (39 before), the drum channels
read as drums 341 of 341 (the toms no longer take the bass's role); the
beat still read at half the tempo in 57 (phase 2's finding, untouched).

### One readings database (2026-10-21)

All 39 games read again on Ragnarok with the readers as above:
`~/diags/bitcomposer/idiom/phase3/readings.db`, 1,836 songs, translator
version 8, notes cache key 5b1140535b27. Every table below counts from it.

### The framework (2026-10-21)

`translate/tables.py` as planned (a Table of outcomes under contexts,
songs voting, backoff to the coarser context, held-out bits a unit, draws
from the whole distribution, the spread of draws measured), with four
things the first comparisons on the rhythm table forced:

- **A floor model.** The even share below the root is not a distribution:
  every pattern never counted gets the whole unseen slot, and a quarter of
  the held-out bars are patterns no development song played (80 % of the
  distinct patterns are one song's). So a floor can be a model: the bar as
  a chain of beat cells (`rhythm.BarCells`, each beat's onsets conditioned
  on the part, the meter, the beat and the cell before it), under which a
  bar never counted whole still has a likelihood and can be drawn. A
  table over a floor backs off no lower than what the floor covers (the
  part and the meter): passing through the pooled root cost 0.4 bits.
- **Votes by shares.** Beside the plan's one vote a distinct outcome a
  song, a song can vote its bars' shares (summing to one a song, so an
  ostinato is still at most one vote): shares predict the held-out bars
  better (−10.48 against −10.76 bits a bar for the chosen shape under
  Witten-Bell) and keep how much a song repeats itself.
- **Absolute discounting.** With nearly as many distinct patterns as
  votes, Witten-Bell gives half the mass to the coarser level at every
  level. A discount of 0.75 a vote scores within 0.05 bits of it and its
  draws are far more like songs (below).
- **A split by song.** A held-out game's per-game context backs off whole,
  so the shared-against-per-game question is asked with the songs split
  within each game (`half_of`), the games' split kept for everything else.

### Rhythm (2026-10-21)

152,029 bars of seven parts in 1,562 songs (213 in free time and 61 mostly
silent left out), the games split: 68,710 development, 83,319 held-out.
Held-out bits a bar, the cell floor under every shape (covers the part
and the meter), share votes:

| shape | Witten-Bell | discount 0.75 | draws: distinct a song / ostinato share (real 7.5 / 0.50) |
|---|---|---|---|
| the floor alone | −11.81 | −11.81 | 22.7 / 0.16 |
| part+meter | −11.53 | −11.32 | 17.4 / 0.23 |
| part+meter+tempo | −11.44 | −11.45 | |
| part+meter+chord (changes in the bar) | −11.44 | −11.49 | |
| part+meter+place (in its part) | −11.45 | −11.50 | |
| **part+meter+previous** (the bar before) | −10.48 | **−10.53** | 12.8 / 0.36 |
| part+meter+previous+chord | | −10.58 | 10.0 / 0.46 |
| part+meter+previous+place | | −10.58 | 9.7 / 0.46 |
| part+meter+previous+tempo | | −10.61 | 10.2 / 0.45 |

Song votes (the plan's) under Witten-Bell: part+meter −11.79, with the
previous bar −10.76. A discount of 1.0: −10.54. By song within the games
(76,791 / 75,238): part+meter+previous −10.26, the same a game −10.27, so
the rhythm table is shared, not a game's. **Kept:** the part, the meter
and the previous bar's pattern over the cell floor, share votes, discount
0.75: 1.28 bits a bar over the floor, 0.79 over the inventory without the
chain. Bits by part: bass −9.9, harmony −3.5, accompaniment −10.5, arp
−12.7, counter −11.1, melody −10.7, drums −11.5 (the arp and the drums
vary most; the drums' bars are every piece's onsets together, the drum
table of its own counts them by piece). The tempo band, the chord change
and the place in the part add nothing to the likelihood once the chain
is there, though each makes the draws more like songs (10 distinct a
song, ostinato 0.46). **Open:** the draws are still more varied than
songs (12.8 distinct a song against 7.5; the ostinato 0.36 of the bars
against 0.50): the song's own habit, drawn once a song, is the plan's
open question, tested first on the values table below.

### Values (2026-10-21)

Whether a note of the melody's or the counter's line is held (SHORT of
the way to the next note or more) or detached, 254,940 notes. The note's
value, its place in the bar, its beat, the meter and the tempo predict
nothing on held-out games (each a little below the unconditioned −0.83
bits a note under Witten-Bell; the value's 456 contexts fit the
development games' habits). The articulation before it helps (+0.10),
and by song within the games the game helps most: (none) −0.86, game
−0.71, part+value+previous −0.69, part+value+previous+game −0.61.
Articulation is a habit of the game and the song, not of the note; the
writer draws it once a song. Tested next: the song's habit (its share of
held notes, in thirds) as a conditioning, and a table of the habits
themselves by game.

### Bass figures (2026-10-21)

The bass's bar as its positions with the chord tone of each onset's
lowest note (R root, r a root an octave or more over the bar's lowest, 3,
5, 7, s a sus chord's tone, + another tone, ? no chord fits), 33,320
bars. Over its 190,943 onsets the marks are R 0.44, + 0.19, 5 0.15, 3
0.07, r 0.07, 7 0.05, s 0.02; of consecutive bars 23 % keep the figure,
20 % keep the rhythm and change marks (passing tones, or the chord
reader's misses), 57 % change rhythm; a song plays 10.9 distinct figures
against 6.9 distinct rhythms. Held-out bits a bar, the cell floor
(keeping marks), share votes, discount 0.75: the floor −21.92, part+meter
−21.48, with the chord's shape −21.53, the chord change in the bar −21.52
or the next −21.51, the tempo −21.52; with the previous figure −21.00,
and nothing on top of it helps (shape −21.02, chord −21.02, tempo −21.04,
next −21.05) though each pulls the draws toward the songs (15 distinct a
song, ostinato 0.36; real 10.4 / 0.39). By song within the games, a game's
own table: −21.63 against −21.61 shared. **Kept:** part, meter, the
previous figure, shared. The marks make the figures eleven bits a bar
dearer than the bare rhythms (−9.9), a fifth of it the chord reader's
noise at most; what the figures are worth is settled by the ear, in
Terra.

### Habits (2026-10-21)

The plan's open question, a song's own habit as a conditioning, has one
answer for the three tables: it does not raise the likelihood, and it is
what makes the draws like songs. A habit is read from the song's own
bars (the values: its share of held notes in thirds; rhythm: its onsets a
bar in three tiers and its share of bars repeating the one before in
thirds; bass: the density tier, its tones as roots / root-fifth / walking
by the share of its marks on R r 5, and octaves) and a writer draws it
once a song from the habits table, then the bars under it.

| table | without the habit | with it | the habit's own table (bits a song and part, by song within games) | draws: distinct / ostinato (real) |
|---|---|---|---|---|
| values (held or detached) | −0.725 (part+value+previous) | **−0.449** (part+habit+previous) | −0.99 by game, −1.18 by part alone | 0.87 (0.88) |
| rhythm | −10.526 | −10.521 | −2.66 by part and game, −2.68 by part | 10.3 / 0.47 (7.5 / 0.50), from 12.8 / 0.36 |
| bass | −21.002 | −21.045 | −3.00 by part, −3.09 by game (the game hurts) | 16.8 / 0.33 (10.4 / 0.39), from 18.6 / 0.27 |

The articulation habit is the exception: it carries a quarter of a bit a
note, and is a game's (−0.99 against −1.18). The rhythm and bass habits
are drawn by part, not by game. **Kept:** every table conditioned on
its habit, the habit drawn once a song.

### Drum figures by piece (2026-10-21)

The drums' bar as each hit's position and piece (K S h t c, o a sample
the reading named no drum; the namer's names from the readings), 26,722
bars of 1,078 songs. Held-out bits a bar, the cell floor, share votes,
discount 0.75: the floor −30.42, part+meter −30.11, with the kit (which
pieces the song strikes at all) −30.07, the habit −30.10, the tempo
−30.23, the place in the part −30.26; with the previous figure −29.51,
and the place on top of it −29.46 (fills land on a part's last bar: the
one addition that helps a chain anywhere), the habit −29.51, the kit
−29.52, the tempo −29.55. By song within the games, a game's own table
−28.55 against −28.56 shared; the drum habits by game −2.52 against
−2.58. Draws: 13.6 distinct a song, ostinato 0.43 with the place (real
8.0 / 0.51), 18.3 / 0.31 without. **Kept:** part, meter, the previous
figure and the place in the part, shared, the habit drawn once a song.

### The song's own mixture (2026-10-21)

The plan's open question, settled: a song is loyal to its own figures in
a way no bar's context captures, and the habit conditioning above only
nudged the draws. `tables.Cache` sets the song's own outcomes as a
mixture over a table: at each bar the song repeats the one before
(same), returns to one it played earlier (earlier, each by how often so
far) or draws a new one from the table; the three shares are a table of
their own under the part and the habit (the bass: same 0.26, earlier
0.32, new 0.42, much alike across habits). Scored song by song in order
on the held-out games (the same split, share votes, discount 0.75, the
cell floor), the mixture over the chosen shape against the shape alone:

| table | the table alone | as the song's mixture | draws: distinct a song / ostinato (real) |
|---|---|---|---|
| rhythm (part+meter+previous) | −10.53 | **−6.78** | 7.0 / 0.46 (7.5 / 0.50), from 12.8 / 0.36 |
| bass figures (part+meter+previous) | −21.00 | **−13.12** | 9.1 / 0.40 (10.4 / 0.39), from 18.6 / 0.27 |
| drum figures (part+meter+previous) | −29.51 | **−12.79** | 9.1 / 0.41 (8.0 / 0.51), from 18.3 / 0.31 |

The mixture over part+meter alone is within 0.03 to 0.10 bits of it, so
the previous-bar chain matters little once the song remembers itself.
**Kept:** every figure table is drawn as the song's mixture; the writer
runs the urn.

### The bass written into Terra (2026-10-21)

`translate/writer/` and `tools/table_bass.py`: the song's bass voice
replaced by one written from the bass table fitted on every other song
(the song never votes for its own bars), the habit the song's own, the
figures drawn as the mixture, each mark a chord tone in the song's own
register on its own bass sample, the rest of the song as decoded. Three
versions before one worth hearing, each a lesson: the table's draws
alone gave a bass with no two bars alike (the mixture fixed it); the
mixture with the habit last in the chain locked onto rests and lone
roots, since a rare context backed off to the pooled inventory where
intros and rest bars weigh most (the habit now comes before the previous
bar, so the backoff lands in the habit's own inventory); and the song's
own rests are kept, a playing bar never drawing a rest (which bars the
bass plays is the arrangement table's question). A new figure must sit
on the song's own grid. A fourth lesson came from the listener's first
minute with the page: the written voice took its volume and envelope
from the voice's first note, and Terra fades its bass in, so the written
line played 23 dB under the original and read as no bass at all; the
voice's usual settings (its most common sample, volume, envelope and
echo) are taken now, and the written stems measure within half a decibel
of the originals. The listener's second minute: Terra's written bass
"holds and then spazzes out" from 25 s on, rapid runs with thirds and
passing tones, and plays over the intro the song's own bass only fades
into. Every run was a bar no song ever played, invented by the cell
floor (bars 17, 25, 41, 49, 56, 57 of 74), and the one real dense bar
came from a song nothing like Terra, while Terra's own habit inventory
(189 figures, 43 song-shares) is peaked on quarter and eighth roots. So
the writer now plays only bars some song played (the floor serves the
likelihood, not the writer), no denser than DENSER (1.5) times the song's
own median a bar or its busiest bar, and each written note takes the
volume of the song's own nearest bass note, so a fade-in stays a
fade-in. Terra's bass came back as ten figures, all roots: quarter
roots, eighth roots, a root on the one, a root with its pickup.
**The goal, restated for the listener:** not Terra's line, a bass that
could belong in Terra. His third minute: "nearly there", one "burst then
pause skip" at 32 s: a bar with a sixteenth pickup (11/4) in a bass that
moves in quarters and triplets, then a bar with one note on beat two in a
bass that strikes every downbeat. Both are bars other songs play; neither
is in Terra's manner. So the writer now reads the song's own manner for
the part (`writer.Manner`) and holds a new figure to it: its strikes a
bar between SPARSER (0.5) and DENSER (1.5) times the song's median (or
up to its busiest bar); the downbeat struck where the song's bass strikes
it in DOWNBEAT (0.9) of its bars; only the subdivisions the song's bass
uses (its feel: Terra's {1, 2, 3}). Terra came back as seven figures,
quarter roots and eighth roots mostly, a root-third-fifth bar twice.
These three are what the generator's bass habit should carry beside
density and tones: a feel and a downbeat loyalty, drawn once a song
(phase 4).

His fourth round: "the bass has no section awareness, it does whatever
it wants through the four beats in each part with no real throughline,
free-forming while fitting each bar in isolation." That is the model: a
bar drawn at a time, the song's mixture remembering which figures but
not where it is. Measured on the readings' 1,324 basses: 63 % of bars
sit in a span repeating a rhythm (marks dropped) with a period of one,
two or four bars, spans 6.6 bars long on average (by exact figure only
41 %: a walking bass keeps its rhythm and moves its tones), and a new
span's rhythm is one an earlier span had 35 % of the time, never the one
just before (by construction). Terra's own bass: four bars of one
figure, forty-eight alternating two, twelve of one, then bits. So the
writer reads the song's own spans and writes a pattern a span: an earlier
span's pattern with that 35 % chance, else as many new figures as the
period, their rhythms differing from one another and from the pattern
before, held through the span (exactly where the song's own figures
repeat exactly; bar by bar with the pattern's rhythm where only the
rhythm repeats, so the tones move). The first try drew the same figure
twice for Terra's two-bar span and the song came out as one figure for
71 bars; the differing-rhythms rule fixed it. Terra now: four bars of
quarter roots, forty-eight alternating eighth roots with a syncopated
root figure, nineteen of a root-third-fifth, the rests kept. For the
generator (phase 4) the spans come from the form reader's sections and a
table of periods and span lengths by habit, not from the song itself.

**Terra belongs** (the listener, 2026-10-22, the fifth version). His
Locke: "crowding out the rest of the song, jumping around, covering the
melody; the voice sounds right." Measured: Locke's own bass strikes 5 a
bar (mean 6.9), the written 8 (mean 9.6), seven of its last eight bars
sixteenth bars of 16 strikes, all on one tone (sixteen fifths in a row)
and the recurring pattern opening on an octave-up root Locke never
plays; no register collision (the melody's floor 58, the written bass's
top 50). The density ceiling's "or its busiest bar" clause had let one
rolled 21-strike bar license sixteenths everywhere, and the manner knew
nothing of tones. Three rounds: (1) the ceiling from the typical bar and
the manner extended to tones (octave-up roots only where the song plays
them, as many different tones a bar as its own bars have, the roots and
fifths' share within its own range, a one-tone bar of PEDAL strikes
only where PEDAL_SHARE of its own such bars are), after which Locke
thinned to two-strike bars (half the median is too loose for a walking
bass); (2) the strikes a bar from the middle half of the song's own bars
widened by SLACK, after which one eight-strike figure heavy in passing
tones came back nine times where Locke's second half changes every bar;
(3) the roots' share held like the anchors', and a bar in no span must
change its rhythm from the bar before. Locke now: roots 56 % (own 45),
passing tones 21 (21), fifths 14 (21), thirds 8 (13); three- and
eight-strike bars; no bar repeating the one before. Terra under the same
rules: four bars of a five-strike root figure, the forty-eight-bar
alternation, then eighteen bars of a six-strike pedal on the fifth,
which Terra's own bass licenses (its intro bars are thirds and it has
bars of fifths near its end): for the ear.

Locke still off: "jumping around, doesn't know it's an organ, short
abrasive notes; it understands bars, it's the choice within the bar
given the instrument." The readings have two bass voices in Locke:
voice 7, 89 notes about a beat long on a one-shot sample, the plucked
line, moving by step; and voice 3, 207 notes of 0.15 beats on a looped,
sustaining tone, a blip at the line's attacks and, where the line rests
(its first eight bars), a rhythm of its own. The tool had taken the bass
voice with the most notes, the blip layer, read the manner from both
voices merged, and written a walking line in eighths onto the sustaining
tone (the "organ") while the real line played on underneath: two basses
at once. And each tone was placed in a fixed octave, so the written line
leapt (thirds 12 %, fourths and fifths 23 % of its moves; Locke's own 3 %
and 15 %). Now: the line is the bass voice with the longest notes and
the manner is read from it alone; a layer (a bass voice with notes under
TICK beats) has its doubling rebuilt on the written line, the song's own
device (the offsets after an attack that DEVICE of the doubled attacks
have, the same pitch relation, length and sample) and keeps its own
notes elsewhere (Locke: 63 of 89 attacks doubled at the attack itself;
30 blips rebuilt, 75 of its own kept); and each tone goes to the octave
nearest the note before within the register (`writer.place`, REACH an
octave and a third over the floor), so a walking line walks. Locke's
line voice alone reads as "medium root-fifth", rests through most of its
first eight bars, then walks in quarters; the written one follows.
For the generator: a layered bass (a line with an attack layer on a
sustaining sample) is the arrangement table's to carry, with the
sample's sustain; and the role reader's "bass" is a role, not a voice.

"Much better, but it cuts out at 28 seconds and comes back later: a
style choice, or a bug?" A bug: at 27.5 s the written line played one
note where Locke's own line starts walking with five, and at 44.7 s a
lone note on beat three. The manner's density window and downbeat rule
were song-wide, and Locke's one-note intro bars (its line rests through
most of its first eight) licensed one-note bars without a downbeat in
the walking section. Density is the arrangement's, bar by bar, like the
rests and the volume: a written bar now strikes between TIGHT (half and
one and a half) times as often as the song's own bar and strikes the
downbeat where that bar does (`writer.envelope`, `within`); the manner
keeps the feel and the tones, song-wide. And where nothing passes in
TRIES draws, the writer takes a figure in the manner and the envelope
alone, else the song's own bar, never an unchecked draw (one such draw
had put ninths of a beat into Locke's bar 14). Locke's walking section
now plays through at two to four strikes a bar, every bar on the one.

"Goes silent still around the same time, and later." Measured bar by
bar (RMS of the stems, `loudness.py`): from 27.5 s to 38 s the written
bass stem sat 4 to 10 dB under the original. Locke's second bass voice
is not a blip layer in the walking section: there it doubles the line
at unison with notes held a whole beat (0.84 s), and blips only in its
own intro pattern, whose 207 short notes had set the voice's median
length at 0.15 beats; the rebuilt doubling had that length everywhere,
so the walking section lost its second voice. A doubling note at the
attack now lasts as long as the line's note it doubles; a note at an
offset after it keeps the layer's own length. The written stem now
tracks the original within 2 dB through the walking section. The lesson
for the arrangement table: a layer is described by what it does at each
attack (length relative to the line's note, offset, pitch relation), not
by one median.

"It completely drops out at 12 s. Do we keep patching it instead of
finding the cause?" At 12.0 to 13.7 s the written stem is digital
silence though the written score holds a line note there (11.10 to
13.66 s) and its doubling: the layer's own intro blip at 11.60 to 12.00
s, kept, overlaps the rebuilt doubling on the same voice, and a voice
plays one note at a time, so the blip's end cuts the doubling; the
line's own sample is a 0.2-second pluck, gone by 12.0 s. Five Locke
rounds, one cause: the harness and the writer treat a bass as one voice
with one figure a bar, and Locke's bass is a two-voice arrangement
whose relation changes through the song; each round rebuilt one more
piece of it from a song-wide median. **Measured** before deciding
(`orchestration.py`, `layering.py`): of 1,314 songs with a bass, 1,177
put it on one voice and 137 on two or more. A per-voice profile keyed
on the event's class (on or off the beat, first in its bar or not)
puts a layered song's own notes back on the right voice and length in
71 % of (event, voice) pairs at the median, 22 of 127 songs at 85 % or
better: too weak to build on. What the second voice does, song by song:
**doubling** in 24 (it sounds at the same events as the first, 74 % of
them at the median, 15 of 24 sharing a sample: Locke's walking section);
**alternating** in 20 (the voices take turns note by note, 94 % at the
median, a note ringing past the other voice's strike 76 % of the time,
all 20 sharing a sample: the tracker's way of letting a note ring);
**apart** in 93 (a second part in the bass register with a rhythm of its
own: a pedal, a pad, Locke's intro pattern), which the role reader
lumps under one role. Doubling and alternating are generic and small to
write for (a doubling voice plays what the line plays; a free voice
takes a note that would cut a ringing one); apart is two parts, the
arrangement table's and the role reader's question, and the known
limitation of the substitution harness and the writer until then.

**Built (2026-10-22, the listener's go):** the layer code is gone from
`tools/table_bass.py`; a second bass voice is read as doubling,
alternating or apart (`relation`, by the shares above: DOUBLING 0.6,
ALTERNATING 0.6 with under NOT_BOTH 0.3 together) and the written line
goes onto the voices by that: a doubling voice plays every written note
at its pitch offset on its own sample; an alternating pair is read as one
part, the written notes ring as the pair's do (the pair's median note
length) and each goes to the voice that is free, the line's own first;
an apart voice stays as it is. Locke's second voice reads apart (its
intro pattern outweighs its walking-section doubling), so Locke stays
the arrangement item's case: **off the Substitution Check**, with Celes
(three bass notes in its first minute). In their place two single-voice
FFVI basses with real lines: Searching for Friends (medium walking, 41
bars) and Johnny C. Bad (dense walking, 33 bars), beside Terra and The
Decisive Battle. The page and `~/Music/bitComposer-dev/Table bass/` hold
those four. **Known limitation:** a song with a second bass-register
part under the bass role (93 of 1,314 songs) keeps that part as it is
while the line is rewritten; the arrangement item owns it.

The Decisive Battle, the listener: "walking all over, doesn't conform
to the structure of the piece, free spirited; it recognizes the walking
style, it just doesn't know how to construct one." Its own bass is not a
walk: a syncopated riff (strikes at the and-a before beats one and
three) that repeats, labelled walking by its marks. Measured over the
readings' basses (`walking.py`): a passing tone (a note the chord reader
calls no chord tone) is a step from both neighbours in 24 % of cases and
from neither in 40 % (the marks are noisy: a fifth of all bass onsets
read as "other"); a bar's last note reaches the next bar's first by step
29 % of the time in walking songs; bars on the same chord inside a span
repeat their figure 53 % (walking), 59 % (root-fifth), 73 % (roots).
The writer had realized every passing tone as the second over the root
and every tone in isolation. Now: a passing tone passes, a scale step
from the note before toward the next note of the bar or on in the line's
direction (`writer.passing`); a new figure uses only the marks the song's
own bass uses in RARE (2 %) of its notes; a bar on a chord its span
already had takes that bar's figure again with the measured chance
(REUSE); and the feel is the positions the song's bass strikes in RARE
of its strikes, not their subdivisions. The Decisive Battle's figures
came out the same (its bass does strike the and of two and use sus
tones, just over the thresholds), its realization smoother; whether the
rhythm vocabulary must weigh the song's frequent positions, not only
its struck ones, waits on the ear.

**The Decisive Battle: "nearly"** (the listener, "a not very good
nearly, but that will happen with generation and I am fine with it; we
aren't trying to generate bangers every time"). His one note: the song
makes a moment at 18 s where everything drops out and regears, and the
bass "blasts through it, deaf to the rest of the music." In the stems,
the rest of the song drops 20 dB at 18.5 s for two seconds; the original
bass keeps its riff there, six short strikes with three-quarter-beat
gaps, and with the rest gone that air is the moment; the written bar was
eight eighths held to the next, a wall. Measured (`breaks.py`,
`energy.py`): a bar where the other parts' onsets fall under 0.4 of the
song's median (1,517 bars in 444 songs) sees the bass keep its figure in
35 %, rest in 32 %, thin in 27 %, thicken in 6 %: what a bass does in a
break is the song's own choice, the arrangement's. By onsets Decisive's
bar 7 is not a break (27 against 38); by energy (level x sounded length
of every part but the bass) it is the song's quietest bar at 0.50 of
the median, bar 8 next at 0.64. So the harness reads the song's moments
(bars under MOMENT 0.65 of the median energy, in runs of at most
MOMENT_BARS 2; Johnny C. Bad's quieter ten-bar stretch is a section,
written like any other) and the written bass keeps the song's own
figure in them, air included (`writer.bass(hold=...)`). For the
generator: the arrangement table carries breaks (where, how long) and
what the bass does in them, per game, from the shares above.

**Searching for Friends belongs** (the listener, 2026-10-22). Johnny C.
Bad: "so close, then blows at 29 s when the bass cuts out in the
original and the written clashes with the section." The stems: the
written bass was silent from 23.6 to 30 s while the original walked,
then came in at 30.0 s, exactly the original's stop-time. The beat
reader had put four 3-beat bars there (and a 1.5-beat bar near the end)
and the writer left any bar not of the meter silent: a shortcut from
its first day, not a decision. Now every bar is written, with the
table's figures for its own number of beats (the readings hold 135
songs in 3/4 and 58 in 2/4) or the song's own bar where nothing fits
(`rhythm.all_bars_of`, the envelope bounding positions to the bar).

"The bass needs to be aware of everything else going on; a lot of good
bass is about awareness." Measured (`locking.py`): at a shared hit (a
position where two thirds or more of the other playing parts strike
together; 1,244 songs have them, 52 a song at the median) the readings'
basses strike too in 63 to 66 % of cases; on a stop (a beat no other
part sounds in: rare, 184 in all) they rest in 53 to 69 %. Two times in
three either way: a tendency, not a law, and the song's own choice where
it isn't. So the harness reads the song's own locking a bar at a time
(the shared hits its bass strikes, the stops it rests in; `locks`) and
the written bass must do the same (`writer.locked`), falling back to
the song's own bar where no figure can. Terra locks in 49 of 74 bars,
The Decisive Battle in 22 of 23, Johnny C. Bad in 37 of 38.

**Where the bass stands (2026-10-22):** Terra belongs; Searching for
Friends belongs; The Decisive Battle nearly ("a not very good nearly,
and that will happen with generation; we aren't trying to generate
bangers every time"); Johnny C. Bad to be heard again with every bar
written and the band locked. The bass table's acceptance by ear is met
on two of four with one nearly, and the bass item closes here, with
these **known issues**, each the arrangement item's or a reader's:

- A second bass-register part under the bass role (93 of 1,314 songs:
  Locke's intro pattern) stays as it is while the line is rewritten;
  the role reader may be lumping two parts, and the arrangement table
  owns layered basses.
- The writer hears the band through the song's own rests, volume,
  density, moments and locking, all read from the song being written
  for; the generator will need each from a table (arrangement: breaks,
  locking, layering, density by section) and the form reader's sections
  in place of the song's own spans.
- The figures' tone marks carry the chord reader's noise (a fifth of
  bass onsets read as "other"; a passing tone is a step from both
  neighbours in only a quarter of cases); the writer realizes marks
  defensively (passing tones pass, the song's own marks only), and a
  contour representation (intervals beside marks) is the next step if
  walking lines still wander.
- The beat reader doubles Terra's tempo and puts four 3/4 bars in Johnny
  C. Bad's walking passage; the writer now follows such bars rather than
  skipping them, but their figures come from the 3/4 inventory.
- The rhythm vocabulary checks the positions a song strikes, not how
  often (The Decisive Battle's straight eighths passed); weighting by
  frequency waits on the ear.

**Johnny C. Bad nearly** (the listener, 2026-10-22: "much better, I can
see it as more of a written choice"). The bass item closes at two
belongs and two nearlies.

### The drums written (2026-10-22)

The harness is a module now (`translate/harness.py`: the song loaded
once, `write_bass`, `write_drums`, the score with the written parts in
place, the stems; `tools/table_parts.py --parts bass,drums`, and
`tools/table_bass.py` a wrapper), the bass figures byte-identical to
before the move. The drums: every voice the readers call drums is the
kit, one part; each piece maps to the voice and sample the song strikes
it with most, with its usual settings, pitch register and note length;
two pieces on one voice at once keep the one the song strikes more. The
first writer drew the whole kit's bar as one figure, and The Decisive
Battle's full kit (kick and snare on one voice, snare and another piece
on a second, a cymbal, a hat in sixteenths) came back as its own bars in
most places: a whole kit's bar is too particular a figure for any
inventory to hold many of, and a per-piece envelope (each piece's strikes
within TIGHT of the song's own bar's, so a snare roll never stands in
for the hat) left almost nothing to draw. So the drums are written a
limb at a time (`rhythm.DRUM_GROUPS`: kick, snare and tom as one line;
the hat; cymbals; the rest), each group from its own inventory over the
readings (`rhythm.drum_group_units`), in the song's own manner for the
group, its envelope piece by piece, its spans, the moments, and locked
to the band two times in three (LOCK_DRUMS, the readings' rate; every
shared hit pinned the kick and snare to the song's own). The four, bass
and drums both written, on the Substitution Check with a switch and a
verdict for each part: Terra's one snare voice, The Decisive Battle's
full kit (its kick-snare line the song's own in 11 of 23 bars, where the
moments and the exact spans hold it, the hat its own in 2 of 21), Searching
for Friends' one hat voice (its own in 1 of 41), Johnny C. Bad's one
ride-like voice (9 of 38). **Awaiting the ear.** Known beside the bass's
issues: the groups are written independently of one another and of the
written bass, each locked to the song's original band, so written parts
lock to the song and not yet to each other; a kit with kick and snare
on one voice can lose a hit where the written line strikes both at once
(The Decisive Battle: 19 of 588); the hat's inventory is dominated by
straight eighths and sixteenths.

Terra's drums, the listener: "nearly; is the snare cutting out short a
style choice or a bug, and it isn't aware of the intro as the written
bass is." Measured: Terra's snare fades in with its bass (its first hits
at 6 of 127; the original drum stem rising from −53 to −41 dB over six
seconds) and plays at four levels through the song, while the written
drums sat at one level from the first bar: the drum writer took the
piece's usual volume where the bass writer takes the song's nearest
note's. And a main snare hit lasts 0.34 s in Terra, nearly to the next,
its roll's pickups 0.09 s, while every written hit got the piece's
median length, 0.15 s, which the pickups pull down: each main hit
stopped halfway to the next. Both the bass's rules, unapplied: a drum
hit now takes the volume of the song's nearest hit of the same piece,
and lasts its gap to the next hit on its voice times the piece's own
sounded share (Terra's snare 0.81; The Decisive Battle's kick 0.91,
snare 0.82, hat 0.81, cymbal 0.94). The missing triplet pickup in
alternate bars is a draw within the rules (a four-strike bar where the
song's own has six). The written drum stem now fades in with the
original (−56, −48, −42 dB over the first three pairs of bars against
−53, −46, −41).

**The Decisive Battle's drums belong** (the listener, 2026-10-22). His
one suspicion: both written parts cut out at 54 s. Not a choice and not
a patch: the readings count a song once through to its loop, the
writers write those bars, and The Decisive Battle loops back to its
first bar after 52.9 s, its first pass ending at 54.6 s of a one-minute
render, where both written parts had no bars left (the other three loop
past the minute, so it never showed). The harness now repeats the
written notes as the song does, shifted by the loop's length from the
bar it loops back to, to the render's end (`harness.looped`); the stems
carry on past 54.6 s within a decibel or two of the originals.

**Terra's drums belong** (the listener, 2026-10-22). Searching for
Friends: "all closed hi-hat; the original has open hi-hat too: a choice
or a bug?" A bug in the harness: its hat voice strikes two samples the
namer both calls hat, a long one (the open hat, 329 hits, on beats one,
two and four and the and of three) and a short one (the closed, 813
hits, on the sixteenths between), and the harness had mapped the piece
to the sample the song strikes most. A hit now takes the sample the
song uses most at its position in the bar, the piece's usual where the
song never strikes that position (`choice` in `write_drums`); The
Decisive Battle's hat and snare (two samples each) choose the same way.

**Searching for Friends' drums belong** (the listener, 2026-10-22).
Johnny C. Bad's drums, nearly: "at 29 s the song calls on the drums for
a fill and ours just keep doing their thing." The stems agree in level
and density; what differs is the kind of bar. Johnny's stop-time leaves
holes where nothing but the drums sounds (29.5 to 30.0 s, 31.5 to 32.0,
34.0 to 34.5), and the original drummer answers each: a roll of triplet
sixteenths at 30 s (11 strikes), a dense triplet roll after it, swing
figures on. The written drums played straight eighths and the plain
swing pattern there, within every rule (the envelope allowed 6 to 16
strikes, the positions are the song's) and deaf to the hole, as the
bass was at Decisive's 18 s; the moment rule missed it because the
stop-time is a ten-bar section at low energy, not a two-bar drop. Now a
bar holding a stop beat (no voice but the part's sounds in it) that the
song's own part plays through keeps the song's own bar (`harness.stops`,
on the detection `locks` already had): Johnny's drums answer in bars 0
and 13 to 19. For the generator, the arrangement table's row: what a
part does when the band stops (fill, hit, keep time, rest), per game.

**The bass and drum items close (2026-10-22).** The listener's verdicts
on the Substitution Check, read back from its store: Terra, The Decisive
Battle, Searching for Friends and Johnny C. Bad, bass and drums, all
eight **belong** ("Johnny C. Bad: the writing basically nails it now; I
bumped them all up to belongs; I was questioning the bass on Decisive
Battle, but that was my taste being injected"). The exit criterion for
these two tables, a bass and a kit written from the tables passing the
ear in substitution, is met. What the two writers share is the record's
real finding: the tables give the inventory and the song's own mixture
gives the loyalty, but a part belongs only when it is written in the
song's own manner (feel, tones, pieces), each bar's own envelope, its
spans, its moments, the band's stops and shared hits, its volumes and
its voices, all read from the song; the generator will need each of
those from a table of its own before a part written into a song it
made can belong there the same way.

### Voicings (2026-10-22)

Two tables from the readings' chord spans (`rhythm.voicing_units`,
`width_units`; a tone sounds in a span when a part's notes on it cover
SOUNDS of it). **Which chord tones a part holds** (harmony,
accompaniment, arp: 23,860 spans, the marks R 3 s 5 7 +), held-out bits
a span, share votes, Witten-Bell: (none) −4.60, the part −4.57, the
part and the chord's shape −3.78, with the bass's tone under it −3.81
(nothing), the voicing's width −3.66, the span before −3.57, the song's
habit (its tones a span, thin / full / rich) −3.34; as the song's
mixture over part+shape+previous −3.37, its draws 5.0 distinct a song
and 0.48 the most common's share against 5.3 and 0.48 real. By song
within the games, a game's own table −3.78 against −3.58 shared: the
game adds nothing. **Kept:** part, shape and the song's habit, as the
song's mixture. **How wide the upper voicing sits** (distinct pitches
to six, close / open / wide: 20,988 spans): the shape, the parts
present and the bass's tone add nothing (−3.53 against −3.55 none), the
span before +0.7, the song's mixture +0.9 (−2.67; with the span before
−2.53, draws 4.1 / 0.54 against 3.8 / 0.60); a game's own table worse.
Width is the song's habit, not the chord's. **Kept:** the song's
mixture with the span before. Neither has a writer yet: the voicings
are phase 4's, when the generator voices its own chords.

### The key check by ear (2026-10-22, set)

The gate before the harmony tables: a dozen songs with the tonic named
by ear, the scale reader scored on them. The Key Check page: twelve
30-second excerpts looping, a row of twelve keys to hold against the
music (a soft two-octave tone), the listener marking the key that
feels like home and whether the song feels bright or dark; the answers
in the page's store (`keys/kNN`), the reader's tonic and mode off the
page (`~/diags/bitcomposer/idiom/phase3/set.json`, on both machines).
The songs, across games, six from each half, the reader's fit 0.6 or
better, none of the substitution set: The Fierce Battle, Unkai, Misty
Menace, Autumn Sky / Womanheart, Jojo, Sailing, Few Paths Forbidden,
Cavern, Vanilla Dome, The Little Sprite, Las Vegas, Rude Awakening.
Clips rendered through the converter and libopenmpt (`keycheck.py`).
Two clips re-cut from where the song's pitched parts settle (Misty
Menace's at 51 s; `recut.py`) and one song swapped (Rude Awakening is
atmosphere throughout; Snowman in its place). The tone tuned to each
song from its notes' absolute frequencies (`abs_tuning.py`: Misty Menace
and Cavern sit 37 cents sharp of A=440, the rest within 9; the readings'
per-sample offsets are not that measure).

**The ear against the reader (2026-10-22, the first round):**

| song | reader | ear | the ear's note is |
|---|---|---|---|
| The Fierce Battle | A minor | E minor | the fifth |
| Unkai | B minor | D minor | the relative major's root |
| Misty Menace | C minor | G# minor | the minor sixth |
| Autumn Sky / Womanheart | E major | A major | the fourth |
| Jojo | E minor | G minor | the relative major's root |
| Sailing | D major | B minor | the relative minor |
| Few Paths Forbidden | G minor | D minor | the fifth |
| Cavern | A# major | F minor | the fifth |
| Vanilla Dome | A minor | D minor | the fourth |
| The Little Sprite | A minor | A major | the same note |
| Las Vegas | C minor | D# major | the relative major |
| Snowman | C# minor | C minor | a semitone below |

The same note once, a fifth or fourth away five times, the relative key
four, elsewhere twice; bright or dark agreed eight of twelve. The picks
are never random: ten of twelve sit in the key's own family, exactly
where a tonic is ambiguous to ears and readers alike (the dominant that
feels like home, the relative pair). So the round cannot score the
reader by itself: on each disagreement either could be right. Snowman's
bass sits on C# at concert pitch (69.1 and 139.1 Hz), so that one is the
ear's miss. **Second round:** the Tonic Duel page (the same clips, two
tones a song in a shuffled order, the reader's tonic and the ear's,
names off the page; `duel-map.json` beside `set.json` holds which is
which), the listener choosing which sounds like home; eleven songs, The
Little Sprite left out where the two agree.

**The duel (2026-10-22, the second round).** The test turned out to need
the ending, not the fit: a tone that fits while the music plays is
consonant, and the fifth is as consonant as home, which is where the
first round's fifths came from. The page got a Stop on A / Stop on B
button a song: the song cuts out, the tone rings alone for two seconds,
and the listener picks the stop that sounded like the end. The picks,
with what the readings say the song leans on (`duel_evidence.py`: the
bass's pitch-class time, the chord reader's roots by time, the roots at
four-bar phrase starts and ends through the loop, Krumhansl-Kessler
correlation on the notes' chroma):

| song | reader | ear | duel | the song leans on |
|---|---|---|---|---|
| The Fierce Battle | A | E | E | A: roots 55 %, bass 42 %; E 0 % of chord time |
| Unkai | B | D | B | B: bass 62 %, roots 53 % |
| Misty Menace | C | G# | C | C: roots 52 % |
| Autumn Sky / Womanheart | E | A | E | E roots 43 % / A 25 %; Krumhansl a tie |
| Jojo | E | G | E | E: roots 88 % |
| Sailing | D | B | D | D: Krumhansl D major 0.78 |
| Few Paths Forbidden | G | D | D | D: bass 46 % vs 4 %, roots 57 % vs 17 %, Krumhansl D minor 0.93 |
| Cavern | A# | F | F | A#: roots 50 %, phrase starts and ends 13 of 20 |
| Vanilla Dome | A | D | D | D: bass 37 %, roots 39 %; A 0 % (chromatic, fit 0.75) |
| Las Vegas | C | D# | C | C: bass 35 %, roots 42 % |
| Snowman | C# | C | C | neither: F#/B (roots 32/20 %); the duel offered two wrong tones |

The ear under the ending test: eight of ten scorable songs agree with
the evidence; every relative-key case went to the reader's tonic, both
of the reader's misses went to the ear's, and the two misses are the
fifth held as home (The Fierce Battle, Cavern). **The reader on the
labelled dozen: 9 of 11** (Snowman unsettled). Its two misses have
causes: Few Paths Forbidden opens on a G minor chord before settling on
D, and the tonic lean weighs the first chord 0.5 against the bass's
share, which only beats it above 50 % (`TONIC_WEIGHTS`, tuned where the
first chord is the tonic by construction, the generator's songs); Vanilla
Dome is chromatic, its best set a harmonic minor with one named mode, so
the tonic was forced onto a pitch class the song never sits on. Across
the corpus (`tonic_corpus.py`, 1,571 songs with a key and chords) the
reader's tonic is the top chord root in 52 % of songs, the top bass
pitch class in 47 %, Krumhansl's tonic in 52 %; 60 % / 53 % / 59 % at
fit 0.9 and better: consistent with the dozen's four in five, the errors
in the low-fit songs. Alternative leans (bass + roots; any pitch class
of the set as a candidate) each fix one miss and lose another on the
dozen (The Little Sprite sits on its IV): eleven labels are not enough
to retune the reader on, and the labels in hand (`keycheck/truth.json`
beside the readings) stay for the day it is.

**Gate decision (2026-10-22):** the harmony tables count over the songs
whose reader tonic is also their most-played chord root: 816 of 1,571
(`tonic_filter.py`). On the dozen that keeps eight right tonics and no
wrong one (The Little Sprite and Snowman out with the two misses). The
bias is toward tonic-heavy songs, accepted: the song's own chords (the
mixture) carry the writing in any case, as they did for rhythm, bass and
drums, and the general table is the fallback.
### Harmony (2026-10-22)

The plan's fifth item, behind the tonic gate: four tables from the
bar-by-bar chord reader over the form's parts (a part that repeats an
earlier one left out), `chord_units`, `change_units`, `cadence_units`,
`loop_units` in rhythm.py (`tables chords|degrees|shapes|changes|cadences|loops`).
The tables by degree count only the songs whose tonic is sure
(`tonic_sure`: the key reader's tonic is the chord root the song plays
most; 843 of 1,562, `--unsure` counts the rest too); the harmonic rhythm
needs no tonic and counts every song. Share votes, discount 0.75, the
games split.

**Chords.** The unit is a bar's chord as a numeral in the song's key, the
shape kept (I5, i, VI, i7, Isus4; 147 entries; a bar without a chord is
one), the chain the bar before's. 16,689 bars, 7,153 development, 9,536
held-out. Held-out bits a bar: none −5.27; the bar before −4.79 (the
only conditioning that helps alone: after I5 the next bar is I5 69 %,
after i it is i 53 %); the bar before that −5.16; the mode, the meter,
the tempo band, the bar's place in its part, the part's place in the
form, the song's variety (distinct chords: one, few, several, many) and
its motion (the share of bars changing chord) each −5.37 to −5.67,
below none (the discount's cost at a level that sorts nothing); a game
nothing, by the games' split and by the songs' (`--split song`: the
mixture −4.11, with the game −4.15). **The song's own
mixture is the table once more:** the mixture over no context −3.94,
over part+mode −4.07, over the chain −4.10 (the chain's gain absorbed by
"same" and "earlier"; its draws narrow to 5.2 distinct chords a song
against 7.4 real, where the mixture over part+mode draws 6.0 and the
unconditioned 7.2; the ostinato share 0.42 against 0.43). The recall
shares: same 0.33, earlier 0.29, new 0.37 (a one-chord song same 0.50,
new 0.50). With the unsure songs in (30,927 bars) the same picture a
quarter-bit worse (none −5.71, the mixture −4.17): the gate's songs are
the more predictable, as a tonic-heavy bias would be. **Kept:** the
numerals as the song's mixture over the part+mode table; a song with no
chords yet draws its first bars from the chain (part+mode+previous,
−4.79 against −5.27), as the figure writers put the habit before the
previous bar. Also measured, the progression factored: the degree alone
(16 entries; none −2.65, the chain −2.28, the mixture over the chain
−2.18, over part+mode −2.20; draws 3.8 to 4.0 distinct against 4.5) and
the shape given the degree (12 entries; part+mode+degree −2.45, as the
mixture −1.98, with the bar before −1.96); the two together −4.14 to
−4.16 a bar against the joint mixture's −3.94 to −4.07, so the joint
table is kept, its 147 entries no burden under the mixture. What the
sure songs play: in minor I5 22 %, i 15 %, VI 4 %, i7 4 %, IV5 3 %; in
major I 23 %, I5 14 %, IV 5 %, V 4 %, vi 3 %; 36 % of bars keep the bar
before's chord.

**The harmonic rhythm.** The unit is a bar's chord changes by position
(beats from the bar line on the half beat; "none"): 37,947 bars of every
song, two outcomes carry nearly all of it ("0" and "none"). Held-out bits
a bar: none −1.006; the song's motion habit −0.834 (+0.17: a moving song
changes chord on 82 % of its bar lines, a static one on 20 %); the bar
before −0.935; the mode, the meter, the tempo, the bar's place in its
part within 0.02 of none; the mixture nothing on top of the habit (−0.84).
**Kept:** part+meter+habit; the writer changes chord on the bar line at
the song's rate, and inside a bar almost never (the chord reader reads
bar by bar).

**Cadences.** The unit is a part's chord sequence's ending (phrases.py's
seven: V -> I, IV -> I, bVII -> I, another -> I, half on V, elsewhere, one
chord): 2,350 parts. A third of the form's parts sit on one chord (815);
of the rest, "elsewhere" 45 to 49 %, a half cadence 15 to 21 %, a return
to I 36 % (another -> I 14, IV -> I 7 to 9, V -> I 6 to 7, bVII -> I 6).
Held-out bits: none −2.37; the progression's length +0.94 (definitional
for the one-chord parts); the part's place in the form +0.015 (a last
part halves on V 17 % against 8 % of first parts, and that is all); the
mode and the variety nothing. **Kept:** part+mode+length, and the
finding that the form reader's parts do not cadence: either game loops
seldom do or the parts are cut mid-progression (item 6's question).

**The loop.** The unit is the chord the loop returns to, 614 sure songs
with a loop: the tonic degree 80 % (I5 32, i 19, I 14, i7 4, Isus4 4, I7
3, Imaj7 2, Isus2 2), the same chord as the last bar 26 %. Neither the
mode nor the last bar's chord predicts it beyond the base (none −3.66,
with the last chord −3.90, 270 development units). **Kept:** the base
distribution: the loop lands on the tonic, and the writer knows it.

**Item 5 closed:** the harmony tables counted and recorded; no writer
yet (a chord substitution into a real song would re-pitch every part, so
these tables meet the ear with the generator's songs, later). The mode
is the key reader's major/minor (the readings keep no finer name to
fold). Next: item 6, phrases and form.

### Phrases and form (2026-10-22)

The plan's sixth item: the form's letters and lengths from the form
reader at both of its levels, the melody's phrase shapes from phrases.py
(`form_units`, `length_units`, `letters_units` in rhythm.py with
`--level part|section`; `contour_units`, `relation_units`,
`ending_units`, `peak_units` in phrases.py with `--length 4|part`;
share votes, discount 0.75, the games split, the mixture tried on each).

**The level.** The reader's parts against the 36 songs marked by ear
(`heard-form.json`, `phrases --heard`): part starts recall 0.76,
precision 0.66 (105 read against 91 marked); sections recall 0.73,
precision 0.53 (51 against 37). The reader over-cuts at both levels, the
parts less; the ear's own level lies between the two and nearer the
parts. **Kept: the part level** (1,366 songs with a form, a median of
three parts of four bars), the sections as the rule that joins a short
part played again at once. No further ear round: the marks exist at both
levels and nothing below turns on them.

**The form as a chain.** The unit is a part's kind, new material, the
part before once more (again) or an earlier part returning (back); 5,556
parts. By index: the first part is new by definition, the second new
90 % / again 10 %, the third new 73 / again 20 / back 7, the fifth and
later new 58 / back 25 / again 17. Held-out bits a part: none −1.07; the
index −0.84 (+0.23, part of it the first part's certainty), the letters
so far −0.88, the kind before −0.90, the song's size in parts −0.94; the
mixture a little worse than each (a song's kinds do not repeat). At the
section level the same picture (none −0.81, the index −0.63) with fewer
agains, as joining them makes. **Kept:** part+meter+index. Whole forms as
one outcome a song: 274 distinct strings in 1,366 songs, 'A' 27 %, 'A B'
18 %, 'A B C' 7 %, 'A B C D' 5 %, 'A B B C' 3 %, 'A A B' 2 % (held-out
−5.0 bits a song, nothing conditions it): a quarter of the games' songs
are one part looping, a tenth of a part's returns are the generator's
AABA and rondo kind, and the chain above is the table to draw from, not
the strings.

**The lengths.** The unit is a part's length in bars (32 and over one
outcome): 4 bars 32 % of new parts, 68 % of agains, 47 % of backs; 8 bars
10 to 12 %; held-out bits none −3.45; the song's habit (its median part
length: short, medium, long) −3.14 (+0.30: a short-habit song's parts are
4 bars 61 %, a medium-habit song's 8 bars 21 %, 4 bars 17 %, 6 bars 13 %);
the mixture −3.32; the kind, the index, the length before each +0.1
under the mixture and nothing alone. **Kept:** part+meter+habit, the
habit a song's choice.

**The phrases** (1,366 songs with a key, fit chords and a form; 8,691
four-bar phrases with a tune, 4,812 at the part's length; the melody
voice 95 %, the counter-line standing in 5 %):
- *Contour*: level 37 %, falling 25 %, rising 24 %, arch 7 %, valley 7 %.
  Nothing conditions it: the phrase's place in its part, the part's in
  the form, the source, the relation to the phrase before, the contour
  before, the mode all within 0.01 of none (−2.04); the mixture +0.07.
- *Peak*: follows the contour (+0.28: a falling phrase peaks in its first
  quarter 72 %, a rising one in its last 45 % or third 31 %, an arch in
  its second 55 %); nothing else.
- *Ending* (the note held longest in the last bar, against the key):
  another degree 36 to 39 %, off the scale 18 to 19 %, the tonic 16 % in
  a phrase that does not end its part and 19 to 20 % in one that does,
  the fifth 14 to 15 %, the third 11 to 12 %. Nothing conditions it beyond
  the mixture (+0.11); whether the phrase ends its part, is the song's
  last, where it sits, its contour, all within 0.01: **the games' phrases
  do not close on the tonic**, by part or by song, and a fifth of their
  endings sit off the read scale (chromatic melodies, or the key reader's
  share of misses, or the pickup taken as the final: a caveat for item 4's
  melody tables, not resolved here).
- *Relation* to the phrase before (the song's first phrase left out, it
  stands to nothing): new 74 to 83 %, repeated 8 to 14 %, answered 4 to
  10 %, moved up or down 2 to 4 %. Held-out bits none −1.27 (four bars);
  the song's habit with the mixture −1.15 (+0.12), the place +0.11; the
  relation before and the part's place in the form nothing once the first
  phrase is out (their earlier +0.68 and +0.75 were that phrase).
  **Kept:** part+mode+habit as the mixture. phrases.py's thresholds
  (SAME 0.75 of the notes in place and pitch) make "repeated" strict; a
  varied repeat reads as new, which the writer should know when it reads
  these numbers.

**Item 6 closed:** the form at the part level as a chain of kinds by
index and lengths by the song's habit; the phrase shapes nearly free, the
peak following the contour; the ear's existing marks answer the level
question, no new round. Next: item 7, the arrangement (which parts play
in which bars, voices a song, echo voices and doublings, the layered
basses and breaks the bass rounds left), then the pack's second format.

### The arrangement (2026-10-22)

The plan's seventh item, and the bass rounds' debts (breaks, layering,
density by section): seven tables from the roles and the notes
(`texture_units`, `presence_units`, `band_units`, `parts_units`,
`voices_units`, `double_units`, `layer_units` in rhythm.py; `tables
texture|presence|band|parts|voices|doubles|layers`). Share votes,
discount 0.75; each run by the games' split and by the songs' within
each game (the per-game question is only answerable by the second: a
held-out game's own table is empty, and the harmony record's per-game
claim is now made on the songs' split too). A part "plays" in a bar
when it strikes a note there or holds one SUSTAIN (a beat) into it.

**The texture** (which parts sound in a bar; 37,947 bars of 1,562
songs; 96 textures in the development half). Held-out bits a bar: none
−4.95; the song's band as its habit with the mixture −1.15 (the mixture
alone −1.72, +3.2 of the +3.8: a song's textures are its own, two or
three a song); the bar before with the mixture −1.25; a game +0.01 by
the songs' split. 77 % of bars keep the bar before's texture. The draws:
over the band habit 3.6 to 3.7 distinct textures a song against 2.1 to
2.2 real (parts dropping in and out too much), over the bar before 2.4
to 3.0 (with the game, 2.4). **Kept:** the mixture over
part+meter+previous(+game), a tenth of a bit dearer and the spread
right: the writer keeps the band from bar to bar and changes it the
song's own way. Parts sounding a bar by the part's place in the form:
3.60 in a first part, 3.91 in a middle one, 3.96 in a last (the intro
thinner by a third of a part): density by section is that small.

**The presence** (each part, plays or rests, a bar; 157,046 units).
Parts rest 6 to 11 % of their songs' bars (the melody 8, the bass,
accompaniment and drums 6, the counter-line and arp 11, held harmony
19). Held-out bits none −0.39; the bar before with the mixture −0.205
(+0.19; after a bar the drums play they play 99 %, after one they rest
they rest 83 %: breaks run on); the part's habit (sparse, mostly,
always) with the mixture −0.21; the bar's place and its part's place in
the form +0.15 each; a game nothing. What conditions a rest: the band's
thinness (the bass rests 16 % of the bars where one other part plays,
4 % where three or more do), a first part (the drums rest 10 % of its
bars against 5 to 6 % elsewhere: intros), the bar before. **Breaks**
(a part that mostly plays resting inside a part, playing on both
sides; `arrangement_dist.py`): 824 over the songs; one bar 67 %, two
16 %, three 8 %, four and more 9 %; 68 % inside the part, 19 % its last
bar (the stop before the next part), 13 % its first. **Kept:**
part+meter+previous as the mixture, the others value kept beside it for
a writer that knows the band.

**The band.** As one string a song (76 bands in the development half:
accompaniment bass drums melody 20 %, with a counter-line 17 %, without
drums 7 %, ...), nothing conditions it, not the game (−4.74 none, −4.81
with the game by the songs' split): too fine an outcome for 40 songs a
game. As the coarse view, each part asked yes or no (`parts`): 31 % of
songs have no drums, 15 % no bass, 9 % no melody, 11 % no chordal part,
34 % a double voice. Held-out bits none −0.88; the band's size −0.70
(+0.19); the game −0.70 alone and +0.08 on the drums (Super Ghouls'n
Ghosts has drums in none of 23 songs, Dragon Quest V in 13 %, Super
Castlevania IV 33 %, Super Mario World 47 %; the band-heavy games in
nearly all), nothing on the melody or the bass. **Kept:** part+band for
the parts, the drums per game.

**The voices.** 8 of the chip's voices in 53 % of songs, 6 in 18 %, 7
in 15 %, 5 in 8 %; a band of five parts uses eight voices 71 % of the
time. Held-out bits none −1.92; the game −1.44 (+0.48, the one table
that is a game's habit: its driver's and its composer's); the band's
size with the game −1.35. **Kept:** part+band+game.

**Doublings** (the role reader's double voices, with what they double
and whether at unison or as an echo, ECHO 20 ms). 66 % of songs have
none; melody echo 8 %, accompaniment echo 6 %, counter echo 3 %, bass
unison 2 %, melody unison 2 %; by game from Soul Blazer 100 % and
Donkey Kong Country 58 to 76 % to none. As the set a song (39 outcomes)
nothing conditions it, the game −0.03; the coarse yes/no sits in the
parts table above (34 % of songs). **Kept:** the base distribution a
game for whether, the shared one for what.

**Layered basses** (137 of 1,332 songs with a bass hold two bass
voices): apart 72 %, doubling 14 %, alternating 14 % (harness.relation,
the line the voice with the longest notes); EarthBound 19 songs (14
apart), Final Fantasy VI 13 (all apart), Super Mario World 9. Nothing
conditions it (137 units); the share a game is the table. The "apart"
songs stay the known limitation: a second bass-register part the role
reader lumps under the bass, for the role reader to split one day.

**Item 7 closed:** the arrangement counted as the texture chain, the
presence chain, the parts a song by band size (drums per game), the
voices per game, the doublings and the layered basses as shares.
Phase 3's tables are all counted; what remains of the phase is the
pack's second format and the reference set. The listening returns in
phase 4, when the generator writes whole songs from these tables.

### The pack's second format, and the reference set (2026-10-22)

**Format 2.** `bitcomposer_pack: 2` adds one field, `tables`, beside the
voices (docs/PACKS.md, "The tables"): the kept shapes of this record,
fitted on one game's readings with share votes and the 0.75 discount,
each written as `translate.tables` writes a table (its conditionings,
vocabulary and the votes under each context), the figure tables with
their bar-cell floor and every mixture with its recall table, so a
model reads back whole (`Table.to_json/from_json`, `Cache` and
`BarCells` the same; `translate/packtables.py` holds the list KEPT,
`fit`, `build`, `read` and the CLI). The loader (`packs/packfile.py`)
accepts 1 and 2, checks the field's shape and keeps it on the pack's
table; the importer, export and add carry it as data; a format 1 file
loads as before.

**The FFVI pack in it.** The importer's thin pack from the 82 SPC files
(`python -m bitcomposer.spc --pack`, 24 s on Ragnarok: 22 samples, a
kit of kick, hat and snare), then `packtables --into` from the readings:
28 tables of 67 songs (the free-time and silent ones out), 2.9 MB of
JSON (the rhythm table's 1,183 bar patterns under 2,289 contexts, the
bass's 715 figures, the chords' 95 numerals; the cell floors' tables
inside). Read back through the loader: all 28 as models, the floors as
BarCells; Terra's own bass bars score −2.53 bits a bar under the pack's
bass mixture (a sanity check, the song being in the pack, not a
measure); the pack composes a song through the 1.x generator unchanged
(`bitcomposer --pack-file ... -s 7`), the tables riding along unread
until phase 4. On Ragnarok at `~/diags/bitcomposer/idiom/phase3/pack2/ffvi/`.

**The reference set.** `translate/reference.py` writes every four-bar
phrase with a tune (phrases.py's windows and tunes) as its rhythm (onsets
in twelfths of a beat from the phrase's start) and its intervals
(semitone steps), with the song, game and bar: 8,691 phrases of 1,366
songs, 2 MB, at `~/diags/bitcomposer/idiom/phase3/reference/phrases-4bar.json`
on both machines, never in the repository. `reference.Index` looks a
phrase up by rhythm and intervals together, or by either alone, for
phase 4's tune-copy check. In the set itself 7,175 of the 8,691 are
distinct; 964 keys are shared by two phrases or more, 137 of them across
different songs: the games' own rate of a phrase reappearing, the
baseline a written song is held to.

### Phase 3 closed (2026-10-22)

What the phase set out to produce: the tables for FFVI (the pack above)
and for the 39 games (the readings database and `tables` CLI, every
shape in this record); the likelihood table that justifies each shape
(this record, item by item); the format 2 draft and a pack in it; the
tune-copy reference set. The exit criteria, one by one: every table's
shape recorded with its held-out likelihood against its alternatives
(the record); shared or per game decided per table from the same
numbers (by the songs' split within each game, the only split that can
tell: shared everywhere but the voices a song, the drums' presence and
the articulation habit); a format 2 pack written from a game and read
back, format 1 still read (above); the tables printed and read as the
music does to an ear that knows it (each table's shares are printed in
this record and in the diagnostics' `*-dist.log`; the reading is the
listener's, and the one criterion that is his rather than the numbers');
and the two added: the bass and the drums written from their tables
passed the listener's ear in substitution (eight of eight "belongs" on
the Substitution Check), and the key check by ear was done before the
harmony tables counted, and set their gate.
Left open for phase 4: the voicings, harmony, form, phrase and
arrangement tables have no writer yet and meet the ear through the
generator's songs; the "apart" layered basses and the chord reader's
noise in the figures' marks stand as known limitations; the phrase
endings off the read scale (18 %) are a caveat for the melody tables.

Written for Terra (habit medium roots, 74 bars),
Locke (dense walking), Celes (sparse roots) and The Decisive Battle
(medium walking), seed 1, beside the originals, in the player's folder
(`~/Music/bitComposer-dev/Table bass/`): the readers read the written
voice as the bass in all four, the key unchanged in three (Celes, three
notes in a minute, moved to its relative major). The Substitution Check
page (the plan's listening instrument, first form) holds the same four:
three stems a song (the rest without the bass, the bass as the song plays
it, the bass as written; the converter's modules rendered through
libopenmpt on Ragnarok) play in sync and a switch moves between Original,
Written and None while the song plays; a verdict (belongs / nearly /
doesn't belong) and a note a song are kept in the page's store.
**Awaiting the ear** on all four.
