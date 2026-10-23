# Phase 5: packs

Planned in outline (2026-10-20); the detail is written when the phase
begins. See `../IDIOM.md`.

## Goal

The second pack format in the product: the PACKS panel imports a game into
it, exports and adds it, the first format still plays, and the built-in
SNES packs move over if chosen.

## Decided (2026-10-23): how generation is scoped in the product

Three things the user can pick, and nothing finer:

- **Chip**, the default: the built-in generator as it is, needing no
  tables and no imports. It always plays.
- **SNES**, and later **Genesis**: the writing of phase 4 on tables fitted
  over everything the user has imported for that system, all games
  together. A style is earned by importing: with too few songs behind it
  the player says so and does not pretend. The number is measured, not
  guessed: FFVI's tables fitted on 10, 20, 40 and all 67 of its songs,
  twenty songs written from each, the measures compared (the
  one-draw-a-song tables, balance, layout and habits, are expected to
  starve first).
- **A game pack**, imported: the game's own samples and its own tables,
  beside its system's style.

Not offered: a pack from one song (its tables are that song's thirty bars,
a remix) or from one composer across games (whose kits would mix). Nothing
fitted on our own readings database ships: it is the measuring corpus, and
keeping it out of the product keeps anything derived from the games' music
out too. The reference set for the tune's copy check comes from the user's
own imports as well.

What this asks of the work below: the importer keeps the user's readings
across imports (today an import leaves a pack and nothing else), the
style's tables are fitted over all of them (the builder gets a scope: a
game, or every game of a system) and record that scope, and the picker
shows Chip always, each system's style with its song count against the
count it needs, and the game packs under their system.

## Decided (2026-10-23): two switches on the writing

Both are conditions on draws the tables already make. The tables, the
vocabulary and the writer are unchanged; a switch only says which of a
table's own outcomes the song may keep. Off by default. Offered on the
SNES and Genesis styles and on game packs (Chip has no theme vocabulary),
kept in the pack's source so an export carries them, written into each
song's plan under `options`, and named on the Song Check pages.

- **Carry a theme.** The songs of FFVI that bring their first phrase back
  later are 43 % of the 67; the phrase-letters table draws at that rate,
  so most written songs never return to their theme, as most of the
  game's do not. With the switch on the plan draws the tune's phrase
  letters again until a later phrase opens with the theme, at most forty
  times; a game whose table holds no returns stays unthemed and the plan's
  log says so. Nothing is weighted: the letters still come from the game's
  own table, and the draw is conditioned on an outcome that table counted
  (`whole.plan(themed=True)`, `tools/whole.py --themed`).
- **The band comes back.** When the theme returns, the `return_band` table
  says what returns with it (FFVI: the chords 22/46, the bass 27/46, the
  accompaniment 29/43; all three 17 of 46, the tune alone 4). With the
  switch on a return with nothing behind it is drawn again, so the tune
  never comes back alone; which of the chords, the bass and the
  accompaniment come with it stays the game's own mix
  (`band_returns=True`, `--band-returns`). It only acts where a return
  exists, so it is a second switch, not a setting of the first.

The owner's reading of Song Check 5 (seventeen songs whose theme returns
with the band): the themed songs are much more listenable. The switches
are for the listener who wants every song to carry a tune, and the cost is
named in the picker: the game's through-composed forms, its battle and
event cues, are left out while they are on. Measured on Song Check 6
(both switches on, 2026-10-23): see `phase-4-writing.md`, round 13.

## Starts from

The format 2 draft (phase 3), the writing that reads it (phase 4), the
PACKS panel as stage 5 left it (`../TRANSLATOR.md`).

## Work, provisionally

- Import writes the tables beside the voices, from the readings it already
  makes.
- The kit chosen by the drum namer rather than by brightness and length:
  today the imported FFVI pack's snare slot holds the game's open hat and
  its most-played snare is not in the kit. Before it ships, every game's
  kit before and after, the doubtful listed, and a listening set.
- The panel says what a pack says, in words: its habits as the tables
  summarise them.
- Export and add carry the tables; `PACKS.md` describes the second format.
- The built-in SNES packs re-made from their games, if chosen: a release of
  its own, since it changes how they sound.

## Produces

The panel writing and reading format 2; the kit fix; the docs.

## Exit criteria

- A game imported in the player gives a format 2 pack whose songs pass
  phase 4's measures.
- A 1.x pack still loads and plays as it did.
- The kit's slots named by sound on all 39 games, the doubtful listed.

## Open questions

- Packs by composer: the weights counted over a composer's games, which
  the evidence so far says travel with the composer across drivers.
- The Genesis path (VGM logs) into the same tables.
- What the panel shows of a vocabulary, and whether a listener can turn a
  table's rows on and off.
