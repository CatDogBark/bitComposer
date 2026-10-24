# Phase 4: the writing

Planned in outline 2026-10-20; the detail below written 2026-10-22, when
the phase began, from what phase 3 found. See `../IDIOM.md` and
`phase-3-tables.md` (the record every table's shape and numbers live in).

## Goal

The generator writes for SNES packs from the tables, one part at a time,
each slice judged on fidelity and on variety before the next is begun; the
chip and Genesis palettes unchanged.

## Starts from

The score of voices and the back end (phase 2); the tables and the format
2 pack (phase 3: `translate/packtables.py`, the FFVI pack in format 2);
the bass and drum writers and the harness that passed the listener's ear
in substitution (`translate/writer.py`, `translate/harness.py`); the
current writing, replaced slice by slice behind the same `compose_song`.

## What phase 3 changed in the plan

- **The song's own mixture is the engine.** Every figure table predicted
  held-out songs twice as well once the song could repeat itself (rhythm
  −10.5 to −6.8 bits a bar, bass −21 to −13, drums −29.5 to −12.8). The
  writer is not "a bar from the table" but "a song": its habits drawn once,
  a few figures drawn and kept, the urn (`tables.Cache`) running through
  the song. A new song's urn starts empty and fills as it is written.
- **The rules that passed the ear read the song being written for**:
  manner, the per-bar envelope, moments, stops, locking. With no original
  to read, each comes from a table (texture and presence for breaks and
  density, the form chain for the parts, the harmonic rhythm for the
  changes) or from the parts of the same song written before it. Hence
  the order below: the skeleton first, the parts that lock to it after.
- **Per game is nearly nothing**: the voices a song, the drums present or
  not, the articulation habit. The idiom is one shared vocabulary; a pack
  brings its samples and those habits. The pack's own tables (FFVI: 67
  songs) are thinner than the 39 games'; under the mixture that may be
  enough, and the first slices will say.
- **The games' forms are small and loop.** A median of three parts of
  four bars; 27 % of songs one part looping, 18 % A B. The loop once
  through runs a median 47 s (quartiles 28 / 69 s; FFVI 61 s, Star Fox
  20 s, Seiken Densetsu 3 89 s); 43 % of songs have an intro before it, a
  median 4 bars. **Decided:** a written song's length is drawn from its
  game (the pack's lengths and form tables), the loop then repeated to the
  player's length; the old 70-second once-through form goes with the old
  forms. The length is a pack's habit, not a setting, until a listener
  asks for one.
- **The melody's moves were never counted.** Phase 3 has the phrase
  shapes (contour, peak, ending, relation) and the note values, not the
  intervals by position and chord. Slice 4 counts that table first.
- **The phrase endings sit off the tonic** (16 to 20 % on it, 18 % off
  the read scale): the melody writer must not be taught to close on the
  tonic from a textbook.

## The slices, in order

Each slice replaces one piece of the old writing behind `compose_song`
for a format 2 pack, so a whole song plays at every step and each slice
is an A/B against the old writing in the same song. A slice is done when
its measures are recorded and the listener has heard it.

1. **The bass and the drums** into the old generator's songs. The
   writers exist and passed the ear. The phase 2 bridge reads a generated
   song as a score the readers read; the harness writes bass and drums
   from the pack's tables for it, the old parts replaced. The first
   listening: old against new bass and drums in the same generated song.
2. **Harmony and harmonic rhythm.** A chord a bar from the chord mixture
   (the chain for the first bars), changes at the song's motion habit, the
   loop landing on the tonic; replaces theory.py's progressions.
3. **Form and arrangement.** The part chain by index, lengths by the
   song's habit, the intro, the texture and presence chains (which parts
   play in which bars, breaks); replaces structure.py's forms and energy
   curves, and decides the song's length as above.
4. **The melody.** The moves table counted (intervals by position, chord
   and value), then phrases written from contour, peak, ending and
   relation, the tune-copy check against the reference set in the suite.
5. **The counter-line, and the tune passing between voices** (the
   readings' counter and the melody's 5 % hand-off).
6. **Voicings and spread.** The chord-tone and width mixtures.

Seeds: one seed a song, each slice taking its own stream from it
(`random.Random(seed + slice)`), so a song a listener kept is made again
after later slices change, with that slice's part the only difference.

## The measures

Per slice: the written parts' units scored by the 39-game tables as a
held-out song would be (bits a unit against the games' own held-out
numbers in the phase 3 record); the spread over twenty seeds (distinct
figures a song, the ostinato share) against the game's; the nearest game
by the vocabulary's rows (phrases.py and vocab.py's headline numbers);
and, from slice 4, no four-bar phrase matching the reference set.

## The listening

Two instruments, the listener's choice (2026-10-22), and the order he set
after hearing slice 1's plan: **the gold standard first.** Comparing a
written part against the old generator's measures "better than before",
not "belongs in the music", and only the second trains the ear or proves
the writing. So every slice that can be substituted into a real song goes
onto the Substitution Check as a new toggle, on the same songs, before
anything touches the generator: free-written bass and drums (slice 1's
new thing), the accompaniment and its voicings, the melody, the
counter-line. The two that cannot be substituted, the harmony progression
(new chords under a real tune clash with it) and the form and
arrangement (the form is the song), wait for the Song Check, when a whole
written song is worth hearing. The old-generator comparison stays for
plumbing and measures.

- **Per slice, the Substitution Check** as phase 3 built it: the old part
  against the new inside the same generated song, several seeds on one
  page, a switch and a verdict a part, notes saved in the page's store.
- **Per milestone, a Song Check**: whole written songs over several seeds,
  mute and solo a part so the listener can say which part breaks a song,
  a verdict and notes a song, and "keep this one" recording the seed.
- **The blind test** (two versions of the generator, which is which)
  after the listener has compared the new writing to the music he knows,
  so he can read his own bias against the blind pick rate.

Before each slice's page is built, what the slice added is said plainly,
so the listening can focus on it.

## Exit criteria

- Songs written with FFVI's vocabulary fall nearest FFVI more often than
  any other game, and with another game's, nearest it.
- Their spread over twenty seeds within the game's own spread, and each
  song committed to its figures.
- The blind pick rate recorded over versions.
- No four-bar phrase matches a game's.
- The built-in SNES packs' move decided.

## Open questions

- How much of the old writing survives: the ending styles, the intro
  conventions, the energy curve (the tables say density by section is
  nearly flat, the intro a third of a part thinner).
- When a slice is good enough to move on: the measure, or the ear, or
  both; phase 3's answer was the ear with the measure beside it.
- Whether a song's "situation" (a battle, a town, a scene) is a weight the
  pack carries; the readings do not say, so not from them.
- The thin pack: where the pack's own table is thin, whether the writer
  backs off to the shared 39-game tables carried in the product, and how
  a pack would say so.

## Record

### Slice 1: the bass and the drums into the old generator's songs (2026-10-22)

**Built.** `harness.load_generated` reads a composed song (compose_song's
dict) as a game's song: its score through `score.of_song`, the readers
over it, the reading kept in a database of its own, the harness's
Context from that; `harness.write_bass` and `write_drums` take a pack's
tables (`Context.models`, from `packtables.read`) in place of fitting on
the readings; `tools/slice1.py` composes seeds with a format 2 pack,
writes the two parts, renders old and new songs and the page's stems,
and measures. Three things the first runs taught, each fixed before
anything was heard:

- *The roles are the generator's, not the role reader's.* On the thin
  FFVI pack a harmony sample read as a snare, so one song's harmony
  channel was rewritten as drums. A generated song's parts come from its
  channels (`_pin_roles`: melody, bass, arp fixed; a harmony channel the
  reader's call among harmony, accompaniment and counter-line; the drum
  channels' samples named by channel, the pitched ones unnamed).
- *The beat is the generator's.* The beat reader read most generated
  songs at half their tempo, so the figures stood on bars twice too long.
  `reading.of_score` now takes a grid, and a generated song brings its
  own (`_generated_grid`: its tempo, four beats a bar from the first row).
  The same for the measures: a written song re-read on any other grid
  counted figures split across bars, which showed as a spread twice the
  real one and sent the first measures wrong.
- *A generated song's old part is no manner to keep.* The substitution
  harness reads the song's own part for its manner, envelope, spans and
  habit, which for a real song is the idiom; for a generated song it is
  the old generator. Free writing (`writer.FreeManner`, `free_envelope`,
  `_free_figures`): the habit drawn once a song from the pack's habit
  table (`bass_habits`, `drum_habits`), any bar the table knows on the
  pieces the song has, the density the habit's, and the figures drawn bar
  by bar from the song's own mixture, whose recall shares carry the
  games' rate of repeating and returning (the span-and-pattern machinery,
  which mirrors a real song's own repetition, forced onto a generated
  song gave 17 distinct figures in 32 bars and an ostinato share of 0.04).
  The form's repeated parts copy their figures; the bars the old part
  rests in rest (the arrangement is slice 3's); the band's moments, stops
  and locks are read from the other parts as before. The lock changes
  the spread little (bass 9.9 distinct with it, 8.6 without).

**Measured** (twelve seeds, the FFVI format 2 pack; the old and the new
parts and FFVI's real songs scored by figure mixtures fitted on the
other 38 games' 1,495 songs, so all three are held out alike; the
spread as distinct figures in the first 32 bars / the ostinato share):

| part | old bits | new bits | old spread | new spread | FFVI real |
|---|---|---|---|---|---|
| bass | −5.90 | −8.86 | 9.8 / 0.28 | 14.1 / 0.30 | −13.54, 11.8 / 0.23 |
| kick, snare, toms | −5.62 | −4.99 | 7.4 / 0.50 | 8.0 / 0.54 | −8.81, 7.2 / 0.42 |
| hat | −1.93 | −2.97 | 3.8 / 0.79 | 5.9 / 0.58 | −7.65, 6.4 / 0.54 |
| cymbals | −0.80 | −0.85 | 2.3 / 0.84 | 2.7 / 0.84 | −3.63, 6.0 / 0.55 |

The old generator's parts are the most "likely" of all under the shared
idiom: roots on the beat, a kick and a snare. The new parts sit between
them and FFVI's real ones in bits and match FFVI's spread (the cymbals
excepted: the old arrangement has few crashes and a free-written part
rests where the old one did). **The nearest game**, each of 36 games'
own bass table scoring each song: the old basses never nearest FFVI
(median rank 8.5 of 36); the new ones nearest FFVI in 4 of 12, median
rank 2 (`tools/slice1.py`, the table in `slice1.json`). The two caveats
on that test: a real FFVI song's own leave-one-out rank is not yet
measured beside it, and phase 3 found figure tables shared across games,
so a game's own table tells mostly by its vocabulary and recall shares.

**What the slice added:** the bass and the drums only. The melody, the
harmony and arp, the form, the tempo, the mix and the samples are the
old generator's; the drumless songs (the pack's habit, four of twelve)
stay drumless; a written part rests where the old one rested. The twelve
songs, old and new, sit in the listener's folder (`~/Music/bitComposer-dev/Slice 1/`).

**The listening moved to the gold standard** (the listener, 2026-10-22):
not the new part against the old generator's but against the real song,
so the free writing, slice 1's new thing, went onto the Substitution
Check as a third option a part, Original / Written (the first round, the
song's own manner followed) / Free, on the same four songs
(`tools/table_parts.py --free --label free`, the tables fitted on every
other song, the habit drawn from the game's other songs). Three more
things the free logs showed before anything was heard, each fixed:

- The habit's stream was the seed's alone, so four songs on one seed drew
  one habit; it is the song's and the seed's now (`habit_rng`).
- The habit ignored the tempo and the kit: Terra, whose grid the beat
  reader doubles, drew a dense walking bass of fifteen notes a bar, and a
  one-snare kit could draw a dense drum habit. The habit is drawn given
  the tempo band, and the drums' given the kit too (`tempo_habits`,
  `kit_habits`).
- Where no figure passed the habit's envelope and the band's lock
  together (a sparse habit under a band that strikes three shared hits a
  bar), the draw fell back to the song's own bar, which leaked the
  original into the "free" part. The filters now loosen in turn (the
  envelope first, then the lock) and never copy the bar replaced.

The free round as published (seed 1, 60 s): Terra bass medium walking,
250 notes in 74 bars, drums sparse mixed on its one snare; The Decisive
Battle bass medium walking, drums medium varied on its full kit;
Searching for Friends bass medium walking, drums dense mixed on its one
hat; Johnny C. Bad bass sparse roots (the band's lock asking more), drums
dense mixed on its ride. Verdicts in the page's store as
`verdicts/<id>bassfree` and `verdicts/<id>drumsfree`, the first round's
kept beside them.

**The free round heard** (the listener, 2026-10-22): free bass and drums
belong in six of eight; two "nearly", both the bass, with notes that say
one thing: The Decisive Battle's "loses the tune some", Johnny C. Bad's
"flops on its opportunity to do some phrasing around 28 seconds". The
free writer hears the band as hits and energy, never as phrases; that
knowledge comes with the melody's phrases and the arrangement's breaks,
and the bass is to be re-heard then. **Known issue: the phrase-blind
bass.** "Overall it's fine, and way better than anything we could have
generated before": the round passed, the slice moved on.

### Slice 2 (reordered): the accompaniment under the song's own chords (2026-10-22)

The chordal parts, harmony, accompaniment and arp (whichever the song
has), written free under the song's own chords and put onto its own
voices: the rhythm a bar from the bar table (the part's; the cell floor;
the song's mixture; the habit drawn from the game's by tempo), the chord
tones a span from the voicings mixture (part, shape, the richness habit
drawn once a song), the spread from the widths mixture, stacked lowest
first in the lowest voice's register (nearest above for close, every
second tone up an octave for open, each tone an octave more for wide),
the tones laid onto the part's voices lowest first (spare voices double
the stack an octave up, spare tones dropped from the middle; a lone arp
voice cycles the tones); a held part sounds to its next strike, the
others at the song's own sounded share. A pad does not lock to the
band's hits; the accompaniment and arp lock at the drums' share.
`writer.stack`, `writer.upper`, `harness.write_upper` (the part named
"upper", every chordal voice replaced), `tools/table_parts.py --parts
upper`; the pack gains a `voicing_habits` table. On the Substitution
Check as a third switch, Chords (Original / Free / None), the rest stem
now without the chordal voices, verdicts as `verdicts/<id>upperfree`.
What the four drew: Terra a held harmony (sparse repeating, thin) and a
three-voice accompaniment (sparse mixed, rich); The Decisive Battle a
two-voice accompaniment (dense varied, rich); Searching for Friends a
three-voice harmony (sparse varied, thin) and one accompaniment voice
(sparse mixed, full); Johnny C. Bad a three-voice accompaniment (medium
repeating, full).

**Terra's bell** (the listener, 2026-10-22: "that one voice at a high
pitch just sounds like a really high bell or ring, super abrasive; a bug
or a writing choice?"). A bug. Terra's accompaniment voices 4 and 3,
whose own notes sit at midi 56 to 61 and 58 to 68, were written at 63 to
90 and 70 to 94: 235 and 271 of their 318 notes above the song's own
top for the voice, a sample two octaves above where the game plays it.
The cause: the widths table says how wide the whole upper voicing sits
across all the chordal parts (Terra reads "wide" because its pad sits an
octave over its accompaniment), and the writer had turned "wide" into
"lift each tone of the stack an octave more than the last", with a
register cap three octaves over the voice's floor. Fixed: the stack is
close (each tone the nearest above the last), every voice's note is
moved by octaves into the voice's own register (its own notes' 10th to
90th percentile; `writer.in_register`), and the spread between parts is
left to where their voices already sit (a real song's given; a generated
song's the pack's registers). The widths table is measured but no longer
drives the writer. Terra after the fix: no written note above any
voice's own top; the pad on 68 to 78 against its own 71 to 78. The four
songs rewritten and the page republished.

