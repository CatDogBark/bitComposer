# Phase 6: the writer as the generator

Planned in outline (2026-10-29, from the owner's direction after 1.2.0rc3);
the detail is written as each piece begins. See `../IDIOM.md`. This phase
supersedes phase 5's picker as it was designed (Chip / SNES on imports /
game packs); phase 5's pieces that survive are named below.

## Goal

GENERATE writes songs the way phase 4 does, from a vocabulary and a set of
sounds, with no import needed; the old generator stays as Classic. Packs
as one thing (voices and habits and tables in one file) dissolve into two
libraries the listener picks from separately: sounds and songs. The
product's version at the end of this phase is 2.0.

## Decided (2026-10-29)

- **A vocabulary ships: Final Fantasy VI's.** The 95 tables fitted on its
  67 songs (about 3.4 MB of JSON, no samples) are the default vocabulary,
  named as what they are. This reverses one point of the 2026-10-23
  decision (nothing fitted on our readings ships); the owner's reading is
  that FFVI's vocabulary is where the writer stands and that naming it is
  honest. A pooled SNES vocabulary over the 39-game corpus is unmeasured
  and not a default until it is (the measurements below).
- **Classic stays.** The built-in generator (`composer.py`, `melody.py`,
  `pattern.py`) is a mode beside the writer: it needs no vocabulary, it
  keeps the chip and Genesis palettes their songs until a Genesis
  vocabulary exists, and its seventy songs stay byte for byte what rc1
  wrote.
- **Two libraries, chosen separately.**
  - *Sounds*: the built-in synthesized sets (today's `ffvi`, `mana`,
    `evermore`, `megamanx` packs are code, not recordings) and a game's own
    samples when the listener has imported it (the pack file's voices,
    WAVs and loudness beside a JSON; the format stays).
  - *Songs*: the readings database, every imported song read as music with
    its per-voice loudness (the lead pass). From it a vocabulary is fitted
    over a scope: one game, or everything imported. The shipped FFVI
    vocabulary stands beside these.
- **GENERATE is three choices**: a vocabulary (built-in FFVI, my library,
  one imported game), a sound set (a built-in set, a game's), and the two
  switches of phase 5 (carry a theme; the band comes back). The writer
  binds the vocabulary's sample ids where the sound set has them and falls
  back to the pool by register where it does not (`whole.samples_for`
  does this today: FFVI's vocabulary on the Mana sounds runs from the
  command line).
- **The reference set never ships.** The tune-copy check runs in CI over
  songs written from the shipped vocabulary, against the machine-local
  reference set; the product does not carry the games' phrases.
- **What the panel shows of a vocabulary** is the map (`vocabulary-map.md`)
  and the words (`VOCABULARY.md`), in the panel's own terms; whether a
  listener can switch a table's rows is still open.

## What stands from phase 5

The format 2 pack file (tables beside voices) as the on-disk form of a
fitted vocabulary and of a game's sounds; the importer keeping the
listener's readings across imports; the builder's scope (a game, or every
game of a system), recorded in the tables' source; the two switches; the
drum namer's kit and the sample envelope (done); `PACKS.md` describing
format 2. Dropped: the picker as Chip / SNES-on-imports / game packs, and
the "too few songs" warning as the only way to a vocabulary (it stays as
the warning on a library vocabulary).

## What the engine already does

- `tools/whole.py` composes a whole song in about 2.5 s on the laptop
  (seeds 171-172, 2026-10-29), so GENERATE's wait is a progress state, not
  a queue.
- The player's GENERATE runs the command line's own argument parsing in a
  thread (`player/engine.py`, `cli.compose_from_args`), so the writer
  plugs in as a mode of the CLI; the engine does not change.
- A built-in sound set with a tables file already writes
  (`tools/whole.py --pack ffvi --tables TABLES.json`).

## The work, provisionally

1. **The engine (2.0rc1).** The CLI's writer mode (`--style`, `--sounds`,
   the switches) and GENERATE through it; the vocabulary fitted over a
   scope and stored as a format 2 file under the data folder; the shipped
   FFVI tables as package data; the readings kept across imports; the
   import pipeline running the full readers and the lead pass; the pack
   loader rewritten for two libraries (and with it the voice-key collision
   reported 2026-10-22: two packs whose `name_sample` keys coincide); the
   copy check in CI; Classic as a mode.
