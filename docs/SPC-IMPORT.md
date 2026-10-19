# SPC import: a game's own instruments and habits, translated

Plan, written 2026-10-18; nothing here is built yet. The goal is a pack
made from a game's real sound files: point the player at a soundtrack's
`.spc` files and get a SOUND that plays the game's own samples, with the
habits of its score (tempo, registers, how the harmony moves, the drums,
the echo), measured rather than guessed. In short, a translator from the
SNES sound system to bitComposer's.

Two halves. **Import** reads what a snapshot holds outright: the sample
bank, the envelopes, the echo. **Emulation** runs the game's own music
driver to find out what the snapshot only implies: which notes are
played, on which voice, when. The import is proven ground (every built-in
pack was made from it, by hand); the emulation is the new and large part.

Out of scope: getting the files. The importer takes `.spc` files as they
are; finding them, and unpacking `.rsn` archives (RAR), is the user's
business.

## What an SPC file is

A snapshot of the SNES sound subsystem at one instant, 66 KB:

- **The 64 KB of audio RAM**, which holds the game's music driver (SPC700
  code), the song's sequence data in that driver's own format, and the
  sample bank: BRR-compressed samples (9-byte blocks of 16 samples, four
  prediction filters, end and loop flags) found through a directory whose
  page is the DSP's `DIR` register, four bytes per sample (start, loop
  start).
- **The 128 DSP registers**: per voice (eight) the volume, pitch (14 bits,
  `0x1000` plays a sample at 32 kHz as recorded), source number (`SRCN`),
  ADSR or GAIN envelope; globally key on and off (`KON`, `KOFF`), the echo
  (`EON` which voices send, `EDL` delay in 16 ms steps, `EFB` feedback, the
  eight FIR taps, `EVOL`), noise (`NON`, the clock in `FLG`) and pitch
  modulation (`PMON`).
- **The SPC700 CPU registers** (PC, A, X, Y, PSW, SP) and the timer and
  I/O state at `0xF0`-`0xFF`, so execution can resume exactly where the
  dump stopped. An ID666 tag gives the title, the game, and often the
  song's length and fade.

Rips are usually dumped at the start of a song, so running the snapshot
plays the song from its top.

## What exists already

The research tools behind the four packs (`~/diags/bitcomposer/*-spc/tools`,
not in the repository) do the import half by hand:

- `survey.py` decodes every BRR sample across a set of snapshots,
  de-duplicates by decoded PCM, and profiles each (steady-state harmonics,
  centroid, attack, decay, loop).
- `voices.py` reads, per snapshot, which voice plays each sample, at what
  sounding pitch, with what envelope, with echo or not.
- `fine.py` and `match.py` compare a sample's profile with a synthesised
  voice's.
- Echo per pack was read off the DSP registers across the snapshots.