**The Decisive Battle's chop** (the listener, 2026-10-22: "super choppy
and staccato, which seems off for that voice"). The writing, in two
places, not the voice: the song's own accompaniment is two voices of
staccato sixteenths (15 and 19 strikes a bar, notes of 0.20 beats, the
same looping sample), as short and dense as the written one (11 a bar,
0.20 beats), but it *moves*, each voice running through the chord's
tones; the writer restruck the same stacked chord on both voices, which
is a machine gun. The voicings table says which tones sound in a span,
and nothing in phase 3 measured how a part travels through them in time.
And the free figures came from other songs' bars with no check against
this song's grid: positions on twelfths and thirty-seconds in a song on
sixteenths, heard as stutters. Fixed: (1) a free-written figure must sit
on the song's grid (FreeManner takes the division; the bass and the drums
too); (2) **the motion habit**, an upper part's share of strike times
whose pitches differ from the strike before's, in thirds (block, mixed,
arpeggiated; `rhythm.upper_motion`), a table in the pack (`motions`, by
part) and drawn once a song given the tempo band, realized by walking
each voice along the stack a step a strike (half a step for mixed), the
voices interlocking. The four drew: Terra's accompaniment mixed, its pad
arpeggiated; The Decisive Battle arpeggiated; Searching for Friends' pad
arpeggiated, its accompaniment mixed; Johnny C. Bad arpeggiated. The
grid check also changed the free bass and drums (Johnny C. Bad's bass
186 to 145 notes, its ride 562 to 324 hits: the off-grid figures gone),
so all twelve free stems were republished. This is the first piece of
slice 4's question, how a part moves through its tones, which the melody
needs in full.

