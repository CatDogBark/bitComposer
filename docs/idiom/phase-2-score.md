# Phase 2: the score of voices

Planned in outline (2026-10-20); begun 2026-10-22, the work recorded under
"Where it stands" below. See `../IDIOM.md`. This is stage 3's first half.

## Goal

One representation of a song as voices and notes in time, which the
decoder produces from a game and the generator produces for a SNES pack;
one back end that makes the module from either; one set of readers that
measures either.

## Starts from

The decoder's notes (`spc/notes.py`, `translate/events.py`); the
converter's stages after decoding (the samples, the instruments, the echo
plan and its copies, the notes' placement, the master volume); the
generator's pattern writing and its channel layout.

## Work, provisionally

- **The score:** voices, each a list of notes with a start and length in
  time, a sample, a pitch, volumes, an envelope (ADSR or GAIN) and whether
  it sends to the echo; a decoded song and a generated one both as this.
- **The generator's SNES path emits a score** rather than rows. The first
  thing this frees is the grid: the converter's placement already lands a
  note at any time (ticks and note delays), so sixteenths, triplets and
  detached notes become a matter of writing, not of rows a bar.
- **The converter's stages take a generated score:** the echo as the SNES
  chip's own (a delay, a feedback, a filter, a send per voice) where a pack
  asks for it; the channel budget measured and reported per song.
- **The readers read a score directly,** so a generated song is measured
  exactly as a decoded one: its roles from the readers, not from its
  channels, unless a comparison says otherwise and says so.
- **A substitution harness:** one voice of a decoded song replaced by a
  generated one, the rest as decoded, rendered to a module for listening
  and read for measuring.

## Produces

The score type; the generator's SNES path through the back end; the
readers over scores; the substitution harness; the chip and Genesis songs
byte for byte the same.

## Exit criteria

- A decoded song through the new path gives the module the converter gives
  today, byte for byte, or the differences are listed and accepted.
- A generated song and a decoded song are read by the same code.
- Chip and Genesis songs unchanged, byte for byte.
- A substituted song renders and reads.
- The channels a generated song needs with its echo is a number the output
  reports: the input to the MPTM question `../TRANSLATOR.md` holds open.

## Open questions

- Beats or seconds as the score's time, and where the tempo map lives.
- How the generator's own echo (repeats on beat fractions, darkened copies)
  and the SNES chip's echo coexist in one back end, and whether a pack
  chooses.
- Whether the built-in SNES packs go through the new path at once or later
  (a release of its own either way, since it changes how they sound).
- How many voices an arrangement takes, now that the hardware's eight are
  not a rule for generated songs.

## Where it stands

**Decided at the start (2026-10-22):** the score's time is seconds, as the
decoder has it; beats are a reading, and the generator knows its tempo
when it writes. The generator's beat-fraction echo and the chip's do not
coexist: SNES packs get the chip's. The built-in SNES packs go through the
new path as a release of their own after a listen. The voice count is the
arrangement's: the current layout's twelve, the echo's channels from the
plan rather than fixed.

