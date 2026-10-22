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

Two instruments, the listener's choice (2026-10-22):

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

**What the slice added, for the listening:** the bass and the drums
only. The melody, the harmony and arp, the form, the tempo, the mix and
the samples are the old generator's; the drumless songs (the pack's
habit, four of twelve) stay drumless; a written part rests where the old
one rested. The listening page: the Substitution Check's form, the old
part against the new in the same song.