**Johnny C. Bad "doing its own thing"** (the listener, 2026-10-22: "having
a hard time following the tune"; Terra, The Decisive Battle and
Searching for Friends' chords passed). Measured: the written
accompaniment sat a semitone from a sounding melody note in 17 % of its
notes against the song's own 7 %. Two causes. The voicings table holds
spans where a part sounds no chord tone at all ("+" alone: 4.6 % of the
games' accompaniment spans, the chord reader's noise where the part
plays blues colour the reader's shapes do not name; Johnny's own
accompaniment reads 29 % "other"), and one such draw, repeated by the
urn, gave six bars of nothing but a ninth. And the writer never looked
at the tune. Fixed: a written voicing must hold a chord tone (`voiced`;
"+" only beside one), and a tone that would sit a semitone from what the
melody or counter-line sounds at that moment moves to the nearest other
tone of the voicing (`unclashed`; the band-awareness rule the bass has
for hits, here for pitches; in a generated song the parts written
earlier are the tune to avoid). Johnny after: clashes 8 % against the
original's 7 %, no chordless voicing; the four songs' chords rewritten
and republished. Heard: "much better".

**The 28-second stretch** (the listener, 2026-10-22: "all the free
styles seem to struggle in the 28 sec part on that song"). An
arrangement event, not a phrase one: from bar 13 Johnny's band drops to
a drum feature for four bars (the accompaniment from 22 to 37 strikes a
bar to 1, the bass from 6 to 1 or 2, the counter-line from 6 to 1, the
drums up from 10 to 20) and the free parts played through it: the free
writer's density was the habit's, the moments rule holds only drops of
two bars or less (a longer quiet stretch in this very song was a section
to write, phase 3 found), and the form reader sees no boundary there.
**Fixed: a free-written pitched part follows the band's energy bar by
bar** (`harness.band_energy`: level x sounded length of every other
voice, the drums left out, since a drum feature is still a breakdown for
the pitched parts, against the song's median; `writer.thinned` scales
the habit's strikes to it; under THIN 0.05 the bar rests; and in a
thinned bar the band's shared hits are not locked to, since the ladder
otherwise dropped the envelope to meet the drums' fill and wrote eight
strikes where the band had one). Johnny after: the bass 1 strike a bar
through bars 13 to 17 where the band sits at 0.30 of its median, the
accompaniment 1 to 2; Terra's intro bars thin the same way. A
band-reading rule, so it carries into generation, where the parts
written earlier set the energy; the arrangement slice adds the table
version for songs with no band yet. The bass and chord stems of all four
songs republished. Heard: Johnny "better, the harmony and bass play a
couple of notes along and the drums take the show" (as the original
does); Terra "very off: strums a handful of chords, many off pitch, a
spazz near the end".

**Terra's handful of chords, off pitch, and the spazz** (2026-10-22).
Four causes, found in the numbers before anything was changed, none of
them Terra's: (1) "thin" was any bar under the band's median, half the
song by definition, so the writer dropped its lock in half the bars and
nothing lifted the sparse habit it had drawn; now a breakdown is under
half the median (BREAKDOWN). (2) The filter ladder dropped the density
limit before the lock, so a bar whose band struck more shared hits than
the habit allows got the one figure that strikes them all: Terra's bass
bar 39, sixteen sixteenth-note fifths, the spazz; the ladder now gives
up the lock before the density, a part keeps its habit and locks where
it can. (3) The voicings' "+" was realized as a ninth in block chords,
the off pitch; Terra's own accompaniment plays a non-chord tone 4 % of
the time and the table's "+" is mostly the chord reader's mislabel, so a
written voicing realizes its chord tones only. (4) The habit itself: the
accompaniment drew "sparse mixed" for a part that is 62 % of Terra's
band, and the readings say that never happens: **a part's density
follows its weight in the band** (its share of the pitched strikes;
`rhythm.part_weights`: an accompaniment that is the main part is dense
in 76 % of songs and sparse in 1 %, a minor one sparse in 40 %; the bass
alike), so the habit is drawn given the part's weight and the tempo
(`rhythm.habits` carries both; the pack's `habits` and `bass_habits`
tables take the shape part+tempo+weight; the drums keep tempo and kit).
And drawn from every game's songs rather than the song's game: phase 3
found the figure habits shared, and a game's own songs are too few by
tempo and weight (FFVI has one fast song whose accompaniment is its
main part, so Terra, read fast by the beat reader's doubling, backed off
to eight songs and drew a 5 % outcome). Terra after: the accompaniment
dense mixed at nine to twelve strikes a bar, the bass two strikes where
it spazzed, no ninths. All twelve free stems of the four songs
republished (every habit redrawn). The open question the pack path
keeps: a generated song draws from its pack's tables alone, and a thin
pack will meet the same thinness; the product may carry the shared
tables as a floor (the plan's open question).

**Johnny C. Bad's chords "repetitive and off pitch"** (the listener,
2026-10-22, after the round above; Terra's chords passed). Measured: the
rhythm was as varied as the song's own (23 distinct bars of 38 against
27, the ostinato share 0.24 for both), but the voicings were 9 distinct
over 38 bars, the commonest "5 +" and "7 +", which the chord-tones-only
rule had reduced to a single tone: twenty bars arpeggiating one pitch
class, and a bare seventh is the "off pitch". The richness habit had
drawn "full" (two tones), with the table's "+" counted as one; a written
voicing now holds its richness in chord tones (`voiced(outcome, tones)`,
RICH_TONES thin 1 / full 2 / rich 3, capped at the part's voices), the
"+" counting for nothing. And voice 4, which plays one note all song (a
G sharp pedal under the comping), had been given moving chord tones in
the bass register, a second moving low line against the bass: a voice
whose own register is PEDAL_VOICE (2) semitones or narrower is a pedal
and keeps its note, struck on the figure. Johnny after: voicings R 7, R
5, R 5 +, R 3 5, R 3 7; voice 4 on its G sharp; the upper voices on E,
B, G sharp, C sharp and A against the original's C sharp, B, D sharp and
E, A, G sharp; clashes with the melody 11 % (the fuller voicings have
more tones to clash; the original 7 %). **Known limitation, the chord
reader on blues harmony:** in 8 of Johnny's 38 bars the song's own
accompaniment mostly plays outside the chord the reader named (dominant
sevenths with blue notes over them), and a written chord follows the
reader, so in those bars it is the wrong chord by any writing. Reader
work, not writer work; the melody slice does not touch it. The four
songs' chords rewritten and republished. Heard: "that's good"; the
chords round closed on the listener's word (no verdict rows clicked for
the chords; the free bass and drums stand at six belongs and two nearly).

**Slice 2 closed (2026-10-22).** Carried as known issues: the
phrase-blind bass (re-hear after the melody and arrangement slices); the
chord reader on blues harmony. Next: slice 3 in the reordered plan, the
melody: its moves table counted first (phase 3 never did), then phrases
written free from contour, peak, ending and relation, on the Substitution
Check as a Melody switch, with the tune-copy check against the reference
set.

### Slice 3 (reordered): the melody (2026-10-22, begun)

**The moves table, counted.** The unit is a move of the tune, note to
note within a four-bar phrase (phrases.py's tune: the melody's line, the
counter-line's where it rests), its outcome the interval in semitones
signed, beyond an octave folded (`phrases.move_units`): 171,905 moves of
1,366 songs, 27 outcomes. Held-out bits a move (share votes, discount
0.75, the games split): none −3.75; **the move before −3.43 (+0.32), as
the song's mixture −3.31 (+0.43)**; the tone the note left stands on
(root, third, fifth, other, none) as the mixture −3.45; the phrase's
contour, its quarter, the beat's strength and the song's stepwise habit
each within 0.01 of the mixture alone (−3.47): the phrase's shape is a
target the moves serve, not a predictor of each move, as the vocabulary
guessed. A game nothing (by the songs' split −3.54 against −3.48). Draws
under the chain and the mixture: 11.9 distinct intervals a song against
11.9 real, the repeat share 0.29 against 0.33. **Kept:** part+mode+previous
as the song's mixture (in the pack as `moves`).

**The melody written free** (`writer.melody`, `harness.write_melody`,
`tools/table_parts.py --parts melody`). The rhythm a bar from the
melody's bar table (the habit drawn by tempo and the part's weight; no
lock, the tune leads; rests where the song's tune rests). Phrases of
four bars over the form's parts (a leftover joining the phrase before).
For each phrase: its relation to the one before from the relations
mixture (repeated: the phrase again; moved up or down: shifted a scale
step; answered: the rhythm kept, the tune new; new: both new), its
contour from the contours mixture, its ending from the endings mixture.
The tune then note by note from the moves mixture, the move before as the
chain, each move kept in the voice's register, in the scale on the beat,
off any semitone the chordal parts sound at that moment, and steered
toward the contour's thirds (CONTOUR_STEP 2 semitones apart) when the
line strays from them; the last note moved to the drawn ending's degree
where the table named one (1, 3, 5). A phrase whose rhythm and intervals
match a game's phrase in the reference set (`harness.reference_index`,
the song itself excepted) is drawn again, up to COPY_TRIES (12). Each
note's length from the articulation table (held or detached by its
value, the song's articulation habit drawn once). The tune never read:
only where it rests, and its register. On the Substitution Check as a
fourth switch, Melody (Original / Free / None), the rest stem now without
the melody voice; the page opens with the melody free and the other
parts original. The four songs' draws (seed 1): Terra medium varied,
held, phrases all new but the first, mostly level and falling; The
Decisive Battle dense varied, detached, falling then rising; Searching
for Friends sparse varied, held; Johnny C. Bad sparse mixed, held. No
phrase copied a game's (the copy check never ran out its tries).
What to listen for: whether the tune belongs over the real band,
whether its phrases breathe and end, and whether it rings as FFVI or as
a generator.

**Heard** (the listener, 2026-10-22): "definitely sounds like a
generator, doesn't belong over the real band in any of them, closer to
random than anything else; not close to even being a melody; the voice
is right and sometimes the notes hit, but it's kinda just doing
whatever." **Measured**, the song's own tune against the written one,
four songs: repeated notes 1 to 19 % of moves against 50 to 64 %; steps
of a tone or less 35 to 74 % against 83 to 92 %; leaps over a fourth 6
to 21 % against 0 to 4 %; a phrase's range 5 to 12 semitones against 3
to 7; strong-beat notes on chord tones 58 to 68 % against 40 to 60 %;
and no motifs: Terra's own tune echoes an earlier bar 84 % of the time
and a two-bar stretch 74 %, the written 49 % and 15 %. The cause was
the architecture: a tune drawn one interval at a time under filters
(register, scale on the beat, the chords' semitones, the contour)
collapses onto the repeated note, which passes every filter every time,
and never builds a motif, since the urn remembered intervals. The bass
and the drums are written as bar figures through the urn, drawn, kept
and returned to, and that is the mechanism of a tune too.

**Rewritten as bar cells through the urn** (2026-10-22). A bar's cell
is its rhythm and its intervals (`Cell`: onsets, intervals, the first
note's offset from the bar's chord root, the moves as scale steps). For
each bar the urn (`Urn`, on a recall table over the games' tune cells,
`rhythm.melody_cell_units`, by the song's echo habit drawn once a song)
keeps the bar before's cell, returns to an earlier one or makes a new
one; a recalled passage goes on with its next bar (CONTINUE 0.8); a cell
that comes back is re-rooted on the bar's chord, its moves as scale
steps (a sequence), its strong beats on the chord's tones. A new cell's
rhythm comes from the melody's bar table and its notes from the moves
table, each move drawn among the moves that fit (`draw_move`: the
register, the scale on the beat, off the chords' semitones, toward the
contour when the line strays CONTOUR_RANGE 5 from its third) with the
table's weights, chord tones on the beat given CHORD_ON_BEAT 0.65 of the
mass, and the repeated note's share held to the song's repeat habit
(REPEAT_RATE rare 2 %, some 12 %, many 35 %: the games' quartiles are
5 % and 30 %, the median 13 %), drawn once a song like the stepwise
habit (the moves table's shape gained the habit: part+mode+habit+previous).
The phrases over the form, their relation, contour and ending, the
ending's degree, the copy check and the articulation as before. The
register is the tune's whole ambitus (its 10th to 90th percentile had
held Terra to seven semitones). Six rounds of measuring, each caught by
the numbers before a note was heard: the chain's stickiness on the
repeated note; the register; the echoed cells landing off the chord
(15 to 27 % of their strong beats on chord tones, fixed by snapping to
the bar's chord: 69 %); the snapping creating repeats (kept a move a
move); the one-note first beat of an echoed cell; the urn's "earlier"
picking a random bar where a tune continues a passage.

**Measured after** (the song's own → the written, seed 1): strong-beat
chord tones Terra 68 → 82 %, Decisive 67 → 69, Friends 67 → 68, Johnny
58 → 49; repeated notes 2 → 17, 1 → 38 (Decisive drew the "many" repeat
habit), 6 → 6, 19 → 5; leaps over a fourth 8 → 8, 21 → 2, 7 → 8, 6 → 22
(Terra and Johnny drew "leaping"); a phrase's range 10 → 10, 12 → 12,
7 → 6, 5 → 10; two-bar echoes Terra 74 → 19 (from 2), the others near
their own. The written tunes now sit inside the games' bands on every
measure; where they sit far from the song's own it is a habit the song
drew (Decisive's many repeats, Terra's leaps), which is the free design
and will be said beside each song. The melody stems republished.
**Awaiting the ear.**

### The integration: whole songs from the pack (2026-10-23, begun)

**What was built.** `translate/whole.py` writes a whole song from a
format-2 pack with no original to follow, and `tools/whole.py` writes
seeds to a directory, renders them, reads them back and prints the
measures beside a game's own songs'. The plan comes first, each draw
from the pack's tables once a song: the key and the tempo (`keys`,
`tempos`); the form, part by part (`sizes`, then `form` by index: new,
again or back; a new part's length from `lengths` under the song's
`length_habits` draw, a repeat as long as the part it repeats; forms
longer than asked drawn again, FORM_TRIES 20), and the loop's bar (after
an intro: a first part the form never comes back to); the band with each
part's weight (`balance`: one of the game's songs' bands with its
weights, one unit a song); the chords, a bar at a time from the chord
mixture (a new part starts the chain's context over, the song's urn goes
on; a repeated part keeps its chords; the loop's first bar from `loops`;
a numeral back to its chord by `chord_of`, the inverse of
`vocab.numeral`); the texture (which parts sound) a part of the form
(`part_textures`); each part's register (`registers`: the melody's its
whole ambitus, the others' 10th to 90th percentile), sounded share
(`sounds`) and habits (the drums' each group's own, `drum_group_habits`
given the kit's). Then the parts are written in turn by the free writers
on a `rhythm.Song` built from the plan (bars of four beats on a grid of
twelve, the chords as spans, the form as the reader's parts), each
writer taking the plan's bars to play (`plays`) where it read an
original's: the drums, the bass, the upper parts, the melody, the
counter-line (the melody writer with `role`, clear of the melody). Each
part reads the band written before it: its shared hits to lock to and
its sounding tones to stay clear of; the band's energy is not read (the
texture is the arrangement; a part the plan has play alone plays). Last
the notes become a `convert.Score` on the pack's samples (`samples_for`:
the lead, harmony, arp and bass pools as the generator uses them, the
kit by piece; the echo as the pack's habits give it, as `score.of_song`
read the generator's), rendered by the converter's back end, and read
back by the readers on the plan's own beat with the plan's roles pinned
(`read_back`) for the measures (`measures`, `tune_measures`: the same
numbers over a written song and a game's).

**Tables added to the kept set** for this: registers, keys, tempos,
weights, sizes, length_habits, balance, sounds, articulation (the
melody's value habit, which `write_melody` had drawn from a table the
pack did not carry, "mixed" assumed), part_textures, drum_group_habits,
chord_tones and contour_sizes. The FFVI pack rebuilt with all 48.

**Hand-set here** is the rendering, not the writing: the voices' levels
and pans (LEVELS, PANS), how the eight voices are shared out (the drums
two, the harmony up to three, the accompaniment up to two: `allot`), the
pool a part's sample comes from (POOLS), a drum hit's length (to the
next hit on its voice, a beat at most). These wait for the product's
mixing, not the tables.

**The first twenty songs, read back beside FFVI's 67** (the quartiles a
quarter under / the median / three quarters; `tools/whole.py --db`):

| measure | written (round 1) | FFVI's own |
|---|---|---|
| bars | 12 / 28 / 35 | 20 / 29 / 36 |
| seconds, once through | 48 / 80 / 122 | 55 / 70 / 93 |
| band (parts with notes) | 4 / 4 / 4 | 4 / 5 / 5 |
| form parts the reader finds | 1 / 1 / 4 | 2 / 4 / 6 |
| drums: strikes a bar | 10.4 / 12.0 / 13.4 | 3.0 / 6.9 / 12.3 |
| drums: share of bars played | 0.58 / 0.74 / 1.00 | 0.75 / 0.93 / 1.00 |
| bass: strikes a bar | 2.9 / 3.8 / 6.6 | 2.9 / 4.3 / 6.0 |
| bass: distinct bars in 32 | 2 / 4 / 6 | 3 / 8 / 13 |
| accompaniment: strikes a bar | 4.8 / 8.0 / 9.3 | 4.8 / 6.3 / 8.5 |
| accompaniment: bar repeats the one before | 0.34 / 0.60 / 0.92 | 0.14 / 0.32 / 0.71 |
| accompaniment: distinct bars in 32 | 1.8 / 2.5 / 5.3 | 4 / 8 / 15 |
| melody: strikes a bar | 2.9 / 3.2 / 3.8 | 3.2 / 4.5 / 6.1 |
| tune: strong-beat notes on the chord | 0.62 / 0.75 / 0.84 | 0.48 / 0.56 / 0.68 |
| tune: range, semitones | 7 / 12 / 19 | 14 / 21.5 / 26 |
| tune: repeated notes | 0.13 / 0.20 / 0.29 | 0.04 / 0.12 / 0.22 |
| tune: steps among moves | 0.54 / 0.68 / 0.78 | 0.60 / 0.67 / 0.75 |
| tune: distinct bar cells in 32 | 7 / 10 / 17 | 8.8 / 12.5 / 18.3 |

**The causes found, each in the readings before the change:**

- *The texture flipped bar by bar.* The bar-level texture mixture (which
  parts sound, after the bar before's) had the band in and out every bar
  or two: the urn's "earlier" share returns to a texture played before,
  and with two textures in the song it flips between them. In the
  readings a part of the form keeps one texture: the modal texture covers
  a median 100 % of a part's bars (quartiles 0.86 / 1.0 / 1.0, a mean
  0.91; FFVI 0.75 / 1.0 / 1.0, 0.86); a part has a median 1 distinct
  texture (mean 1.4); the first bar differs from the modal texture in 12 %
  of parts (an entrance); texture runs a median 2 an 8-bar part. So the
  plan draws **a texture a part** (`part_textures`: the modal texture by
  the part's place in the form and the part before's), a bar's texture its
  part's. Left for later: the 12 % of parts whose first bar is an entrance.
- *The drums struck twelve positions a bar against FFVI's seven.* Every
  drum group (kick-snare-toms, hat, cymbals, other) wrote every bar the
  plan had drums in, under the kit's habit, and a group's figure may not
  rest (FreeManner refuses a rested bar). In the readings the groups'
  habits differ from the kit's and from each other: under a dense kit the
  cymbals and the other sounds are "sparse" (FFVI: 7 of 8 cymbal groups
  sparse), and a sparse group rests in six to nine bars of ten (rest share
  by group habit: sparse repeating 0.66 to 0.81, sparse mixed 0.58 to
  0.61, dense 0.04 to 0.11). So the plan draws **each group's habit given
  the kit's** (`drum_group_habits`), and a group of a planned song **may
  draw a rested bar** at its table's rate (FreeManner `rests`, on only
  with `plays`: substitution's free drums are as they were).
- *No counter-line.* FFVI has one in 52 of 67 songs; the written band
  was four parts to FFVI's five. The phrase tables count both lines as
  the tune's (`phrases.ROLES`, labelled melody), the rhythm, value and
  habit tables have the counter's own rows: **the melody writer writes
  the counter-line** after the melody (`role`), clear of the melody as
  well as the upper parts, in the counter's register and habit.
- *The tunes sat on the chord three beats in four, FFVI's two in four,
  and spanned an octave against nearly two.* CHORD_ON_BEAT 0.65 was a
  constant from the games' band, and an echoed cell's beats were always
  snapped onto the chord; CONTOUR_STEP 2 semitones a third was
  `phrases.LEVEL`, the threshold a contour is heard at, not how far one
  goes. Now **a chord-tone share drawn once a song** (`chord_tones`:
  FFVI's median 0.56) weights the moves and gates the snapping (an echoed
  cell's beat is snapped only while the tune's share so far is under the
  song's), and **a phrase's contour goes as far as the contour-size table
  draws** (`contour_sizes`, by shape and mode).
- *The accompaniment and the bass had a quarter of FFVI's distinct bars
  and twice its repeats.* The lock: shared hits were counted among the
  voices written so far, and with two drum voices and a bass written the
  kick-and-hat coincidences on every beat passed TOGETHER (0.67), so the
  accompaniment had to strike most beats and the few figures that did
  came again and again. In the readings a shared hit is a tutti of a
  five-to-seven-voice band. Now a shared hit is counted **against the
  voices the plan has playing in the bar**, written yet or not: a part
  written early locks to nothing, one written late locks to the band's
  accents.

Also: the form drawn is kept whole (drawn again when longer than asked,
rather than cut); the listening renders play the form once and fade
(`--loops 1`, 48 bars at most), a 60-bar form at 75 BPM having run six
minutes with the loop twice.

**Round 2** (the same twenty seeds after the changes, the FFVI pack
rebuilt with 48 tables; FFVI's own in the table above): drums 5.9
strikes a bar (from 12.0; FFVI 6.9); the tune's strong-beat chord tones
0.62 (from 0.75; FFVI 0.56); the counter-line written in 9 of 19 songs;
the band's median 4 parts still (5); the tune's range 12 still (21.5);
the accompaniment's distinct bars 2 (from 2.5; FFVI 8) and its repeats
0.67 (from 0.60; 0.32); the bass's distinct bars 4 (8); the tune's
repeated notes 0.31 (from 0.20; 0.12); the drums' share of bars played
0.58 (from 0.74; 0.93). Each measured against its draw, song by song
(`tools/whole.py`'s JSON records): the accompaniment's distinct bars as
written equal the distinct bars read back (the measure is faithful); a
"rare" repeat habit gave 0.03 to 0.18 and "some" 0.08 to 0.42; the
chord-tone share landed within a tenth of its draw in 13 songs of 18.

**The causes found, round 2:**

- *The mixture is not the collapse.* `tables.simulate_cache` over FFVI's
  own units with the pack's mixtures (the urn run song by song on the
  real contexts): the accompaniment's distinct bars drawn 8.2 against 10.0
  real, the bass's 9.9 against 13.3, the melody's 8.4 against 11.0; bar
  repeats drawn 0.40 / 0.31 / 0.35 against 0.43 / 0.23 / 0.24. A little
  short on variety, nowhere near two bars in 32. A "new" draw made new to
  the song (an outcome not yet played) over-shoots the other way (11.6,
  12.9, 11.4 distinct) and was not taken.
- *The envelope was.* `_free_figures` on a plain 32-bar song with the
  pack's rhythm mixture: under "dense mixed" 2.6 distinct bars with the
  free envelope (strikes a bar 5 to 16 for a dense habit), 5.0 without;
  "dense repeating" 1.8 against 2.9; "medium repeating" 2.2 against 5.0;
  "dense varied" 6.0 against 9.4; the grid filter changed nothing. The
  habit conditions the table already; the second envelope by the habit's
  density (FREE_STRIKES, hand-set tiers) kept only the densest figures of
  a dense song's table, and the urn then fed on those. **FREE_STRIKES is
  now any count** (1 to 64): the table under the habit is the envelope.
- *A plain table's draw went to the vocabulary evenly.* Under absolute
  discounting (0.75 a vote), a table with one vote an outcome (registers,
  balance, textures a part, contour sizes: one unit a song) keeps a
  quarter of its mass at each level and gives the rest down, and below the
  root `Table.draw` picks any known outcome evenly: 56 % of such draws.
  The melody registers drawn had a median width of 14 semitones where the
  table's votes have 20 (FFVI's ambitus median 21.5, the range measure's
  own value). Now **the plain tables are Witten-Bell smoothed** (the
  discount kept for the mixtures and the figure tables, phase 3's
  choice by bits) and **a plan's one-shot draws stay on the data**
  (`Table.draw(floored=False)`: the coarsest level seen draws from its
  votes alone).
- *The textures drawn a part left a band's parts out.* A part's texture
  was drawn among all songs' textures, kept only if inside the band: four
  parts drawn so can all lack the drums the balance gave the song (Whole
  01 lost its drums; "first" parts are 51 % drumless in FFVI, drumless
  songs included). Now a part's texture is counted **against its song's
  band** (`part_texture_units`: ALL, or "no drums melody", the band's
  parts that rest) and drawn so.
- *A planned drum bar rested whole.* With every group drawing its own
  rests, a sparse kit's groups all rested together in a third of its
  bars (Whole 16: 20 bars planned, 8 written). The plan's texture says the
  drums sound in the bar: **where every group drew a rest, the kit's main
  group plays a figure drawn without one** (`writer.drums`).
- *The tune repeated notes at the tiers' hand-set rates.* REPEAT_RATE's
  rare 0.02 / some 0.12 / many 0.35 realized 0.10 / 0.30 / 0.33: the
  echoed cells carry their repeats in, and the tiers were cut at 0.05 and
  0.2. Now **the song's repeat rate is drawn** (`repeat_rates`: the share
  of the tune's moves that repeat the note, one unit a song) and **held**:
  the repeated note gets its share of the mass while the tune is under
  the rate and none while over it (the chord-tone share held the same
  way, its boost off while the tune is over its share).
- *Each phrase started where the last ended.* The tunes used an octave of
  registers 16 to 24 wide: a new phrase's first move came from the last
  phrase's last note, and a moved phrase moved MOVED's hand-set two
  semitones. Now **a phrase sits where the phrase-shifts table puts it**
  against the one before (`phrase_shifts`: the mean pitch against the
  last phrase's, by relation; a moved phrase moved that far, a new one
  starting that far from where the last left off).
- *The reader's form.* The reader found one part in most written songs
  (FFVI: four) because it read a once-through render: it segments by
  repeats and the loop, and the forms drawn are new-heavy (FFVI's form
  table: "new" in 65 to 92 % of parts after the first). The reader's part
  count is now taken on the looped render, as a player hears it; the
  plan's own parts are the form.

**Round 3** (the same twenty seeds after these; the pack at 50 tables):

| measure | round 1 | round 2 | round 3 | FFVI's own |
|---|---|---|---|---|
| band (parts with notes) | 4 | 4 | 4.5 | 5 |
| seconds, once through | 80 | 76 | 71 | 70 |
| drums: strikes a bar | 12.0 | 5.9 | 6.5 | 6.9 |
| drums: share of bars played | 0.74 | 0.58 | 1.00 | 0.93 |
| drums: distinct bars in 32 | 7 | 5 | 7 | 6 |
| bass: strikes a bar | 3.8 | 3.7 | 2.3 | 4.3 |
| bass: distinct bars in 32 | 4 | 4 | 4 | 8 |
| bass: bar repeats the one before | 0.41 | 0.51 | 0.38 | 0.30 |
| accompaniment: strikes a bar | 8.0 | 7.3 | 6.2 | 6.3 |
| accompaniment: distinct bars in 32 | 2.5 | 2.0 | 4 | 8 |
| accompaniment: bar repeats | 0.60 | 0.67 | 0.42 | 0.32 |
| counter: strikes a bar | - | 3.6 | 3.9 | 4.9 |
| counter: distinct bars in 32 | - | 3 | 3 | 10.5 |
| melody: strikes a bar | 3.2 | 3.8 | 4.4 | 4.5 |
| melody: distinct bars in 32 | 4 | 4 | 4 | 9 |
| tune: strong-beat notes on the chord | 0.75 | 0.62 | 0.60 | 0.56 |
| tune: repeated notes | 0.20 | 0.31 | 0.12 | 0.12 |
| tune: steps among moves | 0.68 | 0.67 | 0.64 | 0.67 |
| tune: range, semitones | 12 | 12 | 16 | 21.5 |
| tune: distinct bar cells in 32 | 10 | 13 | 13 | 12.5 |
| tune: bars echoing an earlier bar | 0.33 | 0.31 | 0.38 | 0.34 |
| the reader's parts (looped render from round 3) | 1 | 1 | 2 | 4 |
| the reader hears the loop | - | - | 1.00 | - |

The habits drawn match the pack's (bass medium walking 9 of 18, FFVI
0.40; accompaniment varied 13 of 19, FFVI 0.46; melody medium varied 9
of 19, 0.46). What the tune does note to note now sits on FFVI: chord
tones, repeats, steps, leaps, its cells and echoes; its range is two
thirds of the way. The drums and the accompaniment's density and
presence sit on FFVI. Still short: the distinct bars of every rhythm
part (bass 4, accompaniment 4, counter 3, melody 4 against 8, 8, 10.5,
9), the bass's density (2.3 against 4.3), and the reader finds two parts
where it finds four in FFVI (the plan's parts are 2 to 8; the reader
hears every loop now).

**The causes found, round 3** (the mixtures run free, `freerun2.py` on
Ragnarok: from START for 32 bars under each habit, as the writer runs
them, beside FFVI's own songs of that habit):

- *The urn's "same" sat on top of the chain's.* Under a "varied" habit
  the free run repeated a bar in 0.31 to 0.37 of its bars where FFVI's
  varied songs do in 0.09 to 0.19, with half their distinct bars: a "new"
  draw from the table could hand back the bar before at the chain's own
  rate, on top of the recall table's "same" share, though `recall_units`
  had counted the three as a partition. **A "new" draw is now new to the
  song** (an outcome not yet played; one played only when none new passes
  the keep). In-sample over FFVI's real contexts (`sim_cache.py`) that
  draw gives the bass 12.9 distinct bars a song against 13.3 real (the
  old draw 9.9), the melody 11.4 against 11.0 (8.4), the counter 12.2
  against 11.2 (8.6); the accompaniment 11.6 against 10.0 and the
  kick-snare group 11.3 against 7.8, over the song's full length, where
  a real song's new bars come early and thin out (the recall shares are
  one rate a song).
- *The floor's runs and the tail.* With the floor counted, a sixth of
  the figure draws came from the cell floor, whose cell-by-cell bars the
  manner refuses unless some song played them whole; and absolute
  discounting (0.75 a vote, phase 3's choice for held-out bits) had given
  the figure tables' long tail, a bar one song played with a small share,
  wholly to that floor. So a "new" bar was mostly a common bar again, and
  a dense habit struck as a medium one (the floor knows no habit: free
  run, dense varied accompaniment 5.7 strikes a bar against 8.7, dense
  walking bass 5.4 against 8.5). **A pack's tables are now Witten-Bell
  smoothed throughout, and a mixture's new draw and the writers' fallback
  draws stay on the coarsest level seen** (`Table.draw(floored=False)`):
  a bar some song played, weighted as the game plays it, the tail in. The
  floor stays for likelihoods.
- *"same" by place.* A part's first bar repeats the bar before less than
  its other bars (FFVI: accompaniment 0.40 against 0.46, bass 0.28 against
  0.36, melody 0.17 against 0.27, counter 0.21 against 0.30): real, small,
  left for later (the recall shape is part+habit).

**Round 4** (the same twenty seeds after these; written / FFVI's own,
medians): bass strikes 4.8 / 4.3, distinct bars 8 / 8, repeats 0.25 /
0.30; accompaniment strikes 6.1 / 6.3, distinct 7 / 8, repeats 0.31 /
0.32; counter strikes 5.5 / 4.9; harmony strikes 1.4 / 1.2; the band 5 /
5; tune chord tones 0.62 / 0.56, repeats 0.11 / 0.12, cells 12.5 / 12.5,
echoes 0.32 / 0.34, leaps 0.08 / 0.05, range 15 / 21.5; the bass and the
accompaniment sit on FFVI on every measure. Two came apart or stayed
short, each a cause of the same kind as before:

- *The drums: 11.9 strikes a bar, 20 distinct bars in 32, repeats 0.03
  (FFVI 6.9, 6, 0.32).* The four groups (kick-snare-toms, hat, cymbals,
  the rest) each drew their own new bars; with the draws on the data and
  new to the song, the kit changed in nearly every bar. The earlier
  rounds had hidden this: a discounted "new" draw mostly handed back a
  common bar, so the groups rarely changed. A kit repeats and varies as a
  whole: **a planned song's kit is now one figure from a whole-kit
  mixture** (the "drums" table, kept beside the groups, which the
  substitution harness keeps using).
- *The tune's rhythms: 3.5 distinct in 32 (FFVI 9), a bar's rhythm the
  one before's in 0.40 of bars (0.10), while its distinct cells (rhythm
  and intervals) were FFVI's 12.5.* A new cell drew its rhythm through
  the rhythm table's own urn (same / earlier / new again), which handed
  new cells old rhythms. **A new cell now draws a rhythm new to the tune**
  (`Cache.draw_new`: the "new" draw alone; the cell urn is the tune's one
  urn).
- *Steps among the tune's moves fell to 0.52 (round 3: 0.64; FFVI 0.67).*
  Not yet run down: the joins between cells grew more frequent as the
  cells grew more various, and an echoed cell is re-rooted within a
  tritone of the last note. To measure after the two changes above.

**Rounds 5 and 6.** Round 5 had the kit worse still (13 strikes a bar,
20 distinct bars, no repeats): the whole-kit group's figures were drawn
under a part name the table had never seen ("drums-KShtco"), so every
level backed off and the floor invented every bar; the kit table's part is
"drums" (`writer.drums`, `part_of`). Round 6, with that: drums 8.7
strikes a bar, 10 distinct bars in 32, repeats 0.25 (FFVI 6.9, 6, 0.32):
whole bars again, a little busier and more various than FFVI's (a "new"
draw at one rate a song gives 8 new bars in 32 where a kit's new bars come
early and stop). The tune after a new cell always took a new rhythm:
distinct rhythms 6.5 (FFVI 9, from 3.5), repeats 0.11 (0.10), strikes 5.0
(4.5); but its distinct cells 17.5 (12.5) and echoes 0.26 (0.34): too
various now. In the readings a new cell takes a rhythm new to the tune in
77 % of cases, the bar before's in 10 %, an earlier one's in 13 % (FFVI
79 / 7 / 14): **a new cell's rhythm is drawn by that table**
(`cell_rhythms`, `rhythm.new_cell_rhythm_units`). Steps 0.60 against 0.67
and leaps 0.09 against 0.05 stay a little off; measured on the written
notes, the read-back agrees to the hundredth (seeds 1-4), and the leaps
sit at phrase starts (0.10 of their moves) and bar joins (0.04), inside a
bar 0.02.

**Round 7** (the same twenty seeds; the pack at 52 tables; medians,
written / FFVI's own):

| measure | written | FFVI | | measure | written | FFVI |
|---|---|---|---|---|---|---|
| band (parts with notes) | 5 | 5 | | tune: chord tones on the beat | 0.63 | 0.56 |
| seconds, once through | 71 | 70 | | tune: repeated notes | 0.12 | 0.12 |
| bass: strikes a bar | 4.8 | 4.3 | | tune: steps among moves | 0.58 | 0.67 |
| bass: distinct bars in 32 | 8 | 8 | | tune: leaps among moves | 0.09 | 0.05 |
| bass: bar repeats | 0.25 | 0.30 | | tune: distinct cells in 32 | 15 | 12.5 |
| accompaniment: strikes | 6.7 | 6.3 | | tune: bars echoing an earlier bar | 0.23 | 0.34 |
| accompaniment: distinct | 7 | 8 | | tune: range, semitones | 14 | 21.5 |
| accompaniment: repeats | 0.31 | 0.32 | | melody: strikes a bar | 5.1 | 4.5 |
| counter: strikes | 5.3 | 4.9 | | melody: distinct rhythms in 32 | 5 | 9 |
| counter: distinct | 6 | 10.5 | | melody: bar repeats | 0.14 | 0.10 |
| counter: repeats | 0.15 | 0.13 | | drums: strikes a bar | 8.7 | 6.9 |
| harmony: strikes | 1.4 | 1.2 | | drums: distinct bars | 10 | 6 |
| the reader's parts (looped) | 2 | 4 | | drums: bar repeats | 0.25 | 0.32 |

**Where the integration stands (2026-10-23).** The bass, the
accompaniment, the counter-line's density and repeats, the band, the
length, the tune's chord tones and repeated notes sit on FFVI's numbers.
Still off, each with its cause named: the tune's echoes (0.23 against
0.34: an echoed cell re-rooted on a new chord and snapped is no longer the
same cell, so the urn's "earlier" draws come out as variants; real echoes
are exact), its steps and leaps (0.58 / 0.09 against 0.67 / 0.05: the
leaps sit at phrase starts, the shift table's draw taken as a jump, and
at bar joins), its range (14 against 21.5), the melody's distinct rhythms
(5 against 9, the counter's 6 against 10.5); the kit a little busy and
various (a kit's new bars come early and stop; the urn's one rate a song
does not); the reader finds two parts where it finds four in FFVI. Open
too: the band's energy is not read in generation (the texture is the
arrangement); the 12 % of parts whose first bar is an entrance; the
within-bar chord changes (`changes`) and cadences unused; the counter is
a second tune, not a response line; the lock acts on no part now (the
upper parts see too few voices written, the melody writer takes no lock);
the rendering's levels, pans, voice allotment and sample pools are
hand-set. Twenty songs a round are at Ragnarok
`~/diags/bitcomposer/idiom/phase4/whole/round7/` (a module and a record
a seed); the Song Check page is to be designed with the owner before it
is built.

What the integration added, for the ear: whole songs with no original
under them, every part free on a skeleton the tables gave (key, tempo,
form with its repeats and loop, a band with its balance, chords a bar, a
texture a part), the kit as one figure, the counter-line, the tune's
chord-tone and repeat rates and its phrase shifts and contour sizes from
the game's songs, and a pack's tables drawn on the data.

### The Song Check, first notes (2026-10-23)

Twenty whole songs on a page (per-part switches, a verdict and a note a
song; verdicts in its store). Song 4 in, the owner's word: "definitely
Final Fantasy, and much better than our other generator, in song
diversity alone and nuance". Ten notes asked bug or writing. Run down in
the tables, two causes behind most of them:

- *A part's register from another part's.* Whole 04's counter at midi
  32 to 44, Whole 05's harmony at 28 to 36 (four octaves under its
  sample: the loop crawls and the baked-in vibrato slows to a warble),
  Whole 08's arp and Whole 12's counter likewise; Whole 19's bass at 56
  to 60 above its accompaniment at 28 to 36; Whole 13's bass at 44 to 68.
  Under Witten-Bell a table keyed by part keeps only 50 to 68 % of a
  register draw at the part's level and gives the rest to the root, where
  every part's registers are mixed: a counter drew a bass-depth register
  in 7.6 % of draws (its own level: never), a bass a floor above middle C
  in 18.6 % (own level: 1.5 %). The sounded shares and habits went the
  same way. **A plan's one-shot draw now stops at the part's level**
  (`Table.draw(floor_k=1)`) and passes over a finer level a single song
  stands behind (`min_songs` 2). **The balance table now carries each
  part's register and sounded share**, so a song's layout is one FFVI
  song's whole (the bass under the accompaniment under the tune), and
  **a pitched part's sample is one the game played in that register**
  (`ranges`, by sample id: the readings' sample keys are the pack's ids).
- *A figure table forgot the habit.* The bass's habit level kept 5 to
  21 % of draws (seven "sparse roots" songs), the rest the whole game's
  bass bars of every habit; so Whole 13's "sparse roots" bass wrote 310
  notes, two of them tremolo bars the reader had kept as figures (44
  strikes). The free-run numbers had shown it (sparse habits at 4.5
  strikes a bar against 1.5, dense under theirs) and were misread. **A
  chain's draw now backs off from the bar before when thin but never
  past the part, meter and habit** (`Table.chain_floor`), and **rolls are
  dropped from the figure tables** (`rhythm.is_roll`: over six strikes a
  beat on a pitched part, over four a beat on one drum piece; 17 of
  FFVI's 715 bass bars). After: sparse roots 2.1 strikes a bar (real
  1.5), sparse walking 1.9 (1.7), dense walking 8.4 (8.5), dense roots
  10.3 (14.2).

Writing, not bugs: Whole 01's one-note accompaniment (a 56-56 register,
a real FFVI drone accompaniment, on a two-voice "full" part: the pedal
rule holds both voices to the note); Whole 10's run of notes in its last
bar (a real fill bar); Whole 16 (thin high accompaniment, a sparse bass
at 60 BPM, a chord sequence with reader artifacts); Whole 17's 28 seconds
(a five-bar A and a two-bar B drawn from tables that hold FFVI's jingles;
the render plays the form once).

