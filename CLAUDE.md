# CLAUDE.md

bitComposer is procedural 16-bit game music: a pure-Python generator with no runtime dependencies that writes Impulse Tracker `.it` files, and a Qt player (`bitcomposer-player`; PySide6, plus jeepney on Linux) that composes as you listen. Since 2.0 the generator writes from a shipped vocabulary, and the 1.x generator is kept as Classic (`--classic`).

Read CONTRIBUTING.md first: it covers the tests, the analyzer tables, the byte-identical check, where things live, building and releasing the emulator, checking the SPC converter and cutting a release. The notes below add to it.

## Branches, CI and pull requests

- `main` holds released code and nothing else. Work goes into `dev` through pull requests, one topic each, and `dev` merges into `main` for a release (CONTRIBUTING.md, Branches).
- CI as the workflows define it: `ci.yml` (the unit tests on Python 3.10 to 3.14, plus the vocabulary-map check) runs on every pull request into `dev` and into `main`, and on pushes to `main`. The Windows build (`windows.yml`) runs only on pull requests into `main`, on `v*` tags, or by hand.
- Before calling a pull request ready, run the whole suite locally with the player's dependencies (Qt offscreen; a skip is not a pass), plus CONTRIBUTING.md's byte-identical check when generator code changed. For a change that could break Windows, start `windows.yml` by hand on the branch (`gh workflow run windows.yml --ref <branch>`), since pull requests into `dev` don't run it.
- Generator changes are judged by measured metrics (`tools/analyze.py` tables before and after, as CONTRIBUTING.md describes), never by ear alone.
- A generator refactor must leave every song byte-identical: CONTRIBUTING.md's two loops (Classic on every `--sound`, then written songs, over fixed seeds) and a sha256 diff. Without `--classic` the CLI writes a written song and does not read `--sound`.
- Keep the CHANGELOG as you go: every pull request adds its own entry under `## Unreleased`, internal changes (tests, CI, docs, process) included. At release, check that every pull request merged into `dev` since the last tag is covered.
- Through release candidates the CHANGELOG heading stays `## Unreleased`; it becomes `## X.Y.Z` only at the final release, with the rcs as bullets inside that section.
- Run `rm -rf build` before building a wheel locally: a stale git-ignored `build/` makes `pip wheel` ship files already deleted from the source, and it can hide packaging faults (the package list is `[tool.setuptools.packages.find] include = ["bitcomposer*"]`). Check packaging from a clean `git archive` in a fresh venv, not from the working tree.

## Writing in the repository

- Repo files, docs, code comments, commit messages and pull request bodies never name a person for the maintainer: write "by ear", "on the listening page" or "the maintainer", as CONTRIBUTING.md does.
- The copyright holder is Enlightened Solutions LLC: LICENSE line 3 (the MIT text unchanged), the installer's AppPublisher and AppCopyright, and the executables' version resources (`tools/windows/make_version_file.py`, CompanyName and LegalCopyright), which `windows.yml` checks. The public contact is catdogbark@pm.me (README, pyproject authors, the installer's AppContact, the listening page's footer); the author is CatDogBark.
- In SPC work, write "SNES chip" for the S-DSP and "SNES sound CPU" for the SPC700, never a bare "chip", because `chip` is also the generator's NES-style palette (`--sound chip`). S-DSP and SPC700 may be given alongside. This holds in pull request notes and commit messages too.

## What the repository never holds

- Never commit a readings database or note data: the readings are the game's music. SPC files and converted modules stay out (CONTRIBUTING.md), the tune-copy reference set is kept outside (`tools/copycheck.py`), and only fitted statistics in `bitcomposer/vocabularies/` ship.
- bitComposer never ships a third-party program. Archives it cannot read itself (`.rsn`, `.rar`, `.7z`) are unpacked by the 7-Zip or unar already installed on the machine (`translate/archives.py`, whose docstring records the decision).
- Code under LGPL, Artistic or no stated licence (spc2it/OpenSPC/SNEeSe, snes_spc) is studied, never pasted. Code that enters the repo must be under a licence that fits an MIT project (MIT, BSD, zlib), with credit (docs/SPC-IMPORT.md).

## Packs and game sets

