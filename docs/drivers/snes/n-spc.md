# Nintendo: N-SPC

Nintendo's sound driver, known as N-SPC, in Nintendo's own games and in
other publishers' (Enix's ActRaiser, Natsume's Pocky & Rocky, Konami's Super
Castlevania IV, Kemco's Top Gear). Grouped by its code (`spc_check.py
family`): the eight games share 0.26 to 0.5 of their driver code with one
another and 0.05 or less with any other driver here, and six of them carry
N-SPC's velocity table (19 32 4C 65 ...), EarthBound a variant of it.
Kirby Super Star shares the code without the table.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| ActRaiser | Yuzo Koshiro | 19 (19) |
| EarthBound | "Akio Ohmori, Ritsuo Kamimura, Ke" (cut off) | 206 (206) |
| Kirby Super Star | Jun Ishikawa, Dan Miyakawa | 70 (70) |
| Pocky & Rocky | Hiroyuki Iwatsuki | 24 (24) |
| Soul Blazer | Yukihide Takekawa, Kazz Tomaya | 20 (20) |
| Star Fox | Hajime Hirasawa | 51 (51) |
| Super Castlevania IV | Masanori Adachi, Taro Kudou | 36 (36) |
| Super Metroid | Kenji Yamamoto, Minako Hamano | 36 (36) |
| Terranigma | "Miyoko Kobayashi, Masanori Hikic" (cut off) | 57 (57) |
| Top Gear | Kemco sound team | 7 (7) |
| Yoshi's Island | Koji Kondo | 48 (48) |
| The Legend of Zelda: A Link to the Past | Koji Kondo | 36 (36) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 500 Hz, key-ons anywhere in a tick (501 songs); 500 Hz, on its ticks (41); 250 Hz, key-ons anywhere in a tick (29) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 5.6 a note (90 %: 51.4) |
| Pitch modulation | in 0 of 610 songs |
| Noise | in 0 of 610 songs |
| Echo | 32 ms, feedback 0.23 (58 songs); 32 ms, feedback 0.39 (45); 0 ms, feedback 0.0 (36); 16 ms, feedback 0.01 (27) |
| Echo volume | 0.0 (102 songs); 0.39 (93) |
| Echo sides inverted | in 2 of 610 songs |
| Echo filter at DC | 0.99 (213 songs); 1.0 (174) |
| Master volume | 96 (241 songs); 112 (206) |
| Density | 493 notes in a song's first minute; a note 0.15 s |
<!-- end generated -->

- **Clock**: a 500 Hz timer in nearly every song (250 Hz in Super
  Castlevania IV), its tempo a count of those ticks, so key-ons land
  anywhere in them: modules use 100 rows a second.
- **Envelopes**: the instrument's ADSR at key-on, left alone while it sounds.
- **Pitch**: vibrato and slides, heaviest in EarthBound (25 pitch writes a
  note) and Pocky & Rocky (17); EarthBound also sweeps notes up from pitch
  0 and pans held notes slowly from side to side.
- **Echo**: each game its own. Star Fox 32 ms at 0.39 feedback, Pocky &
  Rocky 96 ms at 0.56, Kirby Super Star 80 ms at 0.39 to 0.47, EarthBound 16
  to 48 ms, Top Gear 160 ms at full echo volume, Super Metroid little (0.08 in
  14 songs), Super Castlevania IV none. Star Fox, Pocky & Rocky and a third of
  EarthBound's songs filter it to a band (0.1 at DC, as Capcom's); three of
  Super Metroid's boost it (4.1 at DC).
- **Master volume**: 96 in most games, 112 in EarthBound, full in Kirby
  Super Star and Super Castlevania IV.
- No pitch modulation and no noise in any of the 449 songs.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 610 | 0.97 (0.86) | 0.51 (1.10) | 0.99 (0.94-1.02) | 0.99 (0.98) |
<!-- end generated -->

## The converter

What these games brought: a held note's pan followed as the driver moves
it (EarthBound: One Fateful Night's voice from a contour of 0.40 to 0.96); a
note keyed at pitch 0 and given its pitch just after played from that pitch
(EarthBound's sweeps up; You've Got a New Friend! from a 3.3 dB gap to 0.3);
quiet notes kept off the bottom of IT's volume steps by raising the channel
volumes and lowering the global volume (EarthBound's quiet voices measured
silent, Kirby's swells to 3 of 127 a third too loud); a sample's octaves
chosen to place the most of its notes on IT's keys (a sweep from near 0 had
pushed the rest of its sample off the top).

## For generation

The most common driver here, and its games differ more than they share:
the echo is chosen per game (and often per song), the clock and envelopes
are the driver's. What is a game's own: EarthBound's moving pitch and pan,
Top Gear's long full-strength echo, Super Castlevania IV's dry sound.

## Open

- Super Metroid's Wrecked Ship (3.5 dB off, at 0.81 of its level): its
  trailing echoes are the composer's, written as notes (voice 4 replays
  voice 0 on the same sample and pitch 0.146 s later); on IT's 10 ms rows
  the copy comes 4 ms late, which turns the two held tones from adding to
  cancelling ([known limits](README.md#known-limits)).
- EarthBound's A Flash of Memory and The Heroes Return (part 1): voice 3 at
  three times its level (10 dB).
- Single voices with the wrong tone: Kirby Super Star's Battle Windows
  (voice 1, 0.16), EarthBound's Rough Landing (voice 7, 0.23) and Oncoming
  Foe (voice 4), Top Gear's Ending Theme (voice 4, at 0.44 of its level).
