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
- Whether the half bar survives as the harmony's counting level, or the
  root-motion rule replaces it.
- What to do with the 222 songs the beat reader follows loosely: scored
  separately, since a loose grid rounds nothing.
- How much of the drum namer's rule survives the forty.
- Whether the free-time songs are a vocabulary of their own, which phase 3
  decides from what step 5 measures.