2. **The UI (2.0rc2).** `Main.qml` (2,120 lines) reorganized: Style,
   Sounds and Library in place of SOUND and PACKS; import progress; "N
   songs imported" on a library vocabulary; the switches beside the style.
3. **Later: Genesis readers** (VGM), which is what finally retires Classic.

## Measurements before the engine (1.2.0rc4)

- **The pooled fit.** FFVI's tables against tables fitted over the 39-game
  corpus, twenty songs written from each, on the phase 4 measures and
  tools/salience.py: whether a pooled SNES vocabulary is a default or a
  curiosity.
- **The song-count threshold.** FFVI's tables fitted on 10, 20, 40 and 67
  songs, twenty songs from each: where the one-draw-a-song words (balance,
  layout, habits) starve. The number the library vocabulary's warning
  uses.
- **Import time per song.** The readers and the lead pass (every voice of
  every song rendered through the emulator) timed on FFVI: whether an
  import is a progress bar or an overnight job, and what runs in the
  background.

## Built

- **2.0rc1, piece 1 (2026-10-30).** The shipped vocabulary:
  `bitcomposer/vocabularies/ffvi.json.gz` (pack4's 95 tables, 365 KB
  gzipped; `bitcomposer.vocabularies` lists, labels and loads them) and the
  command line's writer mode: `bitcomposer --vocabulary ffvi [--pack SET]
  [--carry-theme] [--band-returns] -s SEED` (`bitcomposer/written.py`:
  the whole-song writer on a built-in SNES sound set, the seed picking the
  set and the title when not named, the module's message naming the
  vocabulary, the sounds and the seed). A song writes in under a second on
  the laptop. Tests: `tests/test_written.py`; the determinism test now
  writes from the shipped vocabulary.
- **2.0rc1, piece 2 (2026-10-30).** GENERATE writes from it: SET's first
  row is STYLE (Classic, or a shipped vocabulary the backend lists), with
  THEME and RETURNS rows for the two switches while a vocabulary is
  picked; the window's flags are then the writer's alone (the vocabulary,
  the SNES sound set when SOUND names one, the switches) and none of
  Classic's, the settings summary says "written from Final Fantasy VI",
  and the choice is saved with the other settings. A written song's
  message carries a `layout:` line, so the window names its channels by
  part.
- **2.0rc1, piece 3 (2026-10-30).** The library's vocabularies. An import
  keeps its readings in the data folder's database (`store.keep` from
  `pack._make`), names the game in the pack's WHY file, counts the game's
  tables with its samples' loudness into the pack as format 2
  (`packtables.into`) and counts the library vocabulary again over every
  song imported, all games together (`vocabularies.refit_library`, to
  `vocabularies/library.json` in the data folder). `bitcomposer.vocabularies`
  names them beside the shipped ones (`library`, `pack:<name>`), with the
  songs behind each and whether it is ready (MIN_SONGS 40, the measured
  threshold); the window's STYLE row offers the ready ones, the command
  line takes any. A pack's vocabulary writes on the pack's own samples
  unless a built-in set is named; `--pack-file` names an imported pack as
  the sounds for any vocabulary.
- **2.0rc1, pieces 4 and 5 (2026-10-30).** The import runs the lead pass
  (`translate/lead.py`: each voice of each song rendered alone, the melody
  label moved where another voice carries the tune) after the readings
  are kept and before the tables are counted, so the tokens count on the
  heard lead as FFVI's shipped ones do. The pack loader refuses a pack
  whose registered voice names (`name_key`) coincide with a loaded pack's,
  naming the pack to rename (the bug reported 2026-10-22; the full
  Sounds-and-Songs loader rewrite waits for the 2.0 window, since the
  format and the panel it serves stay until then). Also found: the module
  splits had not re-exported two annotated module-level names
  (`rhythm.SAMPLE_LOUDNESS`, `SAMPLE_STRIKE`); fixed. Not yet: the copy
  check (the reference set is machine-local, so it is a release check run
  on the owner's machines over songs written from the shipped vocabulary,
  not a CI job), the panel saying "N songs read, the vocabulary needs 40",
  SOUND limited to SNES sets while a vocabulary is picked.

## Measured (2026-10-30, Ragnarok; `~/diags/bitcomposer/idiom/phase6`)

- **Import time per song.** The readers: 0.6 s a song (five FFVI songs,
  3 s wall with four workers on 16 cores). The lead pass, every voice
  rendered alone through the emulator: 3.5 s a song with a melody (three
  songs, 10.5 s). A whole FFVI import, 82 songs, is about six minutes: a
  progress bar, not an overnight job. (The readers name the game from the
  folder, "Final Fantasy 6" from `ffvi-spc`'s files; the lead pass must be
  given that name.)
- **The song-count threshold.** FFVI's tables fitted on 10, 20 and 40 of
  its songs (one seeded draw each) beside the full 67, twenty seeds
  written from each (201-220, with stems and salience) and then forty
  more (221-260, measures only). At twenty seeds the tune's variety looked
  halved under 40 songs; at forty seeds that was seed noise (the full fit
  itself moved from 12 to 11 distinct tune cells between seed sets). What
  holds across both passes: the drums starve first and do not recover by
  40 songs, 2.1, 3.0 and 3.6 strikes a bar at 10, 20 and 40 songs against
  7.0 on the full fit and 6.9 in the game (the kit words and the drum
  chains, conditioned on kit, tempo and habit, are the thinnest tables);
  the counter plays fewer bars (0.77, 0.75, 0.81 against 0.85 and 0.90);
  the tune's balance sits a dB or two further back (medians -6.5, -6.7,
  -5.4 dB under the loudest other line against -5.3). Everything else is
  inside the seed spread. The library vocabulary's warning: under 40
  songs the drums are not the game's; a whole game's worth is what the
  full fit had.
- **The pooled fit.** The tables fitted over the 39-game corpus, 1,562
  songs with a grid, write clean songs (no failures over sixty), and on
  FFVI's own yardsticks sit near the FFVI fit on most measures (distinct
  tune cells 12.5 and 12 against 11-12, drums 7.5 and 8.4 strikes a bar
  against 6.6-7.0, the tune's echoes 0.43-0.45 against 0.45-0.50). The
  differences are what 39 games in one draw should give: a less stepwise
  tune (0.50-0.57 of its moves against FFVI's 0.64), a wider harmony
  (five to seven distinct voicings against three), and the tune a median
  7.2 dB under the loudest other line against 5.3 on the same twenty
  seeds. A pooled SNES style is a second vocabulary for later, not the
  default; FFVI's stands.

## Exit criteria

- GENERATE on a fresh install writes a song from the shipped FFVI
  vocabulary on a built-in sound set, and the song passes phase 4's
  measures and the copy check.
- A game imported in the player gives a sound set and a game vocabulary,
  and a song from them passes the same.
- Classic's seventy songs are byte for byte rc1's.
- A 1.x pack file still loads as a sound set.

## Open questions

- Which built-in sound set is the default under the FFVI vocabulary (the
  `ffvi` set is the obvious one; the vocabulary's sample ids bind to a
  game's samples only when that game is imported).
- Whether the panel lets a listener switch a table's rows, and what that
  means for a song's plan.
- Packs by composer and the Genesis path, as phase 5 left them.
