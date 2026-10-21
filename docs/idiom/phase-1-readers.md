# Phase 1: the readers

Planned in outline (2026-10-20); the detail is written when the phase
begins. See `../IDIOM.md`.

## Goal

Before any table is read from them, each reader (the beat and bar, the key
and mode, the chords, the roles and the tune, the form, the drums) is
scored on ground truth it was not tuned on, fixed where it fails, and the
stage 4 counts are run again, so the plan rests on what the music does and
not on what the readers do to it.

## Starts from

The readings of the 39 games (stage 1), the stage 4 counts and their
"what looks wrong" (`../TRANSLATOR.md`), the beat marks (43 songs) and
form marks (36) already made by ear.

## Work, provisionally

- **An independent decode.** VGMTrans over the games whose drivers it
  reads; a harness that compares its tempo, loop points, note durations and
  track order with the readings' beat, loop, note lengths and tune voice,
  and classifies every disagreement: ours, theirs, or a real ambiguity. A
  program on the machine, for checking only.
- **Songs with known answers.** A set of generator songs across its scales
  (the modes included), forms and kits, rendered and read back; each
  reader's recall and precision recorded. A floor, not a pass.
- **The ear's three pages,** built like the Ear Check and Form Check pages:
  - *Chord Change Check:* tap when the harmony changes, about twelve songs
    across games; no chord need be named. Decides the chord rate.
  - *Tune Check:* each voice soloed; which carries the tune, and where it
    passes, bar by bar.
  - *Drum Name Check:* about forty drum samples drawn at random across the
    39 games, soloed; kick, snare, hat or other. Held out from the namer's
    tuning.
  The marks are kept with the beat and form marks, on the machine, never in
  the repository; the scores are recorded here.
- **Fixes, as the scores demand:** a key reader that knows the modes (the
  tonic from the loop's landing, the bass and the final; the mode from the
  scale's content); chord changes read from where the bass and the
  accompaniment move rather than where a melody's passing note shifts the
  match; the tune as one line across the voices that carry it; the drum
  namer re-judged on the held-out samples; the bars at section joins; the
  songs in free time measured on their own rather than dropped.
- **The counts run again** over the 39 games, the shared-or-own table with
  them, and Stage 4's numbers refreshed.

## Produces

A score per reader against each ground truth; the readers fixed; the
counts and Stage 4 refreshed; the ear marks kept locally with the others.

## Exit criteria

- Each reader scored on held-out ground truth, the numbers recorded here.
- The chord rate and the modes read as the ear and the independent decode
  have them, within a tolerance agreed before scoring.
- What is excluded reported per game, with the free-time songs measured
  separately.
- The shared-or-own table re-read, and the shared-vocabulary hypothesis
  kept or dropped on it.

## Open questions

- How a chord-change tap is scored against a chord span (a window around
  the tap; the rate over the song), and the tolerance.
- Whether the half bar survives as the harmony's counting level.
- What to do with songs the beat reader follows loosely.
- How much of the drum namer's rule survives the held-out set.
- Which of the 39 games VGMTrans reads, and how far its loop points and
  track order can stand for form and the tune.