**Step 1, the converter split (2026-10-22).** `spc.convert.Score` holds
what the stages need: the notes (the decoder's `notes.Note`), the length,
the voices, the master volume, the row rate, the snapshot where there is
one and a sample table where there is not. `score_of` reads one from a
snapshot, `render` runs the stages on one, `convert` is the two in one.
The stages are untouched; over 322 songs of the 39 games (every sixth)
the module a snapshot gives is byte for byte the same.

**Step 2, the readers read a score (2026-10-22).** `events.of_score`
names a score's notes as `play` names a snapshot's (the naming is one
function now), `reading.of_score` reads one through the readers a
snapshot goes through. All 1836 songs read through their scores give
readings identical to the ones from `play` (tempo, meter, key, loop,
roles, chords).

**Step 3, the generator's song as a score (2026-10-22).** `score.of_song`
is the bridge: the patterns the generator wrote, one channel a voice (its
own echo channels left out), as the decoder's kind of note, the preset as
the sample at its own rate, vibrato and portamento as bends, the volume
column and slides as swells, note delays and retriggers as starts, a flat
envelope and a cut (a preset's release tail is not played: the chip
played none). The echo is the chip's: the melody, harmony and arp voices
send at the delay nearest the generator's up to the chip's 240 ms (the
generator's dotted eighths and quarters ran to 450 ms), the generator's
feedback, a gentle low-pass. The chip and Genesis sounds keep their path;
`--score` on the CLI renders a song this way; a snapshot's module stays
byte for byte. Six songs rendered both ways sit in
`~/Music/bitComposer-dev/score-check` for a listen: the score versions
come out within 0.6 dB of the old ones in loudness and darker (the
spectral centroid about halved: the chip's interpolation colouring on the
presets, and the echo's filter), with 13 to 43 channels each with the
echo, the number the MPTM question asked for, all inside IT's 64.

**The generator's songs through the whole path (known answers).**
`tools/known_answers.py --via score` reads sixty composed songs as a game
is read, the beat reader included, against their plans:
- *The beat reader hears half the written tempo in 57 of 60* (a 106 BPM
  song at 53), and the planned bar lines then fall on a read line in 31 %,
  a half bar off in 32 %, elsewhere in 37 %. The tempo rule picks the level
  at which the song's typical voice plays about 1.1 notes a beat (tuned on
  the games' 41 taps, 40 right); the generator's typical voice plays 0.4
  to 0.8 a written beat, half a game's. Whether a listener taps the
  written tempo or its half for these songs is the first thing the listen
  should say; the reader is not retuned on the generator's output.
- Read at that level: the chord root right on 66 % of beats (90 % on the
  generator's own grid), the melody channel the melody in 75 % (95 %),
  the bass channel the bass in 39 of 60: in 17 the tom channel, played at
  several pitches, is the lowest tonal voice and takes the bass's role (a
  tom at many pitches is not a drum by the role reader's rule; naming the
  sample by its sound, as the drum namer can, would settle it: a phase 3
  item), the drum channels drums in 323 of 341.
These are the readers' numbers on music that is sparser and plainer than
the games', and they say more about that music than about the readers;
phase 3 changes the music.

**Step 4, the substitution harness** (`tools/substitute.py`): one decoded
voice replaced by a generated one, the generated voice keeping its own
tempo and length, its preset as its sample and the decoded voice's echo,
rendered through the same back end and read by the same readers.

**The listen, and what it decided (2026-10-22).** Six whole songs rendered
both ways, and two substitutions. The whole songs answered nothing about
the back end: the music going in is the old generator's, and bad notes
render faithfully; the listener found them a muffled copy of something
already poor and the comparison with real SNES music unfair to make. The
substitutions answered the real question: Hyrule Field with a generated
melody holds up, so the rendering is sound when the notes are; Terra with
a generated bass does not, because the bass is wrong for FFVI, which is
the generator's problem and phase 3's work. Decided:
- The old SNES path stays the shipped default; the "release of its own"
  question is closed, not deferred. The score path is the development
  path for the new generator, and ships when the new music beats the old
  by the listener's ear and the measures.
- Listening tests for phases 3 and 4 are substitutions, one generated
  voice inside a real song against the original; whole generated songs
  come back when phase 4 has slices worth hearing. A whole song of the
  old generator asks the listener to project the aim onto it, which is
  too much to ask.
- The tempo question is withdrawn: the reader hearing the old songs at
  half tempo says they are half as dense as a game's, which the readings
  had said; the reader is asked again on the new music, not tuned on this.

**Exit criteria, met:** a decoded song through the new path byte for byte
(322 songs); a generated song and a decoded song read by the same code;
chip and Genesis unchanged; a substituted song renders and reads; the
channels a song needs reported (13 to 54 across the set, inside IT's 64).
Phase 2 closes as plumbing, which is what it was.

**Carried into phase 3:** toms at several pitches taking the bass's role
(naming drum samples by their sound inside the role reader settles it);
the chip's interpolation colouring applied to the built-in synthesized
presets as to game samples, perhaps a double softening, which matters
only if those presets survive the overhaul (imported packs play real game
samples, where it is right); the tempo rule's level on music sparser than
the games', asked again when there is new music.
