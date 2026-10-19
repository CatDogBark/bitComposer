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
| ActRaiser | Yuzo Koshiro | [Nintendo: N-SPC](snes/n-spc.md) | 19 (19) |
| Cybernator | Masanao Akahori | [NCS](snes/ncs.md) | 15 (15) |
| Donkey Kong Country 2 | Dave Wise | [Rare](snes/rare.md) | 109 (109) |
| Dragon Quest V | Koichi Sugiyama | [Chunsoft](snes/chunsoft.md) | 50 (50) |
| EarthBound | "Akio Ohmori, Ritsuo Kamimura, Ke" (cut off) | [Nintendo: N-SPC](snes/n-spc.md) | 206 (203) |
| Final Fantasy VI | Nobuo Uematsu | [Square: AKAO](snes/akao.md) | 82 (79) |
| Jurassic Park Part 2 | Dean Evans, Jonathan Dunn | [Ocean](snes/ocean.md) | 16 (16) |
| Kirby Super Star | Jun Ishikawa, Dan Miyakawa | [Nintendo: N-SPC](snes/n-spc.md) | 70 (69) |
| Lufia II | Yasunori Shiono | [Neverland](snes/neverland.md) | 63 (62) |
| Mega Man X | "Setsuo, Tomozou, Sato, Yuko, Kir" (cut off) | [Capcom: Mega Man X's](snes/capcom.md) | 35 (35) |
| Ogre Battle | Masaharu Iwata, Hitoshi Sakimoto, Hayato Matsuo | [Quest](snes/quest.md) | 26 (26) |
| Pilotwings | Soyo Oka | [Nintendo: Pilotwings'](snes/pilotwings.md) | 21 (21) |
| Plok | Geoff & Tim Follin | [Plok's](snes/plok.md) | 20 (20) |
| Pocky & Rocky | Hiroyuki Iwatsuki | [Nintendo: N-SPC](snes/n-spc.md) | 24 (24) |
| Secret of Evermore | Jeremy Soule | [Square Soft US: Secret of Evermore's](snes/secret-of-evermore.md) | 72 (70) |
| Secret of Mana | Hiroki Kikuta | [Square: Secret of Mana's](snes/secret-of-mana.md) | 69 (68) |
| Star Fox | Hajime Hirasawa | [Nintendo: N-SPC](snes/n-spc.md) | 51 (50) |
| Super Bomberman 4 | Jun Chiki Chikuma | [Hudson](snes/hudson.md) | 26 (26) |
| Super Castlevania IV | Masanori Adachi, Taro Kudou | [Nintendo: N-SPC](snes/n-spc.md) | 36 (36) |
| Super Ghouls'n Ghosts | Mari Yamaguchi | [Capcom: Super Ghouls'n Ghosts'](snes/super-ghouls-ghosts.md) | 23 (23) |
| Super Metroid | Kenji Yamamoto, Minako Hamano | [Nintendo: N-SPC](snes/n-spc.md) | 36 (36) |
| Super Turrican 2 | Chris Hülsbeck | [Factor 5](snes/factor-5.md) | 34 (34) |
| Top Gear | Kemco sound team | [Nintendo: N-SPC](snes/n-spc.md) | 7 (7) |
| Uniracers | Colin Anderson | [Plok's](snes/plok.md) | 10 (10) |
<!-- end generated -->

Composers are as the tags give them unless the SPC folder's `drivers.json`
gives a fuller credit: a cut-off or missing credit is left as it is rather
than filled in from memory (an SPC tag's field holds 32 characters). A
driver goes by its name where that is well established (AKAO, N-SPC), else
by its developer where that is the one driver of theirs found so far, else
by its game (Capcom's two: Mega Man X's, Super Ghouls'n Ghosts'). Which games
share a driver is measured from their code (`tools/spc_check.py family`).

## Composers

### SNES

<!-- generated: composers snes -->
| Composer (as the tags credit) | Games | Drivers |
|---|---|---|
| "Akio Ohmori, Ritsuo Kamimura, Ke" (cut off) | EarthBound | [Nintendo: N-SPC](snes/n-spc.md) |
| Chris Hülsbeck | Super Turrican 2 | [Factor 5](snes/factor-5.md) |
| Colin Anderson | Uniracers | [Plok's](snes/plok.md) |
| Dave Wise | Donkey Kong Country 2 | [Rare](snes/rare.md) |
| Dean Evans, Jonathan Dunn | Jurassic Park Part 2 | [Ocean](snes/ocean.md) |
| Geoff & Tim Follin | Plok | [Plok's](snes/plok.md) |
| Hajime Hirasawa | Star Fox | [Nintendo: N-SPC](snes/n-spc.md) |
| Hiroki Kikuta | Secret of Mana | [Square: Secret of Mana's](snes/secret-of-mana.md) |
| Hiroyuki Iwatsuki | Pocky & Rocky | [Nintendo: N-SPC](snes/n-spc.md) |
| Jeremy Soule | Secret of Evermore | [Square Soft US: Secret of Evermore's](snes/secret-of-evermore.md) |
| Jun Chiki Chikuma | Super Bomberman 4 | [Hudson](snes/hudson.md) |
| Jun Ishikawa, Dan Miyakawa | Kirby Super Star | [Nintendo: N-SPC](snes/n-spc.md) |
| Kemco sound team | Top Gear | [Nintendo: N-SPC](snes/n-spc.md) |
| Kenji Yamamoto, Minako Hamano | Super Metroid | [Nintendo: N-SPC](snes/n-spc.md) |
| Koichi Sugiyama | Dragon Quest V | [Chunsoft](snes/chunsoft.md) |
| Mari Yamaguchi | Super Ghouls'n Ghosts | [Capcom: Super Ghouls'n Ghosts'](snes/super-ghouls-ghosts.md) |
| Masaharu Iwata, Hitoshi Sakimoto, Hayato Matsuo | Ogre Battle | [Quest](snes/quest.md) |
| Masanao Akahori | Cybernator | [NCS](snes/ncs.md) |
| Masanori Adachi, Taro Kudou | Super Castlevania IV | [Nintendo: N-SPC](snes/n-spc.md) |
| Nobuo Uematsu | Final Fantasy VI | [Square: AKAO](snes/akao.md) |
| "Setsuo, Tomozou, Sato, Yuko, Kir" (cut off) | Mega Man X | [Capcom: Mega Man X's](snes/capcom.md) |
| Soyo Oka | Pilotwings | [Nintendo: Pilotwings'](snes/pilotwings.md) |
| Yasunori Shiono | Lufia II | [Neverland](snes/neverland.md) |
| Yuzo Koshiro | ActRaiser | [Nintendo: N-SPC](snes/n-spc.md) |
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