**Rounds 8 and 9** (after the fixes; FFVI's own in the earlier table):
drums 7.1 strikes / 6.5 distinct / 0.29 repeats (6.9 / 6 / 0.32); bass
4.3 / 6 / 0.26 (4.3 / 8 / 0.30); accompaniment 6.4 / 6 / 0.35 (6.3 / 8 /
0.32); counter 4.9 / 3 / 0.15 (4.9 / 10.5 / 0.13); tune chord tones 0.64
(0.56), steps 0.61 (0.67), leaps 0.07 (0.05), repeats 0.17 (0.12), cells
12.5 (12.5), echoes 0.27 (0.34), range 14.5 (21.5: round 8 had 8, the
balance having taken the melody's 10th to 90th percentiles; its whole
ambitus restored). The counter's distinct bars fell from 6 to 3 with the
habit floor and are not yet run down. For listening rounds `--min-bars`
draws a form again under a length (12 bars for the second set: the
first drew three songs of three to four bars, FFVI's jingles).

### Depth: the orchestration FFVI has and the written songs lacked (2026-10-23)

The owner's second-set note: the songs sound like FFVI but not like its
epic ones; "little pieces, not epic orchestration", though a song like
Terra is simple and only fills the space. Measured on FFVI's 67 songs
against the written twenty (`fullness.py`, `coverage.py` on Ragnarok):

- FFVI uses all eight voices in every song; at any instant a median 6.7
  notes sound (quartiles 5.5 / 8.0; Shadow, Blackjack, Dancing Mad, The
  Decisive Battle at 8.7 to 9.8). The written songs used 6 voices (5 / 7)
  and sounded 4.2 (3.0 / 5.0).
- Not continuity: each part fills as much of the song as FFVI's (bass
  0.83 against 0.85, accompaniment 0.89 against 0.92, counter 0.77 against
  0.84, melody 0.68 against 0.78).
- Depth: FFVI's accompaniment has 2 voices (1 to 3), its counter-line 2
  (1 to 2), its harmony 2, its arp 2; the written songs gave the counter
  and the arp one. And a second voice is a line of its own, not a chord
  tone of the first: apart in 65 % of accompaniments with two voices and
  79 % of counter-lines (`harness.relation`), doubling at a third, fourth
  or fifth in a quarter, alternating in 5 %. The layered basses (13 songs)
  are all apart, mostly in the same register.

So: **the balance table carries each part's voice count** beside its
weight, register and note length (the song's whole arrangement in one
draw; `allot` takes the counts and trims to eight); **the layers table,
generalized to every part**, says what a second voice does ("doubling +4",
"alternating", or "apart" with its register offset to REGISTER_BIN and its
density against the line: sparser, like, denser); and **an apart second
voice is written as a line of its own**: the accompaniment's as a second
`upper` line with its own figures, register and voicing at the measured
density (`habit_near`), the counter's as a second tune clear of the melody
and the first counter, the bass's as a second bass line; a doubling voice
is the line again at the interval, in the scale (`diatonic`). Melody
second voices (rare) are doubled only.

**Round 10** (after; FFVI's own in brackets): notes sounding at once 5.4
(3.6 / 6.4; FFVI 6.7, 5.5 / 8.0), voices a song 8 (6.3 / 8); the
accompaniment 8.4 strikes a bar, 9 distinct bars, repeats 0.20 (6.3, 8,
0.32: two lines' onsets merged count denser than FFVI's two do); the
counter 5.4 / 4.5 / 0.13 (4.9 / 10.5 / 0.13); the bass and drums as
before; the tune's steps 0.59, range 14.5, echoes 0.27 unchanged. The
third listening set (Song Check 3) is written from this.

### The theme: the hook as vocabulary (2026-10-23)

The owner's third-set note: the songs never carry a tune; Whole 14 opens
with a hook it never comes back to; Terra states its tune, goes away,
and comes back to it. Measured (`hooks.py`, `heads.py` on Ragnarok,
FFVI's 65 songs with a tune against the written set):

- Exact repeats are not the difference. Keyed by rhythm and intervals,
  FFVI repeats a four-bar phrase exactly as rarely as the written songs
  do (a median of none heard before in a pass; the opening phrase back
  exactly in 11 % of songs). A hook comes back as its head, varied, and
  through the loop, which the readings cut off and the page never played.
- Where the echoes point is the difference. Both echo an earlier bar in a
  third of bars (0.33 against 0.30), but half of FFVI's echoes point at
  the song's first four tune bars (median 0.50, a quarter of songs above
  0.80; the written songs 0.38, a quarter at none), and in 43 % of FFVI's
  songs a later phrase opens with the first phrase's opening bar (the
  written songs 15 %, none in the median). A part returns after another
  in 29 % of FFVI's forms (ours 15 %). Whole 14 echoed its opening in 44 %
  of its echoes and never at a phrase head.
- The vocabulary had no word for it. A phrase stood only to the phrase
  before (repeated, moved, answered, new: 73 to 78 % new in FFVI), the
  cell urn's "earlier" took any bar by its count, and the form was a chain
  of kinds by index.

Counted and kept, as vocabulary rather than a weight: **the phrase
letters of a part** (`rhythm.phrase_letter_units`: each phrase THEME
where it opens with the song's theme head, the first sounding phrase's
opening bar; AGAIN where it opens with an earlier head; NEW; by the
part's phrase count and its place in the form: a one-phrase middle part
opens with the theme in 19 % of FFVI's, a two-phrase middle part is "T n"
in 43 %), **how much of the theme phrase comes back with its head**
(`theme_body_units`: the whole phrase 35 %, the head alone 30 %), and
**the forms whole** (`letters`, one unit a song: "A B" 24 %, "A B C" 11 %,
"A B C B D" 6 %). The melody writer takes the letters: a THEME phrase
after the first opens with the theme's head again (re-rooted on the bar's
chord), keeps as many of its next bars as the table draws, then goes on
new under a drawn contour and ending; an AGAIN phrase brings back the
last non-theme phrase; a NEW phrase is new or answers the one before. The
plan draws the letters a part for the phrases the tune plays in (an
intro without the tune had taken the theme's place at first) and the
form from the game's own letters. The listening render plays the loop's
first bars once more after the form, fading through them (`--tail-bars
4`), so a return through the loop is heard. The measures gain the theme's
returns (`theme_heads`, `theme_returns`) and the echoes of the opening.

After, by the plan's own count: 8 of 20 songs return to their theme
(FFVI 43 %); read back under the reader's own segmentation (which finds
two parts in the written songs where it finds four in FFVI's) the return
shows in fewer. Round 11: the melody's distinct rhythms 7 (FFVI 9, from
4), range 16 (21.5), chord tones 0.57 (0.56); steps 0.54 (0.67) and the
accompaniment's merged onsets 9.1 (6.3) are the open numbers. The fourth
listening set (Song Check 4) is written from this.

