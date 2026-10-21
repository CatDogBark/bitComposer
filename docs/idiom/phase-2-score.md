# Phase 2: the score of voices

Planned in outline (2026-10-20); the detail is written when the phase
begins. See `../IDIOM.md`. This is stage 3's first half.

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
