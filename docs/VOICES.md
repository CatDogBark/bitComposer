# bitComposer's own voices

A written song names its instruments the way its vocabulary does: by the sample ids of the game the vocabulary was
counted from. The token's instrument for a part, its kit, and the ranges, speeds and lengths the tables hold are all
said of those ids. bitComposer's first set of its own sounds (`packs/bit.py`) has names of its own, so on it none of
those words had an answer, and a handful of hand-set tables (ranges, speeds, pools, one envelope, a fixed kit) stood in
for them.

bitComposer's own voices are sounds made by bitComposer, each of which says which game samples it stands for.
Registered in the bit set under those ids, a voice is what the writer finds when a song asks for one of them, so the
counted words answer for it exactly as they do on the game's own samples: a song on the voices is, note for note, the
song the game's samples would play. None of the game's audio is held or shipped.

## Where they live

| path | what |
|---|---|
| `bitcomposer/samples/recipe.py` | a voice from a recipe: the synthesis, `render(recipe, seed)` and `voice(recipe, seed)` |
| `bitcomposer/packs/bit_voices_data.py` | the voices (`VOICES`: each one's recipe, its seed and the samples it stands for) and, for each game, the facts its samples are played by (`GAMES`) |
| `bitcomposer/packs/bit_voices.py` | `use(game)`: the voices synthesised and registered once a process, and the set's table for the writer |
| `tests/test_bit_voices.py`, `tests/bit_voices_lock.json` | the recipe rule, each voice's sound held to its checksum, a song on the voices against a pack file of the same sounds |

`written.OWN_VOICES` turns them on for bitComposer's own set (`bit`, the default). It is off until the voices have
been heard as whole songs; with it off, nothing of them is loaded and every written song is what it was.

## A recipe describes a sound and holds none

A recipe is a short description, measured once from a recording and kept in place of it. Two kinds:

- **tone**, a pitched voice that loops: the levels of its harmonics while it sustains (`steady`) and in its first
  moments (`onset`), in whole decibels; its period and how many periods its loop runs (`period`, `periods`); its level
  at a few moments of its attack (`env`, whole milliseconds and decibels) and how long the attack is (`attack`); and,
  where it has them, how wide its chorus is (`chorus`), how much breath noise it carries (`breath`) and the noise of
  its strike (`strike`).
- **hit**, a sound that plays once: a few partials, each with where its pitch starts and ends and its level at four
  moments (`partials`); noise in half-octave bands at four moments (`noise`); its level curve (`env`). A hit may give
  its own moments in place of the four quarters (`moments`, the bounds in whole milliseconds, spaced as a strike decays:
  0, 5, 15, 35, 75, 150, 300 ...), so a cymbal's first thump and its wash are told apart; how long it waits before it
  strikes (`delay`, whole milliseconds), where a level curve read over a window could not open that sharply; and its
  loudness as an RMS (`rms`) in place of its peak (`peak`).

A recipe holds no wave: no sample value and no phase. Every phase and every noise sample is drawn by `recipe.py` from
the voice's seed, so the same recipe and seed make the same sound on every run, and the sound is bitComposer's own. A
recipe imitates the sound of an instrument; it is not a copy of a recording, and it must never become one.
`tests/test_bit_voices.py` holds every recipe to that: its fields, levels in whole decibels, times in whole
milliseconds, a bounded number of values.

The recipes in the repository were measured from Final Fantasy VI's samples, read from an imported pack. The tool that
measures them reads the game's own recordings and is kept outside the repository for now.

## Standing for a game

`GAMES` holds, for each game the voices stand for, what a recipe does not say: each sample's envelope, release family,
level and percussion flag (a tone's pitch and loop are its recipe's; a one-shot keeps the pitch it was read at), which
samples each part draws from (`pools`, a sample as often as the game's songs give it the part), the kit, and the habits
of the game's scores. These are counted from the game's songs, like a vocabulary.

A voice's `stands_for` lists, by game, the samples it answers for. A second game's samples are added the same way: a
sample whose sound an existing voice already makes joins that voice's `stands_for`; one no voice makes gets a voice of
its own. The set grows as the writer learns more games.

## Changing a voice

A recipe changed on purpose changes that voice's sound, and its checksum in `tests/bit_voices_lock.json` with it:
write the lock again in the same change (`python tests/test_bit_voices.py --write`), and say in the change which voices
moved and why. The lock is never written again to make a failing change pass.