### What comes back with the theme (2026-10-23)

The owner heard the callback in one of the fourth set's twenty (Whole
11) where the plan's letters had eight songs return to their theme, and
asked whether FFVI holds the tune in the melody alone. Measured on FFVI's
46 theme returns, bar for bar against the theme phrase (`theme_band.py`,
`theme_band2.py`): the chords under the returning phrase are the theme's
in 41 % of bars (19 % at any other phrase), the bass's figures in 54 %
(12 %), the accompaniment's bars in 56 % (15 %), the texture no more than
elsewhere (49 % against 44 %). Per return, with half the bars or more
the same: the chords come back in 22 of 46, the bass in 27 of 46, the
accompaniment in 29 of 43; all three together in 17, one of them in 23,
none in 4. The tune itself comes back whole in 14 of 46, three bars in
13, two in 14, one in 5. And the theme travels: another part plays the
theme's head cell somewhere in 12 of 52 counter-lines, 11 of 62 basses,
9 of 57 accompaniments. The fourth set's nine returns had brought the
tune back over new chords in eight (0 of 4 bars the same) and a new
accompaniment in all: a melody event where FFVI's is a band event half
the time, and Whole 11 landed because its form brought B back whole.

Counted and kept: **what comes back with the theme** (`return_band`:
"chords bass accompaniment", "bass", "none"..., one unit a return). The
plan draws it a return: the theme bars' chords are copied under the
returning phrase when the chords come back, and the bass and the
accompaniment copy their own theme bars there when they do
(`song.copies`, applied at the end of `_free_figures` as a form's repeat
is). The theme travelling to the counter or the bass (a fifth of songs)
is left for later. The fifth listening set is drawn from forty seeds,
keeping the songs whose theme returns, each card naming where.

### Round 13: the two switches, carry a theme and the band comes back (2026-10-23)

Decided in `phase-5-packs.md`; built here as conditions on the plan's
draws. `plan(themed=True)` draws the tune's phrase letters again, at most
forty times, until a later phrase opens with the theme; the letters still
come from the game's own table. A plan whose tune has fewer than two
phrases (a part without the tune, then a five-bar part: one window) has
nowhere to come back, and no letter draw can help it, so the plan is drawn
again whole from the same stream, at most ten times; the first set of
twenty burnt forty letter draws on such a song before this was seen.
`plan(band_returns=True)` draws a return again when nothing came back with
the tune; what comes back stays the table's own mix. Both are recorded in
the plan under `options` (`themed`, `band_returns`, `plan_draws`) and in
its log, and `tools/whole.py` takes `--themed --band-returns`.

Song Check 6: the same twenty seeds as every set, both switches on.

- Every song carries its theme back: 20 of 20. Song Check 5, at the table's
  own rate, had 17 of 40.
- 25 returns in the twenty songs, none with the tune alone (FFVI: 4 of 46
  alone; the switch refuses that outcome and nothing else). What came back:
  the accompaniment in 20 of 25, the chords in 18, the bass figure in 16;
  FFVI's 29 of 43, 22 of 46 and 27 of 46. The mix is the table's.
- Eight songs returned on the first letter draw; twelve needed two to nine.
  One song (14) needed a second plan: its first had a one-phrase tune.
- The cost, as the phase 5 plan names it: a short or sparse-melody plan is
  drawn past, so the game's through-composed forms do not appear while the
  switch is on.

Nothing in the writer changed for this round. The tune travelling to the
counter or the bass, the steps, the two-line accompaniment's density and
the reader's parts are as round 12 left them.

### Round 12's open items, investigated (2026-10-23; nothing changed)

Measured on Ragnarok (`phase4/openlib.py`, `ffvi_open.py`,
`written_open.py`, `steps_stages.py`, `steps_roles.py`, `repeat_check.py`,
`ffvi_accomp.py`); the written side is the set 6 options.

**The theme travelling.** In FFVI another part plays the theme's head
cell in 12 of 52 counter-lines (44 places), 11 of 63 basses (46) and 9
of 59 accompaniments (14). In most of those places the tune plays the
theme cell at the same time: the counter in 32 of 44 (25 in the tune's
octave, 5 an octave up), the bass in 29 of 46 (two octaves down in 14,
one to three down in the rest), the accompaniment in 12 of 14. So the
travelling is mostly a second instrument doubling the hook for a bar as
the tune states or echoes it. The hand-off is rare: the counter carries
it over a resting tune in 6 places and over another cell in 6; the bass
carries four bars of the theme phrase in 9 of its 46 places. The songs
whose counter carries it are not the songs whose tune returns (2 of 12).
Our vocabulary has whole-part doubling (`layers`) and a counter written
clear of the tune; it has no word for a part doubling the theme's cell
at its statements, nor for a return carried by the bass. Both would be
new units (a statement: which parts double it; a return: which part
carries it).

**The tune's steps (0.55 against 0.67).** By position, FFVI's moving
moves: within a bar 79 % of them at 0.65 steps, at a bar join inside a
phrase 16 % at 0.61, at a phrase start 5 % at 0.50 (leaps 0.16). Ours:
80 % at 0.59, 16 % at 0.55, 4 % at 0.29 (leaps 0.27). The moves table
itself expects 0.645 steps over the contexts the writer visits, FFVI's
own level; the register filter raises that to 0.69, the clash, scale and
contour filters bring it to 0.658 and the chord weighting on strong beats
to 0.626 (2,313 draws). The drawn within-bar moves came out 0.601 for the
melody and the finished line 0.589 (echoed cells snapped to the chord).
The counter loses far more after its draw: 0.606 drawn, 0.493 finished;
what the writer does to it after the draw is not yet found. At a phrase
start the shift table's draw (where the phrase sits) is taken as the
first move; FFVI reaches it over the phrase. So about three points go to
the chord weighting, one to the other filters, one to the echoes, one to
the joins and one to the phrase starts; the table is not the cause.

**The accompaniment's density (9.1 against 6.3).** FFVI's
accompaniments: 16 with one voice (5.8 strikes a bar), 43 with two or
more (merged 7.3; the line 6.6, the second voice 4.5; 40 % of the merged
onsets struck by both). Ours: one voice 8.7, two or more merged 10.3 (the
line 8.6, the second 6.0). FFVI's habits: dense 30 of 58 (7.4 to 9.1
merged), medium 25 (4.5 to 5.1), sparse 3; our twenty drew dense 10,
medium 8, sparse 1, the same mix. The cause is in the counting: the
figure table's unit is the part's bar with all its voices merged
(`rhythm.units`), so a dense habit's bars hold the 8.5 onsets that in
FFVI are two voices together; the writer gives the whole pattern to the
line and then writes a second line apart with its own habit beside it.
Arpeggiation adds no onsets (`MOTION_STEP` moves a voice along the
stack). Either the line's own bar and the second voice's bar become the
units (new vocabulary), or the merged unit is split between the lines.

**The reader's parts (2 against 4).** The reader finds parts where a run
of two bars or more repeats with 85 % of each voice's notes held, and
joins parts under four bars; FFVI's median part is 5 bars and only 65 of
its 304 parts are letter repeats, so its boundaries come from phrases and
riffs repeated note for note. Our planned repeats (B B) are not note for
note: in ten songs with repeats the melody and the counter copy every
bar, the drums most, the bass's figures copy but its notes differ in a
bar or two of each part (its second line), and the accompaniment copies
nothing (0 of 4, 0 of 6, 0 of 8 bars; the harmony too): the upper writer
has no copy of a repeated part (`_free_figures` copies for the bass and
the drums, the melody writer for the tune). With two to four of eight
voices playing new material the reader hears no repeat and no boundary.
A writing fault, not vocabulary.

### Round 14: the four open items built (2026-10-23, on the owner's go)

Each as the investigation above named it: a writing fault fixed as a
fault, a vocabulary gap given a table.

- **A repeat is a repeat** (`whole.copy_repeats`). A part of the form that
  repeats an earlier one now replays every part note for note, second
  lines and voicings included; the writers had copied their own figures
  only, and the upper writer nothing. The form reader finds the plan's
  parts on the ten songs of twenty that have a repeat (`A9 B4 C7 B4 D4`
  read back as `A9 B4 C7 B4 D4`); the ten without still read as one or two
  parts, and the median stays 2 against FFVI's 4. What remains is FFVI's
  backing repeating itself inside a part as a block (a riff of two or four
  bars in every part at once), which our parts' mixtures do not do
  together: a vocabulary question (the backing's period), put to the
  owner.
- **The line and its second** (`rhythm.line_notes`, `second_figure_units`;
  tables `rhythm` recounted, `second_figures` new). The figure table counts
  an upper part's own line where it holds two voices or more, and a second
  line apart is drawn bar by bar under the line's bar, by the line's
  density class and pattern (the pattern alone backed off to the whole
  part for rare bars and gave a sparse line a dense second). The line's
  density by habit sits on FFVI's (medium 5.2 to 5.9 against 4.9 to 5.2,
  dense 8.4 to 10.1 against 7.6 to 10.5); two-voice accompaniments 10.4
  onsets a bar merged before, 8.6 now, FFVI 7.3; one voice 8.7 before, 6.8
  now, FFVI 5.8.
- **The hook doubled, the theme carried** (`theme_doubling_units`,
  `theme_carrier_units`; `whole.double_theme`, `whole.carry_theme`). Where
  the tune plays its theme cell the table draws which parts play it with
  it and how far from the tune (FFVI: none in 65 %, the bass two octaves
  down most often); a phrase whose tune is not the theme draws a carrier
  (FFVI: none in 99 %). Set 7: the hook doubled in 13 of 20 songs (25
  bars: the accompaniment 11, the bass 9, the counter 3, the harmony 2),
  the theme carried in none, as one phrase in a hundred predicts.
- **Steps.** A new phrase is steered to where the shift table puts it over
  its first third rather than jumped there (phrase-start steps 0.29 to
  0.34; FFVI 0.50), and an echoed cell is moved whole to the start that
  lands the most strong beats on the chord instead of having single notes
  bent (its intervals kept). The counter-line's "loss" after its draw was
  the investigation's own measure merging its two voices; measured on its
  first voice it loses nothing (0.59 drawn, 0.58 finished). The tune's
  steps inside a bar stay 0.58 against 0.65: three points are the chord
  weighting on strong beats, which holds the chord-tone rate; recovering
  them means moves counted by whether they land on a chord tone, a
  vocabulary choice left open.
- **Elsewhere:** the player's music folder renamed on the owner's machine
  (`~/Music/bitComposer`; the code already defaulted there, the old folder
  had won as a fallback); the vocabulary documented, every table with what
  it counts and what it controls (`VOCABULARY.md`).