- Adding a game set: put the game folders beside the others, add each to `drivers.json` (`{"folder": {"driver": "<file slug>", "game": "...", "composer": optional}}`), run `tools/spc_check.py` `traits`, `sweep` and `doc` (`doc` regenerates the generated blocks in `docs/drivers/` and writes a skeleton file for a new driver), then hand-write the driver file's notes. CONTRIBUTING.md gives the commands.
- When SPC measurement shows a built-in style pack (ffvi, mana, evermore, megamanx) got a habit wrong, add a row with the numbers and where they were measured to `docs/drivers/snes/README.md`, "The style packs against the drivers in play", in the same pull request as the finding. Don't change the packs themselves unless asked.
- A thin pack with tables: `python -m bitcomposer.spc <spc dir> --pack <out dir> --name <name>`, then `python -m bitcomposer.translate.packtables --db READINGS --game GAME --into <out dir>/pack.json` adds the tables and marks the pack format 2 (docs/PACKS.md). `python -m bitcomposer.translate FOLDER --against PACK --songs N` measures songs generated on a pack against the game's own.
- Whole songs from a format-2 pack: `python tools/whole.py --pack PACK.json --seeds 1-20 -o DIR --game "Final Fantasy VI" --db readings.db` (defaults: the loop once, at most 48 bars, a 3 s fade). `--pack` is required; `--themed` and `--band-returns` turn on the two switches, `--stems DIR` writes each part alone, `--tail-bars N` plays the loop's first bars once more after the form, `--min-bars N` draws again any form shorter than N bars.

## The whole-song writer (`bitcomposer/translate/`)

### Before you change it

- Read the record of the earlier rounds that touched the same part or table: `docs/idiom/phase-4-writing.md` ("The integration" and the round records after it) for the writing, the Record section of `docs/idiom/phase-3-tables.md` for the tables, and `docs/idiom/VOCABULARY.md` for the tables the writer draws. The rules and numbers there were measured and heard, and the record says why each one stands.
- A writer is not patched past what its vocabulary says. When written songs miss something the games do, ask whether the vocabulary (the counted tables) has a word for it: if not, count a new unit from the readings and keep it as a table, never a weight, constant or steering rule in the writer; if a word exists and the writer still misses, fix how the tables are drawn from, as a fault. Where the choice between stretching an existing vocabulary and counting a new one is open, put it to the maintainer first; it is not made in code (docs/IDIOM.md, Rules of evidence).

### What a writer change carries

- A writer round is one branch and one pull request into `dev` (or stacked on the round below), merged with a merge commit, never squashed. Its commits: code and tests (with the refit `bitcomposer/vocabularies/default.json.gz` when the tables changed), then a separate commit for the docs, the round's record and the regenerated vocabulary map.
- The docs go in the same pull request: a CHANGELOG entry under `## Unreleased`, `docs/idiom/VOCABULARY.md` entries for new or changed tables, `docs/LIMITS.md` for what stays open, `docs/idiom/rules-to-words.md` where a rule becomes a word, the regenerated `docs/idiom/vocabulary-map.md`, and the round's record as a section in `docs/idiom/phase-4-writing.md`.

### The vocabulary map check

- `docs/idiom/VOCABULARY.md` describes every kept table (what it counts and what it controls) and is updated whenever a table is added or its counting changes. CI runs `python tools/vocab_map.py --check docs/idiom/VOCABULARY.md` and checks that `python tools/vocab_map.py --out /tmp/vocabulary-map.md` reproduces `docs/idiom/vocabulary-map.md` exactly; run both before pushing a change to the tables or the writer's source. A new table needs its entry (a double-time `@2` table is covered by its base's entry when the page names it in code type).
- Each kept table needs a bold `**table**` entry in `docs/idiom/VOCABULARY.md`, or the map check fails.
- In the writer's source (`bitcomposer/translate/whole/`, `writer/`, `harness.py`), never write a kept table's name as a string literal (`"bass"`, `"loops"`): `tools/vocab_map.py` reads it as a draw site, lists the function under that table, and the map check fails. Use the role constants (`R.BASS`) or attributes.
- A table's conditioning name must not collide with a name in `tools/vocab_map.py`'s `SOURCES` (a conditioning once named `kind` was renamed `note` for this).

### Tables and the shipped vocabulary

