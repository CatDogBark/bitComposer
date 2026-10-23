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
