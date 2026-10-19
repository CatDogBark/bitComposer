# Music drivers

The record of every game the import has been tested against, by console and
music driver: who wrote the music, what the driver does with the sound chip
(measured, not assumed), how closely the converted module matches the
original, and what is still off. It is the converter's reference, and the
start of the generator's: a driver's and a composer's habits, measured here,
are what a pack is made of (`../SPC-IMPORT.md`, `../../VISION.md`).

A game's music driver matters more than the game. Many games share a
driver, and a driver's habits (how it keys notes, shapes envelopes, uses the
echo) are what the converter has to understand; a composer's are what the
generator can learn from. So each driver family has a file of its own, under
its console:

- [`snes/`](snes/README.md): the SNES sound chip, what the converter carries
  for it, its limits, and its drivers.
- Sega Genesis: later (the YM2612 and the PSG, through VGM register logs).

Each driver file has the same parts: its games and composers, what the
driver does (its clock, envelopes, pitch writes, pitch modulation, noise,
echo, master volume, density), the scores, what the converter does for it,
what it means for generation, and what is open.

## The measures

Each song is converted at its full length (to catch failures and IT's
limits), then its first 30 s are compared with the console emulator's own
output, the whole mix and each voice alone (the emulator can leave voices
out; the converted song says which of its channels carry each voice). The
emulator is the reference: against libgme it correlates at 0.93 to 0.98
sample for sample, and listened to side by side it sounds the same.

- **contour**: how the loudness moves (50 ms windows, each side the
  original sounds on). A steady sound, such as a wind bed, scores low even
  when it matches, so read it with the gap.
- **gap**: the median distance in dB between the two loudness contours.
- **level**: the module's RMS over the original's.
- **tone**: the two averaged spectra, correlated. A wrong timbre at the
  right loudness shows here and only voice by voice (The Phantom Train's
  noise-shaken tone came out a steady beep; the whole mix hid it).

What a driver does is measured over each song's first minute, medians
across a game's songs unless a number says otherwise. CONTRIBUTING.md
("Checking the SPC converter") has the commands.

## Games

### SNES

<!-- generated: games snes -->
| Game | Composer (as the tags credit) | Music driver | Songs (scored) |
|---|---|---|---|
| Final Fantasy VI | Nobuo Uematsu | [Square: AKAO](snes/akao.md) | 82 (79) |
| Mega Man X | "Setsuo, Tomozou, Sato, Yuko, Kir" (cut off) | [Capcom](snes/capcom.md) | 35 (35) |
| Secret of Evermore | Jeremy Soule | [Square Soft US: Secret of Evermore's](snes/secret-of-evermore.md) | 72 (70) |
| Secret of Mana | Hiroki Kikuta | [Square: Secret of Mana's](snes/secret-of-mana.md) | 69 (68) |
<!-- end generated -->

Composers are as the tags give them unless the SPC folder's `drivers.json`
gives a fuller credit: a cut-off or missing credit is left as it is rather
than filled in from memory (an SPC tag's field holds 32 characters). Driver
names are given only where they are well established; otherwise a driver is
named for its game.

## Composers

### SNES

<!-- generated: composers snes -->
| Composer (as the tags credit) | Games | Drivers |
|---|---|---|
| Hiroki Kikuta | Secret of Mana | [Square: Secret of Mana's](snes/secret-of-mana.md) |
| Jeremy Soule | Secret of Evermore | [Square Soft US: Secret of Evermore's](snes/secret-of-evermore.md) |
| Nobuo Uematsu | Final Fantasy VI | [Square: AKAO](snes/akao.md) |
| "Setsuo, Tomozou, Sato, Yuko, Kir" (cut off) | Mega Man X | [Capcom](snes/capcom.md) |
<!-- end generated -->

The tables between "generated" markers here and in the console folders are
written by `tools/spc_check.py doc` from `traits` and a sweep; everything else
is written by hand. Each console's tables are its own, so one console's tool
never rewrites another's.

## Adding a console

A folder of its own beside `snes/`: a README for the sound chip (what the
converter carries for it, its limits, how to add a game) and a file per
driver family, in the same parts as the SNES ones, so a composer's or a
driver's habits read the same whatever the hardware.