- A change to how a table is counted (`translate/packtables.py`, `KEPT`) reaches the songs only after the pack's tables are refit (`python -m bitcomposer.translate.packtables --db READINGS --game GAME --into PACK.json`) and the shipped vocabulary is written again from the refit pack. Rendering on an unrefit pack measures the old tables.
- A game read again loses what the lead pass wrote into its readings (which voice carries the tune, round 64): run `python -m bitcomposer.translate.lead GAME SPC_FOLDER --db READINGS` after every re-read and before the tables are counted. `packtables` says as it counts whether the pass has run, the tables' source keeps it (`"lead": {"heard", "relabelled"}`), and the shipped vocabulary's test in `tests/test_written.py` asserts it; rounds 102 to 151 were counted without it.
- A change that refits the counted tables commits `bitcomposer/vocabularies/default.json.gz` on its branch before the pull request; verify with `git log -3 -- bitcomposer/vocabularies/default.json.gz`.
- A fixed-seed test against the shipped vocabulary asserts the table's own values, never a bound that one draw happened to meet. Run the full local suite after the shipped vocabulary is in place.
- The band-levels test in `tests/test_whole.py` iterates every balance token, so a new song-level token field must be filtered out there (as `shapes=`, `quals=`, `form=` and `cycle=` are).

### Random streams

- Every new plan-time draw gets its own stream, `random.Random(f"whole:{seed}:<name>")`, never `_plan_once`'s shared rng: inserting a draw there shifts every later draw (habits, registers, samples, notes). Retired draws stay in place. For a before/after, diff the plans' habits, samples and part logs first and assert they match apart from the new word.
- `plan()` retries `_plan_once` on one shared stream for themed songs, so a draw added inside `_plan_once` shifts the next attempt's key, form and band. Put new once-a-song draws after the retry loop (as `_plan_counter` is) or on an own stream.
- A draw that a later word overrides stays on the plan stream: removing it would shift every draw after it, so never drop one without replaying.
- A per-part draw loop on one stream couples the parts: dropping one part's draw re-deals every later part's. Give each part its own stream.
- Changing the chord chain's state in the middle of its draws shifts later shared-stream draws; post-process after the chain instead.
- The render stream `whole:{seed}:render` is shared by `samples_for` and the pack-habit echo fallback, so reordering or re-pooling one part's sample choice moves the others (the floors and the echo word have their own streams).
- `Table.p()` mixes every coarser level down to the root, so adding one part's units to a shared table shifts other parts' draws.

### Holds

- A writer's hold counts exactly as its token field counts: the same roots, the form's repeats as they will be played, over the whole song.
- A share hold counts the candidate note (would this note put the line over its share) rather than acting only once already over; a lagging hold lets the first note of a never-played class through.
- Anything changed in a chord part before the tune is written re-writes the tune, so holds on chord parts run after the tune and the counter-line are written.
- For a hold inside a part's writer an own stream is not enough: a bar drawn again puts every later bar in another context and re-pitches the tune. Write the bar as before, check it, and repair a failing bar in place with no draw; compliant songs then stay identical.

### Traps in the code

- `compose_written(vocabulary="default")` draws from the vocabulary shipped in the checkout (a pack file lends only sounds), so an old pack file alone is not a "before": monkeypatch the writer or use another checkout. `whole.song_of(plan)` has no written notes (use the result's `["written"]`). A `Table`'s back-off drops the last conditioning first, so order conditionings by importance.
- The packages re-export their sections' names: `bitcomposer.translate.writer`'s `__init__` rebinds `upper` (and `whole`'s rebinds `plan`) to the functions, so patch a module through `importlib.import_module("bitcomposer.translate.writer.upper")`.
- A registered pack names its samples with the pack's prefix (`<pack>_<id>`) while the tables and the pack file key the bare sample id, so a lookup by the prefixed name silently never matches (once it made every pool sample choice random). Resolve against the raw ids: `translate/whole/render.py`'s `raw` lambda strips `<pack>_`, and `best_sample` takes it.
- The readings' `Song` dataclass is unhashable (it cannot be a dict key), and `readings.UPPER` cannot be read when `arrangement.py` is imported (a circular import), so `arrangement.py` uses a literal tuple.
- In the plan records, a layered part's figure strings are `"line || second"` joined; split on `" || "` to read them.
