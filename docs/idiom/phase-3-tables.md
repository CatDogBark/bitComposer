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

## Planned in detail (2026-10-22)

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