Song Check 7 is written from this (set 6's options, the same seeds).

### Round 15: the riff and the landing (2026-10-23, on the owner's go)

Two vocabulary expansions, each checked for generality on all 39 games
before it was built (`phase4/period_count.py`, `period_roles.py`).

- **The riff** (`rhythm.period_units`, `period_hold_units`; tables
  `periods`, `period_holds`). A backing part's period inside a part of
  the form: the lag at which its bars repeat (1, 2, 4, 8) or none, counted
  on figures (the bass by its figure, the drums by their pieces, an upper
  part by its pattern), since a riff moves with the chord and keeps its
  figure; on absolute pitches almost nothing repeated, in any game. Held
  share 0.6. FFVI: the bass has a period in 36 % of its parts, the drums
  in 42 %, the accompaniment in 46 % (a 1-bar period in a third of those,
  2 bars in most of the rest); across the 39 games the shares are the
  same kind of number, Mega Man X's included. Inside a period a bar is
  held nine times in ten. The plan draws a period per backing part per
  new part of the form and the held bars; the free figure writer plays
  the bar a lag before again there (re-realized on the bar's chord), and
  an upper part takes its source bar's voicing on the same chord. The
  reader's parts do not move (a riff under four bars is inside a part by
  the reader's own rule); the 4-bar exact-repeat shares rose (drums 0.23,
  bass 0.10, accompaniment 0.04; FFVI 0.15, 0.07, 0.01 by the same loose
  key). A first joint count (every backing part together, 0.75 held) had
  found blocks in a quarter of parts only; the per-part word is the one
  the writers use.
- **The landing** (`moves` conditioned on `place` and `tone`). The moves
  table had counted where the arriving note falls in its beat and the tone
  the note left stands on against the chord since phase 3 without being
  drawn by them. Drawn by them, the tune approaches chord tones as FFVI
  does and the within-bar steps went from 0.58 to 0.67 (FFVI 0.65) with
  no chord weighting at all, but the chord-tone rate fell to 0.48 (0.56):
  the filters shift the chain's balance. The weighting now acts only
  while the tune is under its drawn rate (the repeat controller's
  shape): chord tones 0.57, within-bar steps 0.61. The counted rate is
  held; four points of steps remain.
- Two-voice accompaniments 8.2 onsets a bar merged (8.6 before, FFVI
  7.3). Song Check 8 is written from this.

### Round 16: the feel and the layered bass (2026-10-23, from the owner's notes on set 8)

The owner heard the bass stumble (Whole 10 of set 8) and the crash cymbal
played fast as a constant noise. Investigated first, then built on his
go.

- **The stumble** was two faults in the vocabulary's reach. First, no word
  for the feel: FFVI's bass bars on triplet positions, 18 % of its bars,
  came only from its compound and shuffle songs (Terra, Dancing Mad, the
  Opening Theme's third part, Slam Shuffle), and the figure tables carried
  no mark of that, so a straight song drew a triplet bass bar beside
  straight drums, each part on its own (Whole 10's bass on triplet
  positions in five bars, its drums in thirteen others; nine of nineteen
  songs with a bass had some). Now `feels`: a song's feel, duple or triple
  (a quarter of its onsets or more on triplet positions), drawn once a song
  (FFVI: triple in one song of five) and every figure table conditioned on
  it (`FIGURE` gains `feel`). In twenty written songs, four triple, the
  sixteen duple have no triplet bass bar at all. Some duple songs still
  draw swung drum bars, as FFVI's own duple songs have them (Setzer's kit
  swings in 89 % of its bars over a straight bass): the game's writing.
  Second, the bass's second voice: Whole 10 drew a second bass line
  "apart, same register, denser" and wrote it as a sixteenth-note root
  under a walking line, both busy; FFVI's thirteen two-voice basses are a
  sustained line (three or four strikes a bar, notes near a beat long)
  under a staccato voice (five to twelve strikes, 0.15 to 0.4 beats) in
  the same register. Now the bass figure table counts the sustained line
  (`line_notes` for the bass: the voice with the longest notes), the
  second voice is drawn from `second_figures` under the line's figure, and
  `layer_sounds` gives a layered part's line and second voice their own
  note lengths (upper parts too). Set 9's layered basses: a line of three
  to four strikes near a beat long under a second of five to thirteen
  short ones.
- **The cymbal** is FFVI's writing drawn too often and played on the wrong
  sample. Bars with four or more cymbal hits are 37 of FFVI's 1,334 kit
  bars (Fanatics, Grand Finale), a ride in sixteenths; five of twenty
  written songs had them against four of 67 in FFVI, because the kit is
  drawn as one figure under the kit's habit and the plan's cymbal-group
  habit ("sparse" in every one of those songs) is never looked at: a
  drawing fault, open. And the pack's crash slot holds the built-in SNES
  crash: the pack builder (`translate/pack.py`, the thin pack) keeps the
  six most-struck drum samples and sorts them into pieces by brightness
  and ring, and FFVI's cymbal (in 22 of its 67 songs, struck 561 times)
  ranks eighth; its toms seventh; the slot the builder called the snare
  holds a sample the namer calls a hat, and the true snare (5,690 strikes)
  is not in the kit. The readings know every drum by name. The kit from
  the namer's labels is phase 5's listed item; for the FFVI pack it can be
  built now.
- Measures after this round: chord tones on strong beats 0.56 (FFVI
  0.56), steps inside a bar 0.61 (0.65), two-voice accompaniments 7.7
  onsets a bar merged (7.3), one voice 6.4 (5.8), the reader's parts 3
  (4). Song Check 9 is written from this. Pack: 64 tables.

### Round 17: the kit from the namer's names, the cymbal habit honored (2026-10-23, on the owner's go)

- **The kit.** The thin pack builder (`translate/pack.py`) now names a
  game's drum samples with the drum namer, each measured as the game plays
  it (at its most-played pitch, its loop held as long as the game holds
  it: measured as a one-shot, FFVI's looped snare rang long enough to be
  called a cymbal and took the crash slot), and gives each kit slot the
  most-played sample so named; brightness and ring remain the fallback
  where the namer finds no kick or snare. FFVI's kit before: a hat in the
  snare slot, no tom, no cymbal, the true snare absent. After: kick, snare,
  hat, tom, cymbal, rim and open hat, every one the sample the readings
  name the same way (the snare in 31 readings, the cymbal in 30). The dev
  pack is rebuilt from the 82 SPC files with this kit (26 samples, 64
  tables); the brightness pack is kept beside it.
- **The cymbal habit.** The plan's drum group habits cap each single-letter
  group's hits a bar in the kit draw at its density tier's top (sparse 2,
  medium 6, dense 16; `writer.group_caps`, `free_drum_envelope`); the kit
  drawn as one figure had drawn under the kit's habit alone, and the
  one-letter groups' habits had not even reached it (the whole-song writer
  handed it the kit's habit only). Twenty songs before: four with a bar of
  four cymbal hits or more, eighteen such bars of 415; after: none.
- Song Check 10 is written from this: the first set on FFVI's own snare
  and cymbal.

### Round 18: the second line's tempo and feel, the layered part's samples (2026-10-23, from the owner's note on set 10)

Whole 03's second bass line went "super fast": a 22-strike bar, Dancing
Mad's tremolo bass, which FFVI plays at 60 BPM (5.5 notes a second, its
fastest bass voice) drawn into a 115 BPM song at 10.5 a second, on the
long sustained bass sample. Two words were missing.

- **`second_figures` by feel and tempo.** The second line's table had been
  conditioned on the line's density and figure only; it is counted on
  FFVI's thirteen two-voice basses, so Dancing Mad's 48 tremolo bars were
  a large share of its pool. Now (part, feel, tempo band, density, line).
  Twenty songs' fastest second bass line: 2.3 notes a second.
- **`layer_samples`.** FFVI's layered bass plays on two samples, the
  sustained line on a long one (the same sample in ten of thirteen songs)
  and the busy voice on a short one; the writer had given a part one
  sample a song. The pair is counted once a song per layered part (the
  line's and the second voice's most-played samples, as the pack names
  them) and drawn at rendering; the second voice's notes go to its own
  sample in the score and the stems (`samples_for`, `score_of`). Set 11's
  layered basses: the long sample under the short one, as FFVI pairs them.
- The pack: 65 tables. Song Check 11 is written from this.

### Round 19: a line and its voices, no stack (2026-10-23, from the owner's note on set 11)

Whole 01's accompaniment overpowered the song, most of all in its fast
bars. Not the levels: the voices. The part had drawn four voices; the
writer put three into a block stack, every voice striking at every onset
(arpeggiation only turning which tone each took, spare voices doubling an
octave up), and the fourth apart, so a 24-onset arpeggio bar, one voice's
flourish in FFVI, was three voices hammering 24 times a bar plus a second
line, at the accompaniment's level each. FFVI's accompaniments have two
voices as a rule and they rarely strike together: 1.46 voices an onset in
arpeggiated parts, 1.20 in mixed, 1.19 in block; a busy bar belongs to one
voice. The `layers` word had covered the second voice only; a third or
fourth had no word, so the writer stacked them.

Built: `layers` counted for every voice beside the line, by rank (the
busiest first), and an upper part written as its line (one voice, the
part's figures and voicing, its own lengths) plus each further voice by
its drawn relation, a doubling voice diatonically at the interval, an
alternating or apart voice as a line of its own under the line's bars
with its own lengths and the pair's second sample; no stack. Twenty songs:
Whole 01's accompaniment from more than three voices an onset to 1.23,
14 notes a bar where it had 39; the set's arpeggiated parts 1.81 (FFVI
1.46), the excess the doubled voices (2.0 by definition, as FFVI counts
them too). Levels stay hand-set a part; the readings keep no note levels
(the raw readings do; storing them is import work). Song Check 12 is
written from this.

### Round 20: the voice beside the line (2026-10-23, from the owner's note on set 12)

Set 12's Whole 01 and 02 came out garbled: round 19 had made each voice
beside an upper part's line an independent line, its own figure drawn
under the line's bar, its own voicing, motion, habit and lengths. Whole
01 had four arpeggios in one register whose onsets fell on the line's 14
to 32 % of the time, at unrelated intervals; Whole 02 a staccato line (a
0.4 note-length draw) over two busy lines an octave below it in the bass's
range. No wrong notes (no semitone, seventh or tritone clashes between the
voices): four unrelated things at once. FFVI's voices beside an
arpeggiated line, measured on every upper part with two voices or more:
0.60 of the line's strikes, the line's note lengths (1.02), two thirds of
their onsets on the line's onsets, the interval to the line steady in 27
% of notes only; a doubling voice 1.0, 1.0, 0.99. Bar by bar, a voice
beside the line plays in 79 % of the line's bars, strikes with half its
onsets (median; a third of the bars every onset), and adds 1.2 of its own.

Built: `second_figures` for an upper part re-encoded as a mask over the
line's onsets plus the voice's own (`rhythm.second_mask`, `apply_mask`),
by the song's feel and tempo band and the line's onset count (a mask read
onset by onset; one from a shorter line read around a longer one had
filled it, so the draw never backs off below the count, `MASK_FLOOR`),
drawn a bar; the voice takes a tone of the line's own voicing (the
line's voicing shared through `writer.upper(shared=, tone_index=)`, the
tone drawn a span) and the line's lengths; the bass's second voice keeps
its own figure. Twenty songs, voices beside an arpeggiated line: strikes
0.72 of the line's (FFVI 0.60; drawn once a line figure 0.88), lengths
1.00 (1.02), onsets with the line 0.98 (0.67: the own onsets are rarely
drawn), interval steady 0.65 (0.27: the voice walks the arpeggio in step
with the line); voices striking together 2.06 to an onset (FFVI 1.46; set
11's stack three and more, set 12 1.81). Doubling voices 1.0 throughout,
as FFVI's. Song Check 13 is written from this.

### Round 21: the sample for a register, the register of a voice (2026-10-23, from the owner's note on set 13)

The owner heard piercing pitches in the accompaniment and the tune on
several songs (Whole 01 among them) and took it for a level. It was
pitch. The parts sit where FFVI's sit (accompaniment median 61 against
62, melody 68 against 69), but the samples were being played far above
their recording: FFVI plays a sample more than an octave above its
recorded pitch in 0 % of accompaniment notes and 2 % of melody notes,
never past +20; the written songs in 10 % and 8 %, up to +27 and +28
(Whole 07's melody played a sample the game used at midi 36 to 48 up at
92). Two faults, both in drawing words that exist.

- **The sample for a register** (`whole.best_sample`). `sample_fits` had
  asked only that the register's centre lie within six semitones of a
  range the ranges table draws for the sample, and drew at random when
  nothing fit; worse, it looked the sample up by the pack's prefixed name
  while the table names the pack's own id, so it had found no range at
  all and every pool choice had been random. Now the pool sample whose
  game-played range covers the register best is taken, the part's top
  weighing most, and when the pool's best still falls more than REACH (7
  semitones) short of the top, the pack's other tonal samples are tried;
  the pool's share decides a tie.
- **The register of a voice** (`rhythm.register_notes`). The `registers`
  and `balance` tables had counted a layered part's register over all its
  voices, and the writer handed that span to every voice: Whole 01's
  accompaniment line and Whole 20's melody ran over 44 to 96. FFVI's
  layered accompaniments span 16 semitones merged (max 52) but 12 as a
  line (max 24); five of its songs span more than 30 merged, no line does.
  Both tables now count the line voice's register; the voices beside it sit
  at their layer offsets.

The measures after the fix are in the set's lede (Song Check 14).

### Round 22: the voice that doubled a pitch, the sample's playing habits (2026-10-23, from the owner's note on set 14)

The owner heard Whole 02's accompaniment "glitching" from about seven
seconds, as if its voice played too fast. Bars 3 and 4 there are
sixteenth bars on all three accompaniment voices (eight notes a second,
50 ms notes from the line's 0.4 sounds draw) on sample f89f5aedfd, a pad
with a 39 ms attack that FFVI plays at 65 ms at the shortest and under
5.6 notes a second in its fastest bars; and at most of those onsets two
of the voices sat on the identical pitch (midi 46), the voicing there
having two tones. One fault and one missing word.

- **The fault** (`writer.upper`). A voice beside the line took its tone up
  the line's voicing (its rank's, or one drawn a span) without regard to
  what the other voices of the part already held at the onset, so with a
  thin voicing two copies of one sample played one pitch at once and
  phased against each other. The part's pitch classes at each onset are
  now kept in the shared voicing dict (`("taken", (bar, position))`); a
  voice beside the line takes the first free tone up from its own, and
  where every tone of the voicing already sounds it sits the onset out.
  FFVI's voices beside a thin voicing double at the octave or rest.
- **The sample's playing habits** (two tables, `sample_lengths` and
  `sample_speeds`, in VOCABULARY.md). Per song and sample: the shortest
  note the game plays it at (a class of the tenth-percentile length) and
  the fastest bars it plays it in (a class of the ninetieth-percentile bar
  rate). The sample for a part now weighs the part's fastest bar as
  written (`whole.part_speed`, over the line and its doubling voices) in
  three reaches, a song that plays the sample this fast first (the class
  drawn a song, as the ranges are: a song plays the pad at eight where
  most hold it), then any song's fastest bars, then the excess over the
  game's fastest on it against the range's fit; and at rendering a note
  on a sample is never shorter than the song's shortest on it
  (`score_of`, a floor from the drawn class; a floored note is trimmed to
  the voice's next key-on, which cuts it on the SNES chip anyway, and the
  grid would otherwise have cut the next note at the first one's old
  end).

Measured on the twenty seeds before and after (habits22.py; FFVI from the
readings): two voices of one upper part on the same midi at one onset,
0.337 of the two-voice onsets to 0.006 (FFVI 0.068; the same pitch class
0.541 to 0.009 against FFVI's 0.273, whose octaves are the doubling
layer's, not this fix's); rendered notes shorter than the game's
shortest typical note on their sample 7.3 % to 2.0 %, 273 of the 277 left
cut by the voice's next key-on; voices whose fastest bar outruns the
sample's typical fastest in FFVI 31 to 20 (of about ninety), past the
game's fastest bar ever on the sample 0 to 2 (Whole 06's counter at 9.4
against 8.7 a second: no sample covering its register reaches a class
that fast, so the least excess decided). The first cut of the speed term
(a weight only) had left the 31 at 20 too and put a bass sample the game
never plays past 5 a second under a line at 9.9; the reaches came from
that.

Open from this round: FFVI's voices share a pitch class at an octave in
a quarter of its two-voice onsets (the doubling layer's intervals) where
the writing has one in a hundred; the extra voice's interval steadiness
still stands open from round 20.

### The exit checks, run (2026-10-24; checks only, nothing in the writer changed)

Set 15 passed the owner's ear ("almost every song is good now, the misses
are acceptable"), so two of the exit criteria were measured on its twenty
songs (seeds 1-20, both switches). The scripts sit beside the others on
Ragnarok (`fourbar_check.py`, `nearest_check.py`, `nearest_tables.py`,
`octave_check.py`); the games' tables they fit are cached under
`~/diags/bitcomposer/idiom/phase4/nearest/tables/`.

- **No four-bar phrase matches a game's: passed.** Every part's line
  (melody, counter, bass, accompaniment), windows of four bars at every
  bar as rhythm in twelfths and intervals, against the tune-copy reference
  set (every game's four-bar tune phrases) and against FFVI's own parts
  from the readings: no exact match in 461 melody, 322 counter, 437 bass
  and 425 accompaniment windows of six notes or more. Forty-two melody
  windows share a four-bar rhythm with an FFVI tune on other pitches. At
  two bars the backing matches FFVI exactly fourteen times (bass 7 of
  307, accompaniment 7 of 409): stock cells, an alternating bass from
  Returners, arpeggio figures from Cyan and the Ending Theme.
- **Songs written with FFVI's vocabulary fall nearest FFVI: passed, 20 of
  20.** Each of the 37 games with twelve readings or more got its own 67
  tables (the pack's KEPT set, `packtables.build`); each written song was
  rendered once, read back by the readers as the measures are, its units
  counted table by table, and every game's tables scored them (bits a
  unit, summed over the units, summed over the tables). FFVI is nearest
  for every song. By family: the figure tables (the upper figures, bass,
  drums, the kit's groups) put FFVI first in 11 songs and second in the
  other 9 (Super Ghouls'n Ghosts first there, a game of 23 songs whose
  thin tables score common bars high); the plan tables first in 8, median
  rank 2; the tune's tables first in only 5, median rank 5.5 (Bahamut
  Lagoon first in 5). Table by table, the `rhythm` figures put FFVI first
  in 20 of 20, `drums` 15 of 16, `bass` 14 of 19; `moves`, the tune's
  bulk (137 units a song), puts it first in 5 of 20 at a mean rank of 9.
  The remaining tune tables and nearly every plan table hold one to
  seven units a song, and their rankings are not a measure: the winners
  are the games with the smallest vocabularies (Jurassic Park Part 2's
  one-outcome tables win `balance`, `layer_samples` and `theme_doubling`
  outright), the known bias of a likelihood toward low-entropy tables on
  common outcomes. A fair per-table distance would score each song
  against the game's own songs' spread under its table; not built.
  Reading: the backing and the plan are FFVI's by the tables; the tune is
  where the songs are least FFVI, which is where the owner's ear put it.
- **The octave, measured while the writing items were listed.** FFVI's
  voices beside a line share a pitch class in 0.286 of the two-voice
  onsets where the voices' rhythms differ (an octave apart in 15 %, the
  same midi in 8 %) and in 0.122 where they double; the written songs
  0.000 and 0.009. The layers table has the word for it (`apart +0
  like`: bass 31 %, counter 21 % of second voices sit in the line's own
  register), but the voice beside the line takes a tone of the voicing
  up from its own, never the line's pitch an octave off. The word that
  would carry both this and the voice's interval steadiness (round 20,
  0.65 against 0.27): the voice's interval to the line at each onset,
  drawn in context, in place of the rank's tone.

