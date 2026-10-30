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
  (`rhythm.SAMPLE_LOUDNESS`, `SAMPLE_STRIKE`); fixed.
- **2.0rc1, piece 6 (2026-10-30).** The copy check as a release tool:
  `python tools/copycheck.py --vocabulary ffvi --seeds 1-100` writes the
  songs as the product does (no reference set at hand, so no phrase is
  drawn again) and probes every four-bar window of each tune, from every
  bar, against the games' four-bar phrases (the reference set, kept
  outside the repository; not a CI job for that reason). Run before a
  vocabulary ships: on the shipped FFVI vocabulary, seeds 1-100 plain and
  101-200 with both switches, 4,160 windows of 200 songs, none copies a
  game phrase (rhythm and intervals together); 111 share a rhythm alone
  and 9 the intervals alone, as any two tunes in a style do. Not yet: the
  panel saying "N songs read, the vocabulary needs 40", SOUND limited to
  SNES sets while a vocabulary is picked.

- **2.0rc1, piece 7 (2026-10-30, the owner's call).** The writer is
  GENERATE, with no game's name in front of the listener. The shipped
  vocabulary is `default` (its `source` records that it was fitted on
  Final Fantasy VI's 67 songs; the README says so plainly), the window
  calls it bitComposer's own, a song's message reads "Written by
  bitComposer on the Evermore sounds (seed 7)", and the command line
  writes without a flag (`--classic` is the 1.x generator; `--vocabulary`
  names your library or one of your games). SET's rows are WRITER
  (bitcomposer, classic), FROM (shown once a library or game vocabulary
  is ready), THEME and RETURNS. The listener's own imports keep their
  games' names; the Song Checks, the docs and the tools keep saying FFVI,
  where the comparison is the point.

## Built, 2.0rc2: a voice fitted to its part, and bitComposer's own set

The smoke test's listener heard the writing holding up and the voices
holding it back, and the plan log said why on every seed: "none in the
pack; the pool rule chooses". On a built-in set the pool rule had nothing
to score. The vocabulary's sample tables (ranges, sample_speeds,
sample_lengths, sample_ambitus, part_samples) name samples by the game's
ids; a built-in voice has a name, not an id; `best_sample` found no range
for any voice of the pool and fell to `rng.choice`. A tune planned at
72-92 could land on a cello, a 200 ms swell on sixteenths, and the
register bound fell back to the plan's.

- **Profiles** (`packs.profile`): every built-in pitched voice carries the
  range it sounds right in (each pack's `RANGES`, set by ear and by the
  instrument the recipe models, not measured from any game), a speed from
  its measured attack (struck: 24 a second; a 10 ms attack 12; 30 ms 8;
  60 ms 6; 120 ms 4; 200 ms 3; slower 2) and a shortest note (the
  sample_lengths classes, at 1.5 times the attack). `best_sample`,
  `sample_speed`, `sample_floor` and `ambitus_of` answer from the profile
  where the tables know nothing of the id; the pool strips the set's
  prefix from a voice's name, so the set's name travels with the lookup.
  The plan log names each pick, its register, its speed and its range.
- **The set** (`packs/bit.py`): 34 generic instruments and a kit,
  synthesised from descriptions, modelled on no game's bank, with
  something slow and something quick in every register the shipped
  vocabulary reaches (melody 40-92, counter 48-84, accompaniment 40-80 at
  2 to 12 a second, bass 28-56). It is the writer's default; the four
  styled sets are Classic's and a written song takes one only by name.
- **Measured** (seeds 201-220 on the shipped vocabulary, the laptop): the
  written measures on the FFVI set before and after the fit are the same
  to the second decimal but for the tune's chord tones (0.53 to 0.57 at
  the median) and steps (0.65 to 0.60), as they should be: the notes are
  the same, the voices and the bounds moved. On the FFVI set, of the 75
  part picks over the twenty seeds, 24 had sat outside the part's
  register before (11 above the voice's range, 13 below); after, none.
  The `bit` set's measures sit on the FFVI set's line for line. Four
  seeds were put in the dev player's folder for the owner's ear.

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

## Smoke test (2026-10-30, the laptop; 2.0rc2)

The second exit criterion, run the way a listener would meet it: a fresh
data folder (`BITCOMPOSER_DATA_DIR` on an empty directory), the 2.0 window
loaded headless on the Qt venv, and Final Fantasy VI's 82 SPC files
imported through the window's own `import_from`, the stages watched on
`backend.importState`, then a song written through the window's settings.

- **The import.** 82 files read in 61 s (the readers, four workers); the
  lead pass took 11 min 14 s with the whole test suite running beside it
  (3.5 s a song measured alone would be under five minutes); the game's
  vocabulary and the library's counted in under a second. The stage lines
  arrived in order: reading the songs, hearing which voice leads, counting
  the game's vocabulary, counting the library's vocabulary.
- **What it made.** One pack, 67 samples, a format 2 pack file with the
  95 tables; 67 songs in the vocabulary (the 82 files hold 67 distinct
  songs, as the shipped fit did); the lead pass heard all 67 and moved the
  melody label in 9, the count the LIBRARY row now shows. The window
  offered three vocabularies afterwards: the default, the library (67
  songs, ready) and the game (ready).
- **The song.** WRITE set to the game's vocabulary on the game's own
  sounds, GENERATE through the window: "The Wharf of Rust", seed 851766,
  1,050 notes, playing within four seconds of the press, the band's live
  meters reading on nine channels. The copy check over that vocabulary
  (`tools/copycheck.py --vocabulary pack:final_fantasy_vi_spc --seeds
  1-50`): 50 songs, 1,055 four-bar windows, none copies a game phrase (20
  share only a rhythm).
- **Found and fixed.** The window read the list of vocabularies once at
  start, so the fresh game showed "no vocabulary yet" under LIBRARY and
  had no card under WRITE until a restart (2.0rc1's FROM row had the same
  gap); the list is read again on every packs change, and a window test
  covers it. The pack's label carried "(from its SPC files)" after the
  game's name, noise now that the window keeps your games under their own
  heading; it is the game's name alone.

## Exit criteria

- GENERATE on a fresh install writes a song from the shipped FFVI
  vocabulary on a built-in sound set, and the song passes phase 4's
  measures and the copy check.
- A game imported in the player gives a sound set and a game vocabulary,
  and a song from them passes the same. (Imported through the window and
  written from, 2026-10-30: the smoke test above, the copy check clean
  over that vocabulary; phase 4's measures over it are the release's run.)
- Classic's seventy songs are byte for byte rc1's.
- A 1.x pack file still loads as a sound set.

## Open questions

- **The echo is a vocabulary gap** (noted 2026-10-30, the owner's call: fine
  as it is for now, documented). A written song's echo is not drawn from
  the vocabulary: no table counts a game's echo, so the sound set's habit
  decides it, the way Classic's packs do (`render.echo_of` over
  `PACK["habits"]`: `bit` always on, slap or eighth, feedback 0.55 to 0.7;
  the styled sets as their games have it). The readings hold what a table
  would count, each song's echo on or off, its delay, feedback, filter and
  wet, and the writing's way is a counted word drawn once a song beside the
  balance. Not now: a writing change while the FFVI tuning stands.
- Which built-in sound set is the default under the FFVI vocabulary (the
  `ffvi` set is the obvious one; the vocabulary's sample ids bind to a
  game's samples only when that game is imported).
- Whether the panel lets a listener switch a table's rows, and what that
  means for a song's plan.
- Packs by composer and the Genesis path, as phase 5 left them.
