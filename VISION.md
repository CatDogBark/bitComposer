# Vision

**A procedural composition engine with its own musical research pipeline:
it studies how game music was made, and composes its own.**

bitComposer reconstructs music from classic game consoles into Impulse
Tracker (IT) modules, beginning with the Super Nintendo (its SPC700 sound
CPU and S-DSP sound chip), with the Sega Genesis (YM2612 and PSG) next. The
game's own music driver runs in an emulator, and what it tells the sound
chip becomes notes, instruments and effects in a tracker file anyone can
open and edit. Where the hardware does something no tracker can say, such
as one voice bending another's pitch at audio rate, that part is kept as
the emulator played it.

These reconstructions are research material. Measuring how the original
composers built their music (melodic contour, harmony and voicing, rhythm
and groove, arrangement, how the instruments share the space) gives the
generator new resources to compose with: habits, palettes, grooves and
ranges, stated as data.

What crosses from game music into the generator is measurement, never
material: statistics and relationships, not melodies and not samples. A
pack imported from a game's files uses that game's samples, and it stays
in the user's own collection, like the files it came from.

The generator writes its songs in the same IT format, so they are measured
with the same tools as the music it studied and compared against it: a
generated song either sits inside the range human composers worked in or
outside it, and the measurement tells which.

**The pipeline is a loop:**

Classic game audio → hardware emulation → IT reconstruction → musical
analysis → generation resources → original IT compositions → the
listener's keeps → analysis of what was kept → refinement ↻

The listener closes the loop. Every song the player makes is provisional
until someone keeps it, and only kept songs feed back into refinement: a
generator tuned on everything it makes would drift toward what it already
does. Measurement says where a song sits; the listener says whether it is
worth keeping.

The goal is not to imitate existing songs or to prescribe what a song must
be. It is to widen what the generator knows about how musical parts relate,
so that an enormous variety of original music can come from those
relationships working together.

## Where it stands

- **Now:** the generator, with seven sounds (four of them style packs
  measured from game soundtracks) and packs as data files; the player, with
  KEEP; the SNES emulator, with its sound CPU passing all 254,000
  SingleStepTests cases and its sound chip checked against a reference
  player, by measurement and by ear; SPC to IT.
- **Next:** packs measured from a soundtrack by the importer, and the
  player's PACKS panel (`docs/SPC-IMPORT.md`); the Sega Genesis, through VGM
  register logs.
- **Later:** the keep-and-refine loop.

*Endless music. Keep what moves you.*