Not run: the spread over twenty seeds against the game's own (slice 1's
distinct-figures and ostinato measure, over the whole song); the blind
pick rate, on hold by the owner's call until a game he does not know by
heart; the nearest-game test in the other direction, which needs a second
game's pack (Mega Man X, after phase 5 by his call). The owner holds the
writer where it is for now and has ideas of his own to put first.

### Round 23: the voice beside the line as a melody of its own (2026-10-24, on the owner's go)

Set 15 passed the ear, and the owner asked for the writing items and chose
this one first: the voice beside the line (round 20's mask gave it the
line's rhythm; its pitch was a hand rule, a tone of the line's voicing up
from its rank). He asked whether the fix was a rule replacing a rule; it
is a word replacing a rule, and the open choice in it was settled by
counting, as the rules of evidence ask.

**Counted first (interval_check.py, move_check.py, product_check.py on
Ragnarok).** FFVI's voice beside a line, where the two strike together
(3352 onsets): a third below the line most (12 %), an octave off in 13 %,
on the line's own pitch in 5 %, its interval kept from one such onset to
the next 37 % of the time; where it strikes alone (1546 onsets, a third
of its onsets) it repeats its note 29 % and moves a step 37 %. Held out
over FFVI's songs: the interval to the line is best predicted by the part,
the relation and the interval before (the chain, 0.7 bits a unit); the
layer word, the line note's chord role and the line's own move add
nothing. But the voice's own move from its last note is surer than its
interval (3.4 against 3.9 bits a unit with the line; 3.3 against 4.5
alone), and the product of the two words, normalized over the candidate
intervals, is surer than either (3.36 bits against 3.87 and 3.71). The
written voices before: never at the octave, holding their interval 54 %,
and placed against the line alone (the first cut of this round) they had
leapt five scale steps or more at 43 % of their onsets against FFVI's
11 %, a voice jumping between 53 and 84 within a bar.