What they could not do, and what limited every pack: a snapshot is one
instant. It shows eight voices mid-song and says nothing about which one
is the melody (doublings, trills and chord tops pulled the traced "lead"
medians up by an octave or more; see the register plan in ROADMAP.md),
nor about tempo, phrase, groove or form. The rest of the song is in the
sequence data, in a format that differs per driver (Square's, Nintendo's,
Capcom's...). Reading every driver's format is endless; running the
driver is one job.

## The pieces

### 1. The pack file format (built: `docs/PACKS.md`)

The "your own packs" roadmap item: a pack as data, not Python. A pack
file is JSON holding the table a built-in pack keeps as `PACK` (palette,
label, voices per role, habits, trims), with the pack's own voices as WAV
files (tuning, loop, release family, volume). `bitcomposer/packs/packfile.py`
checks it, registers its voices with the sample registry and the pack in
`PACKS` (not in the random draw), and `--pack-file` composes with it; the
player's PACKS panel will pass that same option. It carries every habit
the composer reads (27) and every role.

Changed from the first plan: the built-in packs stay Python. Their
tables carry comments recording where each number came from (bank
counts, DSP readings), which JSON cannot hold. Instead a test writes each
built-in pack in the format and reads it back unchanged, which proves
the format can say everything they say and keeps it that way.

### 2. The SPC reader (built: `bitcomposer/spc/`)

The research tools' decoding, made a module with tests: the file layout,
ID666 (text and binary), the BRR decoder, the sample directory, the DSP
register map (per voice the volume, pitch, sample and envelope; the echo,
noise and pitch modulation). Pure Python, standard library only, like the
generator. `python -m bitcomposer.spc` shows what a snapshot holds, and
`--export DIR` writes every sample of a set of snapshots once, as WAV, with
its loop in `samples.json`.

Three things the research tools did not need and an import does:

- **The chip's arithmetic exactly.** The research decoder ran the filters
  at half scale and clipped where the chip wraps: a sum past 15 bits loses
  its top bit on the SNES, which flips its sign. The reader wraps, as the
  chip does; a random-block test checks it against a second decoder
  written the way bsnes does it.
- **Loops as they sound on the repeats.** A loop whose first block
  predicts from the samples before it decodes differently on its first
  pass and on the repeats, so a tracker looping the first pass clicks.
  The reader appends repeat passes until one decodes as the last did
  (within 64 of 65536, where the filters' rounding drifts for ever) and
  loops that one.
- **Telling samples from leftovers.** A snapshot's directory has 256
  entries, most pointing at whatever the RAM holds now. An entry counts as
  a sample when every block's shift is at most 12 and the first block is
  unfiltered, as encoders write them, or when a voice is playing it.

### 3. The emulator

Enough of the machine to run the game's driver and record what it tells
the DSP, not to make sound:

- **The SPC700 CPU**: 256 opcodes over a small set of addressing modes, at
  1.024 MHz, cycle-counted so the timers run true.
- **The three timers** (two at 8 kHz, one at 64 kHz). Drivers pace their
  tempo off them, so they are the clock everything is measured by.
- **The DSP as a register file** that logs every write with its cycle
  time: `KON`, `KOFF`, pitch, `SRCN`, volume, envelope, echo and noise
  registers. Sound synthesis is not needed for the log, which keeps the
  emulator small: the DSP's job here is to be written to.
- **The I/O ports** the main CPU would talk through, left as the snapshot
  has them (a running song does not wait for the game).
- **The IPL ROM** (64 bytes) for drivers that jump into it.

How long to run: the ID666 length when the tag has one, otherwise until
the song's register writes repeat (the loop point), capped at a few
minutes of song time.

Speed matters because this is pure Python. A three-minute song is about
180 million CPU cycles, tens of millions of instructions; an
interpreter's first target is a minute or two per song on a laptop,
with a progress screen like UPDATE's. If that target is missed: a tighter
dispatch loop first, then stopping at the detected loop point; a compiled
core is a decision for later, not a default.

### 4. The translator

The register log becomes musical events, then measurements:

- **Notes.** A `KON` on a voice is a note: its sample (`SRCN` at that
  moment), its pitch (the sample's fundamental, measured once by the
  reader, times pitch / `0x1000`, to a MIDI note and cents), its volume and
  pan, its length (to the `KOFF` or to where the envelope reaches zero).
  Pitch slides and vibrato show up as pitch writes between notes.
- **Tempo and grid.** Note onsets against the timer clock give the beat
  and the rows; swing shows up as a regular long-short offset.
- **Roles.** From the notes, not the snapshot: drums are the unpitched or
  fixed-pitch percussive samples on the grid; the bass is the lowest
  sustained line; the melody is the line with the most varied, phrase-shaped
  motion in the upper register; harmony is notes sounding together under
  it; the arp is fast repeated chord tones. Each guess carries its
  evidence, and the user can overrule it.
- **Habits.** The translated song measured with the same yardsticks the
  generator is judged by (ANALYSIS.md): tempo, scale and key motion,
  energy and density, harmony mode (held, stabbed, chugged), bass style,
  drum density and groove, echo settings and which roles send. Over a
  whole soundtrack they become the pack's weighted habits.

### 5. Two outputs

- **SPC to IT, one to one.** The translated song written as an `.it`
  module with the decoded samples: the same notes on the same samples.
  This is the translator's proof: render the `.it` with libopenmpt, render
  the `.spc` with a reference player, compare onsets, pitch and loudness
  (below). It is also a feature in its own right (a game's song in a
  tracker), for the user's own files.
- **A pack.** The soundtrack's samples as the pack's voices (envelopes
  baked and loops kept, the way `samples.dsp` finishes the SNES voices),
  the roles from the translator with the user's corrections, the habits
  measured over every song. The generator composes new songs with it,
  as with any built-in pack; it is chosen in the player's PACKS panel
  (below), kept apart from the built-in sounds.

### 6. The player: PACKS

Imported packs get their own place, apart from the built-in sounds and
SET (decided 2026-10-18):

- **A PACKS tile** after MIX in the tool row (AUTO, SET, MIX, PACKS),
  opening a panel inside the window the way SET and MIX do. Room for it
  comes from the GENERATE button, which can shorten from
  "GENERATE NEW TRACK" to "GENERATE"; checked at the narrowest screens
  the window is checked at.
- **The list.** One row per imported pack: its name, the game (from the
  files' ID666 tags), how many songs it was measured from, and USE,
  ROLES (the role picker again) and DELETE.
- **IMPORT** at the bottom of the panel: choose `.spc` files or a folder;
  a progress screen over the window while each song is emulated, the way
  the update screen shows its work ("emulating song 3 of 24"); then the
  role picker (hear each sample, see what the translator decided and why,
  change it); then the pack joins the list.
- **USE** makes the pack the sound for GENERATE and auto-generate. One
  sound is in use at a time: SET's SOUND row then reads
  "imported: <name>", and choosing a built-in sound there switches back.
- **Not in random.** SOUND's random draw never picks an imported pack
  (decided 2026-10-18; an "include in random" switch can come later if
  it is missed).
- **Songs** from an imported pack are songs like any other: the mixer,
  KEEP and the ten-song prune apply. The song message names the pack,
  and a song keeps playing after its pack is deleted, since its samples
  are inside the `.it` file.

Imported packs live in the user's settings folder.

## Checking each step

Measured, as everything here is:

- **Reader (done):** over the 258 snapshots the four packs were built
  from, the 4,728 samples the research tools found decode to exactly twice
  their values in 3,414; the other 1,313 differ only where the research
  decoder let a sum run past 15 bits, which the chip wraps. Of the 262
  samples the voices were playing, the plausibility test keeps 259 (all
  262 are listed, being played) and drops 70% of the directory's other
  entries. 56 of the 61 played loops that never repeat exactly settle
  within the seam tolerance.
- **Emulator:** the onsets in its key-on log line up with the onsets in
  the reference player's audio of the same snapshot, within a few ms, for
  every driver in the test set (the four built-in packs' games: three
  Square titles, whose drivers differ by version, and Capcom's Mega Man X). A reference player is a development
  tool only (for example ffmpeg built with libgme), never a dependency.
- **Translator:** the one-to-one `.it` against the reference render:
  onset match, pitch error in cents, loudness envelope correlation.
- **Habits:** a ground truth already exists. The four built-in packs were
  tuned by hand from these same games; importing each game's snapshots
  should land the measured habits near the hand-made `PACK` tables (FFVI's
  echo is 80 ms with feedback 0.64 in every snapshot, for one). Where they
  disagree, either the translator or the hand tuning is wrong, and the
  numbers say which to look at.
- **Determinism:** a song from an imported pack is a function of the seed,
  the version and the pack's files, like any other.

## Order

Each step is its own branch and pull request, shippable on its own:

1. The pack file format (built), proven on the built-in packs by a
   round-trip test.
2. The SPC reader (built), checked against the research tools.
3. The emulator, tested against reference renders. The long one.
4. The translator and SPC to IT, which proves 3.
5. The pack from a soundtrack, checked against the built-in packs.
6. The player's PACKS panel: the list, IMPORT, the role picker, USE.

## Risks

- **Emulator accuracy.** Drivers lean on timer behaviour and odd
  instructions; one wrong flag stalls a song. The test set has four
  drivers; others will find new faults.
- **Speed** in pure Python (above).
- **Drivers that load samples during the song** (from the main CPU): a
  snapshot holds only what was loaded when it was taken; such songs
  import with what was there.
- **Pitch modulation, noise and echo tricks** some scores rely on:
  logged and translated where IT can say it, reported where it cannot.
- **Role guesses** will be wrong sometimes; the role picker exists for
  that.

## The files are the user's

The repository ships the code, never game files or anything extracted
from them: the samples are the publishers' recordings. Imported packs
and the songs made with them contain those samples, so they stay on the
user's machine. A future "share a pack" feature leaves imported samples
out. The built-in packs stay as they are, re-synthesised from
measurements, borrowing nothing.

## Related

The Road Rash pack (ROADMAP.md) reads Genesis VGM files, which are
already register logs: no emulation needed, and the translator (step 4)
works on them unchanged once the YM2612's registers are mapped. The
two plans share that step.