**Built.** Two tables (VOCABULARY.md): `voice_intervals` (the interval
to the line in scale steps where the two strike together; part, relation,
the interval before) and `voice_moves` (the voice's move from its own last
note at every onset; part, relation, place: with the line or alone).
`writer.upper(kind=)` draws the voice's note: with the line, each
candidate interval weighs its probability under voice_intervals times the
probability under voice_moves of the move it implies (the line's move
between the two onsets known from the line's notes kept in `shared`);
alone, the move alone. Never an interval or a move the game never made
(the words' vocabularies, as a draw would); a pitch another voice of the
part holds is drawn again (an octave shift had put the collisions at a
sixth above), the onset skipped after four. The voice sits in the span
FFVI's voices beside a line sit in (the line's register widened by the
layer offset's cap, `rhythm.LAYER_OFFSET`) rather than folded into its own
offset register, which had turned a drawn third below into a sixth above.
The round-22 guard is on the pitch itself now, not its class, so octaves
are allowed and unisons are not (the second voice's sample may be the
line's).

**Measured after, the written voices by the plan's own words (2007
onsets with the line, 69 alone):** an octave off 0.17 (FFVI 0.13), on the
line's pitch 0.02 (0.05), the interval kept 0.41 (0.37); the intervals
themselves a third below 0.11 (0.12), a sixth below 0.09 (0.08), a third
above 0.08 (0.08), an octave above 0.08 (0.06), an octave below 0.07
(0.04); the voice's own move with the line within a step 0.66 (0.57),
five steps or more 0.03 (0.11); alone, a repeat 0.30 (0.29), a step 0.21
(0.25). Chord tones 0.40 against FFVI's 0.74, a number not to trust across
the two sides: FFVI's chords are read from its notes, the written songs'
are planned.

**Open from this round.** The voice's own onsets: FFVI's voice strikes
alone in a third of its onsets, the written one in 3 %. The lines are not
the cause (the written line bars with three onsets or fewer 0.43 against
FFVI's 0.31); the mask draws under the written contexts give own onsets
in 15 % of bars against the table's 27 %, so it is in the drawing, to be
found. The doubling voice's chord tones (0.31 against FFVI's 0.82 by the
same biased measure; `diatonic()` doubles at one scale interval where
FFVI's doubling voice bends to the chord), the same word's domain, not
built. The measurement scripts classify a written voice by the plan's
word, not by `harness.relation` on its notes: the mask's coincidence
makes nearly every written voice beside a line a "doubling" by the
reader's rule, and a first after-measure had ranked the voices by note
count and read a doubling voice's notes as an apart voice's.

### Round 24: a sample given a job the game never gave it (2026-10-24, from the owner's notes on set 17)

Five new seeds (21 to 25, Song Check 17) on round 23's writing. The owner
heard a staccato pluck in Whole 22's bass and a chirp in Whole 24's
counter, and Whole 23 had no drums though its plan played them in 32 of 46
bars. Three drawing faults and a kit rule of mine, all one family: a
sample, or a bar, given a job the game never gave it.

- **The pair of samples by halves, from another part, out of reach.**
  Whole 22's second bass voice played sample 48bab384c7 at midi 54 to 68;
  FFVI plays it at 36 to 48 (Dancing Mad's low second bass). The pair
  table had drawn Dancing Mad's pair, the pack lacked its first sample,
  and the second was applied anyway under the line's own choice, at the
  layer word's +8 from a different song. Whole 24's second counter voice
  played 5d5fe2fd48 at 80 to 92; FFVI plays it at 64 to 76 (a mallet it
  gives Kefka's, Strago's and Gogo's tunes). The pair table counted no
  counter-lines (`layer_sample_units` looked at the chord parts and the
  bass), so the draw fell through to the root and took Under Martial Law's
  accompaniment pair. Fixed as faults: `pair_for` draws from the part's
  own pairs alone and only where the pack holds both samples; the pair
  applies only where each sample reaches its voice's register by the
  ranges table (`reaches`, REACH at both ends), else the second voice's
  sample is chosen as the line's is, by its register and speed
  (`second_register`, `part_speed(second=True)`); the pair table counts
  the counter-line and the tune. After: Whole 22's second bass on
  cab1413363, Whole 24's second counter on 72f0a1e88e, both FFVI samples
  of those registers.
- **A chain floored on a context with one outcome.** Whole 23's kit habit,
  "sparse repeating", has one FFVI song in triple feel, and that song's
  counted kit bars are all rests; the drum chain, floored on the habit,
  drew rest 46 times. Fixed as a fault in `tables.Table.draw`
  (`floor_outcomes`, FLOOR_OUTCOMES 2): a chain's floor steps down to the
  deepest level that holds a choice. A first cut stepped down from any
  one-song context (FLOOR_SONGS) and re-densified every part whose habit
  one song had (Whole 24's counter from 46 notes to 117); a one-song
  context with bars of its own is the game's vocabulary and stays. With
  it the figure tables' shape puts the habit before the feel
  (`packtables.FIGURE`), so a step-down lets the feel go and keeps the
  habit. Whole 23's kit now plays 11 hits in 7 bars: FFVI's sparse
  repeating kit, which is what the habit word says, under a plan whose
  presence word has the drums in 32 bars (two words drawn apart, noted).
- **The kit's rim was a melody instrument.** Round 17 filled the rim slot
  with the busiest sample the drum namer calls "other"; in FFVI that is
  the mallet above, a tune in sixteen songs with a few drum-role notes.
  No FFVI figure strikes the rim letter, so it never sounded in a Song
  Check; it reached the ear only through the pair fallback. Fixed:
  `pack.drum_uses`, a kit slot takes only a sample whose drum-role notes
  are half its notes or more; the rim is now 63d84c8c76, a drum. The thin
  pack was rebuilt from the SPCs (69 tables; the pair table 96 units of 64
  songs, 28 of them counter-lines).

**Measured after, seeds 1 to 30.** Of 29 second voices, 7 share the line's
sample (no pair, the fit's own choice) and, by the most-voted range of
their sample, 13 still sit more than REACH outside it at one end. Those
are not the samples' fault: the voices' registers are. A second voice's
register is the line's at the layer word's offset, and the offset is drawn
without regard to where the line sits, so a counter line at 64 to 76 with
"apart +16" puts its voice at 80 to 92, where FFVI plays nothing; the fit
then takes the least bad sample. The word that would carry it: the layer
offset conditioned on the line's register, or the voice's register as a
word of its own. Not built; the owner's call. Open from before stands.

### Round 25: richness, measured and given words (2026-10-24, from the owner's judgment on sets 16 to 18)

The owner heard the writing as a generator's beside FFVI: staccato,
single notes with no depth, a tune that rarely says anything, and asked
whether the rounds were going backwards or uncovering something deeper.
Measured (depth_check.py, envelope_check.py, timbre_check.py on
Ragnarok), it was the second: every round so far had worked on which
notes are written, and what he heard lives in how a note is rendered and
mixed, and in the tune's shape over a song.

**What the counts said.** The written notes are not short: longer and more
legato than FFVI's (tune 0.95 of its gap against 0.87, 335 ms against
201; counter 0.95 against 0.86; accompaniment 0.80 against 0.84; bass
0.90 against 0.89). The render was the staccato: every note flat at full
level and cut dead (`score.GAIN_FULL`, since the phase 2 bridge). FFVI
plays every note through ADSR (40 snapshots, 30 s each): attacks instant
for the tune, the chord parts and the bass, but a third of the
accompaniment's notes and half the bass's decay while held (sustain rate
15 or 16 on the main accompaniment sample), its pads swell in over 640 ms
(72 % of harmony notes), vibrato on 5 % of tune notes, the echo on 94 %
of them. Notes sounding at once are equal (written 4.8, FFVI 4.5), but
FFVI plays them on 3.1 distinct samples where the writing (counted on its
real samples) had used 4.3: FFVI stacks voices on one timbre (one sample
for both voices in 20 of its 43 layered accompaniments, 13 of 28
counter-lines, 7 of 8 harmonies). The readings do keep each note's level
(the voices table's blobs; an earlier note here had said they did not):
FFVI's parts sit close, the bass loudest (0.28 of full), the tune 0.22,
the chord parts and counter 0.19, the harmony 0.18; the writer's hand-set
mix had the tune at 1.4 times the accompaniment and the pads at 0.6 of it.
The tune: FFVI's peaks at 0.45 of the song with a 22-semitone range and
repeats its cells more; the written tunes peaked at 0.24 and spanned 16,
with no song-level word to say where a tune should climb.

**Built, on his go ("the 4 word fixes for the richness"), with the kit's
other slot (Song Check 18's Whole 29).**

- **The envelope a sample plays with.** `pack.envelope_of`: the thin pack
  builder keeps each sample's modal key-on envelope from the SPCs and
  writes it as the pack sample field `envelope` ({"adsr": [ADSR1, ADSR2]}
  or {"gain": GAIN}); the pack file checks it, the registry keeps it by
  voice (`samples.SAMPLE_ENVELOPES`), and `score_of` plays every note
  through it (the converter already renders ADSR from snapshots). 25 of
  25 FFVI samples carry one; 86 % of rendered notes play through an ADSR.
- **Levels.** `rhythm.load` keeps the readings' note levels
  (`Song.levels`, `Song.voice_levels`); two tables, `levels` (a part's
  share of the song's loudest, in tenths) and `layer_levels` (the second
  voice against its line); the plan draws them; `score_of` plays the
  loudest part at `TOP_LEVEL` and the rest at their share. Written
  medians after: bass 0.85, counter 0.64, accompaniment 0.59, harmony
  0.59, melody 0.55, drums 0.47, each part drawn on its own share.
- **One timbre.** `pair_for` returns a pair of one sample as "same" and
  the second voice takes the line's sample whatever the pack gave the
  line. Second voices on the line's sample 13 of 29 (from 7); distinct
  samples sounding at once 3.22 (FFVI 3.07; 4.26 before, counted on the
  written songs' real samples).
- **The arc.** Three tables in phrases.py: `climax` (which tune phrase,
  by its place among the song's, holds the tune's highest note), `arc`
  (how far each other phrase's top sits under the song's peak, by place),
  `summit` (how far the peak sits above the tune register's top). The
  melody writer draws the climax phrase and the ceilings and rebinds its
  register a phrase at a time, so every note of a phrase, not only its
  ending, stays under its ceiling (a first cut bounded the endings and
  the entry alone and left the peak at 0.17). After: the peak at 0.42 of
  the song (FFVI 0.45), the range 18 semitones (FFVI 22, from 16).
- **The kit's other slot.** `pack.other_slot`: the sample carrying most
  of the game's drum strikes the namer called other in their song (FFVI:
  the snare sample itself, 512 strikes), in place of the busiest sample
  named other (a melody instrument, round 17) or the busiest drum-majority
  one (a one-song orchestral hit, round 24, Whole 29's strange sound).

Song Check 19 is one seed twice, Whole 28 as set 18 published it and on
this round, by the owner's design: a song chosen for its potential, not
for being liked, and a before and after on the same seed. Open from this
round: vibrato (5 % of FFVI's tune notes), the tune's motif economy
(echoes 0.27 against 0.34, a drawing question), the second voice's
register (the layer offset drawn without regard to the line's height),
the melody sitting a shade under the accompaniment in the drawn levels
(FFVI's tune is 1.16 times its accompaniment; the shares are drawn a part
at a time), and `PACKS.md` naming the envelope field.

### Round 26: the bass that would not finish (2026-10-24, from the owner's notes on Song Check 19)

The owner took round 25's account of Whole 28 (the bass's notes identical,
its samples and levels changed) and heard, in both renders, a bass that
"isn't quite finishing what it's doing": notes ending abruptly, and the
second voice playing notes of its own instead of carrying the line. He
asked for a bug check. Measured (bass28_check.py, bass28_check2.py), one
bug and two missing words; the triplet runs are the writing (the song is
in triple feel, and FFVI's "medium walking" bass runs so in its shuffle
songs, in two-voice songs too, 4 of 13).

- **The bug: a bar's last note cut at the bar line.** The sounded-share
  word (`sounds`, `layer_sounds`) was counted against the gap to the
  voice's next onset wherever it falls; the bass and upper writers applied
  it against the bar's end. Every bar-final note of the written bass line
  ended on the bar line; FFVI's do 2 % of the time, running on into the
  next bar's first note. Where the next bar began late (Whole 28's bar 2
  at beat 0.5) the line held four beats, dropped into a half-beat hole and
  came back. Fixed in both writers (`writer.first_onset`, `realize(...,
  runs_to=)`): the last note runs to the next bar's first onset; at a rest
  bar or the song's end the bar line stays. After: 0.60 of the line's
  bar-final notes end on the bar line, those whose next bar begins on the
  beat (the note then ends where the next begins) or rests.
- **The share by the gap** (`gap_sounds`, VOCABULARY.md). FFVI's bass
  plays half its gap under two beats and nearly all of it from two beats
  on (one voice 0.83 / 0.46 / 0.97 / 0.99 by gap class; the second voice
  0.50 / 0.45 / 0.97 / 0.99); one share a voice had put the slap bass at
  0.50 of a three-beat gap and left a hole where the game holds. Counted a
  note on the chord parts and the bass, by part, voice (only, line,
  second) and gap class; the plan draws a share per class; the writers
  take it by each note's gap (`writer.share_at`); `sounds` and
  `layer_sounds` stay for the parts without the word. After, Whole 28's
  second voice: 0.40 under a beat, 0.20 at one to two, 0.90 at two to four
  (the 0.20 a draw within FFVI's spread for that class).
- **The second bass voice on the line's pitch.** FFVI's slap plays the
  sustained line's pitch class at 78 % of their shared onsets; the written
  second bass, drawing its own chord roles over the second_figures
  rhythm, at 31 %: that was the "random notes". The voice_intervals and
  voice_moves words are now counted on the bass too (`_beside_lines`),
  and `writer.bass(shared=, kind=, models=)` re-pitches the second voice's
  notes with them (`writer.beside_pitch`, the same product draw as the
  upper parts', factored out), the line recording its notes in `shared`.
  After: the same pitch class at 88 % of shared onsets.

Song Check 20 is Whole 28 three times: set 18's render, round 25's and
this round's, the bass figures the same notes in all three. Open: the
one share the upper parts' voices beside the line still take from the
line (gap_sounds gives them "second" now; measure), the melody writer's
own lengths (articulation, not this word), and the rest of round 25's
list.

### Round 27: two basses, or one in two layers (2026-10-24, from the owner's notes on Song Check 20)

The owner heard the two bass voices as incoherent in every song: one
voice a hook, the other "random stuff around it". Measured
(bass_coherence.py): in FFVI's thirteen two-voice basses the sustained
line plays 3 strikes a bar on 2 pitches and the slap 6 on 3, twice as
busy, and the slap strikes together with 75 % of the line's notes (from
39 % to 100 % by song) while a third of its own fall on the line's: the
line sits inside the slap's rhythm, one bass in two layers. The written
two-voice basses (five among seeds 1 to 20) had the slap striking with
41 % of the line's notes, Whole 28 36 %, and the slap no busier than the
line (0.74 of its strikes): two basses. Neither voice varies by repeating
bars literally (FFVI 0.00 and 0.08), so the hook feel is the rhythm's
consistency, not a riff.

**Why.** Round 18 gave the second bass voice a figure of its own, drawn
from FFVI's second-voice bars given the line's bar; when the written
line's bar is one FFVI never played, which is most bars, the draw backs
off to the part's general bars and returns unrelated to the line. The
chord parts met the same fault in round 20 and got the mask.

**Built, on his go.** `second_figure_units` counts the bass as it counts
the chord parts: the second voice's bar as a mask over the line's onsets
(which it strikes with, plus onsets of its own, `second_mask`), by the
feel, the tempo band, the line's onset count and pattern. `write()` draws
the mask a bar under the line's pattern and `writer.mask_figure` makes
the second voice's figure from it: the line's marks where it strikes
with the line, the root at its own onsets, both re-pitched by round 26's
voice words (the line's pitch where they meet, its own move between).
A first cut kept round 18's memo, one draw per line pattern, and Whole
28's five patterns all drew the doubling mask ('1 1 1'): a second voice
identical to the line, no fills (the slap on 99 % of the line's onsets,
0.96 of its strikes). The mask is drawn a bar, as the chord parts' is.

**Measured after, the two-voice basses of seeds 1 to 20 (five songs):**
the slap strikes with 0.71 of the line's notes (FFVI 0.75; before 0.41),
its own onsets on the line's 0.65 (FFVI 0.33; before 0.45), its strikes
1.29 of the line's (FFVI 1.93; before 1.47). Whole 28: 0.81 of the line's
notes (before 0.36), its strikes 0.89 of the line's. The two voices are
one rhythm now; the slap's own fills between are still fewer than FFVI's,
the bass mask table being thirteen songs (278 bars; the chord parts'
had 1302), and a sparse triple-feel line draws from the thinnest of it.
Song Check 21 is Whole 28 a fourth time beside set 18's, round 25's and
round 26's renders. Open: the slap's fills (the thin bass mask contexts);
the line's lurch between a one-note bar and a run in thin figure
contexts; and round 25's list.

### Round 28: the bass on the kit (2026-10-24, from the owner's question on Song Check 21)

**His question.** The sustained bass line starts and stops and leaves
odd empty space; a bass holds the rhythm, that is its job; does FFVI's?
And then: check FFVI's themed songs with a bass in particular.

**Measured first (discussion only).** By pattern FFVI's bass holds the
rhythm less than ours: a recent pattern held in 0.29 of its bars (themed
0.35) against the written 0.59, the downbeat rested on in 0.38 (themed
0.36) against 0.07. What it does is sit on the drums: three quarters of
its notes strike with some drum (0.75 themed, 0.77 all), and where two
drum pieces strike together, a bass note is there in 0.94 of the cases.
The written bass had 0.44 and 0.67: `locks_of` had locked the bass to
the whole planned band, a threshold the bass, written second with two
drum voices to hand, met in no bar, so it had been locked to nothing.
The slap's own fills were at half FFVI's rate (0.35 of its onsets off
the line's; FFVI 0.67), the bass mask table's floor standing on
one-song contexts.

**Built, on his go.** `bass_locks` (`rhythm.kit_accents`,
`rhythm.bass_lock_units`): the share of the kit's accents (positions
where two pieces strike together, on the figure grid) carrying a bass
note, in tenths, drawn once a song and given to the bass writer as the
lock's share (`writer.bass(lock_share=)`, `locked`); the lock's
positions are the written kit's accents. `tables.Table.draw` gained
`floor_songs`: the floor steps down to the deepest level that many
songs reach; the bass mask draw passes `PLAN_SONGS` (2) so the slap's
fills come from more than one song's bars. A test for each.

**Measured after, seeds 1 to 20 (15 songs with a bass and drums):**
the bass's strikes with any drum 0.44 to 0.52 (FFVI 0.75), the kit's
accents carrying a bass note 0.67 to 0.78 (FFVI 0.94); the slap's own
onsets 0.35 to 0.38 of its strikes (FFVI 0.67), its strikes 1.29 to
1.36 of the line's (FFVI 1.93). Whole 28: the lock applied in no bar,
and the slap's own onsets 0.10 to 0.18.

**Found: the lock has nothing to hold in this kit, and FFVI's themed
kits are the same kind.** By exact onset time FFVI's kit strikes two
pieces at once 0.04 times a bar; on the figure grid (`position`, as the
figures and `kit_accents` count) 2.63 times a bar in the 28 kits that
stack at all, and the other 17 kits with a bass never stack and have no
kick or snare voice (a hat, a cymbal or an unnamed piece under once a
bar). FFVI's themed kits: the low voice (kick, snare, toms) 8.95 times a
bar, the high (hat, cymbals, the rest) 0.65, stacks 0.37 a bar at the
median, four of twelve never. The written kits: 0.36 stacks a bar, five
of fifteen never; Whole 28's kit is the kick 64 times, the snare 260,
the hat 32, in 36 bars, no two together. The kit is not the fault; the
word is silent for a kick-and-snare kit. What FFVI's bass does there,
label-free: it follows one piece of the kit at 0.81 of that piece's hits
(themed 0.91; the piece once or twice a bar; the readings label it a
cymbal in 13 songs of 44, a snare in 10, a kick in 7, so the label is
no handle, and the pack's kick sample is struck in 14 songs only), and
its strikes fall on some kit onset at 0.77 of its notes (kits of two
pieces or more 0.82; by bar, all of its strikes on the kit in 0.58 of
bars, most in 0.19, fewer than half in 0.06, none in 0.16).

**Found: the line's lurch is the figure chain's depth, and a coarser
memory does not mend it.** Whole 28's line strikes 1, 10, 2, 1 a bar
through its A part; FFVI's bass under the same habit (medium walking)
keeps within one strike of the bar before in 0.59 of bar pairs and
jumps four or more in 0.18 (held-out songs overall: 0.74 and 0.09).
The bass table conditions a bar on the exact figure before it, and
under this habit 174 of 182 previous-figure contexts hold one song, so
a bar after a figure FFVI never played (the ten-note run, the two-note
bar) is drawn from the habit's whole spread (0.14 empty bars, 0.17 of
seven strikes or more) with no memory of the bar before. The candidate
was a coarser memory, the previous bar's strike count or onset pattern,
before or instead of its figure. Scored as phase 3 scored shapes
(held-out bits a unit, FFVI's 1874 bass bars split by song, the cache
mixture over each): the shape as it stands is best (-10.08 bits; the
pattern -10.10, the count -10.15), and what each writes keeps within one
strike in 0.64 to 0.68 of bar pairs (FFVI 0.74) and jumps four or more
in 0.15 to 0.17 (FFVI 0.09): the chain is not where the steadiness
lives. The unchained shape writes 0.64 too; the Cache's recall carries
it (its ostinato share drawn 0.34 against FFVI's 0.40). No shape change.
`~/diags/bitcomposer/idiom/phase4/prev_shape.py` scores any candidate
in a minute.

Song Check 22 is Whole 28 a fifth time beside the other four; the fifth
differs from the fourth in the slap's fills only, and the page says so.
Open, for his decision: a counted word for the bass on the kit's onsets
(`bass_on_kit`: the share of the line's strikes on some kit onset, by
the song, drawn and asked of each bar's figure), which reaches every
kit and would turn the ten-note run off the kit away; the slap's fills
against the line's density; the recall share; and round 25's list.

### Round 29: the counter-line beside the tune (2026-10-24, from the owner's note on Song Check 22)

The owner heard the counter-line and the tune "competing for air time
and blending together". Measured first (counter_vs_melody.py,
counter_split.py): FFVI's counter plays WITH the tune, not in its rests.
In its 52 songs with both, 0.67 of the counter's onsets fall on the
tune's, 0.82 of its sounding time lies under the tune's notes, it plays
1.42 times the tune's notes, as loud as the tune (level ratio 1.00 at
the median), 64 % of its notes below the tune and its register 2.5
semitones under; and it fills 0.61 of the tune's resting time. The
intervals split by timbre: on the tune's own sample (18 of 52) the
counter is a harmony line in thirds (-3, -4, +3, +4 = 36 % of shared
strikes, 0.82 of its onsets on the tune's, register gap -3); on another
sample (34) it sits at octaves and unisons (37 %), 0.52 of its onsets
on the tune's, 1.57 times the tune's notes, level 0.83. The written
songs (seeds 1 to 20, fourteen with both): 0.43 of the counter's onsets
on the tune's, 0.98 times its notes, level 0.74, register gap -1, the
tune's sample in 3 of 14; Whole 28 the tune's sample, the tune's
register (gap 0) and 0.19 of its onsets on the tune's, two tunes
interleaved on one timbre. The cause: `whole.write()` ran
`writer.melody` a second time for the counter with its own random
stream, and nothing in the vocabulary related the two lines.

**Built, on his go ("good with the words, go ahead"); three words
(VOCABULARY.md).** `counter_figures`: the counter's bar as a mask over
the tune's bar, counted as `second_figure_units` counts a voice beside
its line with the tune's line as the line (`rhythm.counter_figure_units`,
1493 bars of 52 songs; the line pattern `-` and count 0 where the tune
rests, the outcome then the counter's own onsets alone, 153 bars, which
`apply_mask` gives at a resting line instead of a rest); drawn a bar
after the tune is written as the second bass voice's mask is
(`MASK_FLOOR`, `PLAN_SONGS`). The voice words extended to the counter
beside the tune (`_beside_lines`; 3681 interval units, 6834 move units),
the kind its sample relation rather than a layer relation: a new share
`counter_samples` (same 17, other 35 by the line voice; the scripts'
merged notes say 18 and 34) drawn once into the plan and honoured at the
rendering (`samples_for`: a "same" counter takes the tune's sample; an
"other" counter the pool's best but the tune's, chosen for the register
it was written in). `writer.counter` writes the counter over the mask's
positions with `beside_pitch`: the tune's pitch and the drawn interval
where they strike together, its own move between, in the tune's register
widened by the layer offset's cap; its lengths from the `values` word
under its articulation habit, a bar's last note running to the next bar's
first onset (the gap the word was counted against; round 26's fix,
applied here). `counter_levels`: the counter's level over the tune's in
tenths, drawn once; the plan sets the counter's level to the tune's
times the share. A test for each; the suite passes (336 tests).

**Measured after, the same script (seeds 1 to 20, fourteen songs; FFVI
in brackets):** onsets on the tune's 0.43 to 0.56 (0.67); notes per
tune note 0.98 to 1.12 (1.42); level ratio 0.74 to 1.00 (1.00);
register gap -1.0 to -2.5 (-2.5); the tune's sample 3 of 14 to 5 of 14
(18 of 52); sound under the tune 0.76 to 0.78 (0.82); the tune's rests
filled 0.68 to 0.59 (0.61); above the tune 0.37 to 0.30 (0.36). Whole
28: 0.19 to 0.75 of its onsets on the tune's, on another sample, the
register gap -6 (its counter_levels draw 1.5, the one such song in
FFVI's 52; its tune rests 0.44 of the time and the counter fills 0.46
of that). A first cut had given the "other" counter the pool's best
sample, which is the tune's favourite: 10 of 14 on the tune's sample
and the owner's complaint intact, so the word is honoured both ways; and
the counter's bar-final notes cut at the bar line had filled 0.42 of
the tune's rests, the run-on 0.59. The before and after runs are
`phase4/r29_before.log` and `phase4/r29_after2.log`.

**Lost from the old counter path, by design (no second writer kept):**
the counter's phrase arc, contours, endings and relations, the echo urn
(the `echo` habit is drawn and unused), the chord-tone and repeat-rate
controllers, the step habit, the reference-set check (the line follows
the tune's rhythm and the drawn intervals; a copied phrase would be the
tune's, which is checked), and a second counter voice apart (one song of
the twenty; its layer word is logged, the voice not written: no word
counts a voice beside a counter that follows the tune). The counter
keeps its articulation, echo and sounds draws in the plan; the melody's
own `values` draws still cut a bar's last note at the bar line (open
since round 26).

**Open.** The counter's density against the tune (1.12 against 1.42) and
its own onsets' share: the mask's floor stands on the tune's onset
count, and the written tunes' sparser bars (a one-note bar in Whole 28's
A part) draw from the thinnest contexts; a second counter voice apart;
the "same"-sample unison guard is a writer's rule carried over from the
chord parts, not a count; the counter's chord clash against the
accompaniment is not read (the old path's `draw_move` stayed clear of
sounding semitones, the voice words count the interval to the tune
only). Song Check 23 is Whole 28 a sixth time beside the other five; its
counter is the change asked for, but not the only one (below).

**Reviewed (the same day; seeds 1 to 20 and 28 composed under the
round-28 code and pack and under this round's, every part's notes
compared).** One fault fixed: `counter_samples` and `counter_levels` had
been drawn at the end of `_plan_once`, on the plan's shared stream, and a
themed plan is drawn again on that stream when its tune cannot come
back, so the two draws inside the first attempt shifted every draw of
the next; Whole 14's key, form and band had changed (its drums and
harmony gone). The draws now come once in `plan()` after the retry
loop, after every existing draw, and every plan of the twenty-one is
the round-28 plan again. Two changes to parts other than the counter
remain, neither a fault in the words and neither fixable without a
choice the owner makes: (1) the counter's units sit in the shared
`voice_intervals` and `voice_moves` tables, whose coarse levels every
part's probability mixes in, so the chord parts' and the bass's second
voices draw a little differently (the probabilities move by 0.3 to 7 %
of their mass, enough to flip draws, and a flipped draw changes the
chain after it): in Whole 28 the second bass voice differs in 13 of 298
notes; across the twenty-one, ten songs' accompaniment voices and five
songs' second bass voices, and through the tune's clash check seven
songs' tunes. The choice is between the counter's own interval and move
tables (the other parts untouched, two more tables) and the shared ones
as the brief asked; it is for the owner. (2) The rendering's shared
stream: the counter's sample is now chosen after the tune's and from a
pool without the tune's sample, so the draws after it fall elsewhere:
Whole 28's echo is "normal" where it was "light" (wet 0.4 against 0.24)
and the floors on its bass samples are shorter (0.12 and 0.08 s against
0.4 and 0.12); of the fifteen songs with both parts, four have another
sample for the tune itself (three more the same sample under the pack's
other name for it), four an echo come or gone and three its wetness
changed. Nothing
restores the round-28 draws short of replaying them. The owner hearing
Song Check 23 against 22 hears the counter, the echo and the bass's
floors, not the counter alone.
