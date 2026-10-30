# Rules to words: what the whole-song writer still decides by rule, hand number or fallback

The vocabulary rule ([IDIOM.md](../IDIOM.md), "Rules of evidence"): a writer is
not patched past what its vocabulary says. When the written songs miss something
the games do, the answer is a new unit counted from the readings and kept as a
table, never a weight, a constant or a rule in the writer that steers a draw
toward the effect. A "rule" here is anything on the whole-song path that decides
what is heard without a counted table behind it: a hand-set number, a fixed
order, a filter, or a fallback that fires often enough to shape the songs.

This page keeps the rules audit of 2026-10-24 (`~/diags/bitcomposer/idiom/phase4/
rules-audit-report.md`) so the list can be returned to. The audit was reading
only, on the tree at commit 6a89f99 (after round 29); nothing was changed by
it. Its scope: `translate/whole.py`, `writer.py`, the writer-facing parts of
`rhythm.py` and `phrases.py`, and `pack.py`. The FFVI numbers come from the
readings (`phase3/readings.db`, 67 songs) and the pack
(`phase3/pack2/ffvi/pack.json`); the written songs' numbers from seeds 1-20
composed as the Song Checks are (themed, band returns, 12 to 48 bars), not
rendered. The scripts, each running in under three seconds:
`phase4/audit_fallbacks.py` (the counters over seeds 1-20), `audit_ffvi.py` and
`audit_ffvi2.py` (FFVI's measures), `audit_written.py` (the same measures on the
written songs). Aggregates only.

Line references are as of 6a89f99 and drift as the files change; the names
hold longer than the numbers. Each item carries a status: **standing**, or
**replaced in round N** where a later round built the word (see the round's
record in [phase-4-writing.md](phase-4-writing.md)). Since the audit, round 30
replaced the counter's sample rule with `counter_pairs` and round 31 the
counter's level (the draw that reached `level_of`'s cap) with
`counter_shares`; both are marked below. The rest are to be replaced in the
owner's order.

The audit's short answer. The writing of notes is now almost all words: over
twenty seeds the figure ladder took its first rung in every accompaniment,
harmony and drum bar and in 335 of 346 bass bars; no `DEFAULTS` fallback fired;
the melody's copy check never ran out; the habit draws never fell through. What
is still rule lives in four places: the rendering (the echo, the pans, the kit,
the absolute level), the band's lock (the shares an upper part and the drums
strike of the band's shared hits), the tune's two filters (no semitone against
the band, no off-scale note on a beat) and its note lengths, and the spans the
voices beside a line are folded into. Two fallbacks fire often enough to be
rules: the sample fit leaves the part's pool in 17 of 86 choices, and the game's
own sample pair is refused by the reach check in 8 of 13 tests (the reach check
now runs against the planned register before the writing, round 34). A few constants
are dead in the whole-song path (listed at the end).

## The top ten rules to replace

Ranked by how much of what is heard each shapes on seeds 1-20. "Size" is the
round that would replace it.

| # | rule | where (6a89f99) | what it shapes | the word | the FFVI measure | size | status |
|---|---|---|---|---|---|---|---|
| 1 | The echo: which parts send (`SENDS`), and the delay, wetness and feedback re-expanded from the generator's names | `whole.py:64`, `echo_of` 1227-1245; `pack.habits` 276-288 | every tonal note of the 18 songs in 20 with an echo (the bass and drums never send) | `echo_sends` (a part sends or not, one unit a part a song); `echo` (delay in 16 ms steps, echo volume over main, feedback) as classes counted from the SPCs | not in the readings; the SPCs carry each voice's EON flag and the echo registers (`snap.echo`); round 25 saw the tune echoed on 94 % of notes, the other parts uncounted; the pack's own counts: delay "slap" 49 / "row" 10 of 59, wet "normal" 67 of 72, feedback quartiles 0.55-0.78 | medium | standing |
| 2 | The pans | `whole.py:60-61`, `score_of` 1307 | every note of every song | `pans` (a voice's pan to 0.05, by the part and the voice's rank) | the store keeps a pan a note: FFVI's voices sit at 0.42 / 0.50 / 0.58 (quartiles of 508 voices), only 181 within 0.05 of centre; by part the medians are bass 0.51, harmony 0.58, accompaniment 0.49, counter 0.51, melody 0.50, drums 0.51, and a part's own voices sit 0.16 to 0.19 apart (accompaniment, counter, harmony), the bass's 0.08, the drums' 0.11; the writer's are fixed (tune centre, counter 0.6, harmony 0.35/0.65/0.5, accompaniment 0.6/0.4, drums 0.5/0.58) | small | standing |
| 3 | The kit: one kit a game, two voices by a fixed split, a letter's sample by a fixed order, a hit cut at one beat, one pitch a drum | `whole.py:52-56` (`DRUM_VOICES`, `KIT_FOR`, `DRUM_LENGTH`), `write` 826-842, `score_of` 1333 (`KIT_NOTE`); `pack.kit_by_name` 204-226, `build` 310 | every drum hit in the 16 songs with drums; 236 of 3373 drawn hits dropped because two pieces fell on one voice at once (7 %); 257 of 3137 hits cut by the one-beat cap (8 %) | `kit` (the song's samples by piece, and which pieces share a voice: one unit a song); `drum_lengths` (a hit's length by piece); the drum's pitch a song | 32 distinct kits in 47 songs with drums; a kick in 17 songs only (2 samples), a snare in 26 (6 samples), a hat in 17 (4), a cymbal in 23 (3), an "other" in 11 (11 samples: the pack's one rim slot plays the snare sample for all of them); 2 drum voices a song (median), 1.3 pieces a voice, the kick and snare on one voice in 10 of 47; hit lengths hat 0.21, snare 0.20, kick 0.45, cymbal 1.22 beats (medians), 663 of 14854 over a beat; the drum's pitches are in `pack.gather` (`g.pitches`), not the readings | large | standing |
| 4 | The band's lock: the share of the band's shared hits an upper part must strike (`UPPER_LOCK`: harmony 0, accompaniment and arp 2/3), the drums' (`LOCK_DRUMS` 2/3, dead: the drums are written first), the lock positions counted over the planned band | `writer.py:395`, `1477`; `whole.locks_of` 668-692 | the accompaniment's bars in 19 songs (a lock applied in 29 of 257 drawn bars), the harmony's in 7 (never) | `band_locks` (the share of the band's shared hits a part strikes, in tenths, by the part: `bass_locks`' shape for the other parts), the positions from the parts written before it | FFVI medians: accompaniment 0.89 (n 58), harmony 0.67 (15), arp 0.73 (4), drums 0.81 (46), bass 0.86 (63); the written songs: accompaniment 0.65, harmony 0.65, drums 0.52, bass 0.61 (the bass's own word is round 28's) | medium | standing |
| 5 | The tune's filters: no move onto a semitone against a sounding upper tone (`CLASH`), no off-scale note on a beat (`STRONG_SCALE`) | `writer.py:401`, `810`, `draw_move` 964-967 | every move of every tune (1187 draws over the seeds; the counter's intervals are clear of the tune only) | `clashes` (the share of tune onsets a semitone from a sounding chord-part tone, once a song, held by the controllers as `chord_tones` is); `strong_scale` (the share of strong-beat notes on the key's scale), or both folded into `moves`' conditioning | FFVI tune onsets a semitone from a sounding upper tone: 607 of 6834 (9 %); the counter 862 of 7741 (11 %); the counter against the tune 341 of 8428 (4 %). Strong-beat tune notes off the key's scale: 677 of 4172 (16 %), the counter 1106 of 5304 (21 %); part of that is the key reader's (a modal tune read as its parent key, IDIOM.md) | medium | standing |
| 6 | The tune's note lengths: a detached note sounds 0.5 of its gap, a held one 0.95, and a bar's last note is cut at the bar line | `writer.py:643-644`, `melody` 1452-1458, `counter` 798-804 | every tune note and every counter note | `gap_sounds` for the melody (the share by the value's class, as the chord parts and bass have since round 26), the last note's gap to the next bar's first onset | FFVI detached tune notes sound 0.40 of their gap (quartiles 0.27 / 0.40 / 0.42), held ones 0.90 (0.83 / 0.90 / 0.95); 284 of 1654 bar-final tune notes sound past the bar line (17 %), the written ones 0 of 473 | small | standing |
| 7 | The span a voice beside a line, and the counter, are folded into: the line's register widened by `LAYER_OFFSET` (24) each way; the second bass voice `BESIDE_SPAN` (24) above the line's floor | `whole.py:934`, `966`; `writer.py:649`, `1821`; `rhythm.py:2244` | the second voices' notes (2047 accompaniment, 767 bass) and the counter's (1916) over the seeds | the voice's register as a word of its own, or the layer offset conditioned on the line's register (round 24's open item) | FFVI counter notes below the tune's ambitus 18 %, above 12 %, more than 12 outside 11 %, more than 24 outside 0.4 %; its lowest note sits 2 under the tune's lowest at the median; accompaniment second voices outside the line's 10-90 register 51 %, more than 12 outside 12 %, more than 24 outside 3.5 %; the second bass's highest note 12 above the line's floor (median, quartiles 9 / 12 / 31). Written: counter outside the tune's register 29 %, more than 12 outside 3 %; accompaniment 61 % and 10 %; the second bass's top 23 above the floor | medium | replaced in round 34: the sample is chosen before the writing and the range the `ranges` word drew for it is the voice's register (`whole.bound_of`); the spans and round 32a's fold are gone |
| 8 | The meter: every song in 4, on a twelfth grid | `whole.py:47-48` | every song (FFVI's 3/4 songs are never written, and their bars never counted) | `meters` (a song's meter, once a song; the figure tables already carry the meter value) | 63 of 67 FFVI songs in 4, 4 in 3 | large | standing |
| 9 | The doubling voice: the line again a fixed number of scale steps off (`diatonic`), never bent to the chord | `whole.py:387-390`, `919`, `983` | the doubling voices (the layers word's "doubling" draws) | the doubling voice's note against the chord (the voice words' domain, round 23's open item) | round 23: the doubling voice's chord tones 0.31 against FFVI's 0.82 (a biased measure, both sides noted there) | medium | standing |
| 10 | The bass's ceiling and its passing tone: the register word's top ignored (the floor plus `REACH` 16); a bar-final "+" passes on in the line's direction | `writer.py:121`, `bass` 1780, `place` 1839; `realize` 1879-1886 | every bass bar of 19 songs; 57 of 492 written bass bars end in "+" | the word's own top (a fault, below); `passing_targets` (where a bar-final passing tone lands against the next bar's first note: the interval, or the mark against the next chord) | the registers word gives the bass 8 semitones (median high - low; mean 12); FFVI's line reaches 9 above its floor at the 90th percentile and 12 at its top (the written 12 and 14). Bar-final "+": 297 of 1697 FFVI bass bars (17.5 %; written 11.6 %); the next bar's first note is within a step of it in 178 of 282, at the median the same pitch (the "+" is often the next chord's tone anticipated), a step on in the line's direction in 75 | small | the ceiling replaced in round 34 (the bass writes within its sample's drawn range, `writer.bass(ceiling=)`); the passing tone standing |

Next in line, not in the ten (all standing): the drum group caps
(`DENSITY_CAPS`; FFVI's sparse hat exceeds 2 hits in 19 % of its bars), the
loop's bar (`loop_bar_of` agrees with FFVI in 40 of 61 songs), the sample pools
by motion (an arpeggiated accompaniment draws from the arp pool; 59 % of FFVI's
accompaniment notes are on samples its arps never play), and the absolute level
(`TOP_LEVEL` 0.85 against FFVI's loudest part at 0.28 of full).

## The inventory

Classes: **R** a rule a word should replace; **F** a fallback; **M** drawing
mechanics; **C** a rendering constant; **D** a word's own definition. "Fires"
counts are over seeds 1-20 unless said otherwise. Line numbers as of 6a89f99.
An item is standing unless it says otherwise.

### whole.py

- `METER = 4`, `DIVISION = 12` (47-48) — **R** (the ten's #8) and **M**: the grid holds sixteenths and triplets; chosen by hand to fit every figure.
- `VOICES = 8` (49) — the SNES chip's; `LETTERS`, `MAX_PARTS = 12` (50-51) — **D**: the form-size count also stops at 12 (`rhythm.form_size_units`).
- `DRUM_VOICES` (52), `KIT_PIECES`, `KIT_FOR` (53-55) — **R** (#3): the kick, snare and toms on one voice, the rest on the other, a letter's sample the first its kit has. Two pieces at one position on one voice keep the first by the group's order (`write` 838): 236 drops in 20 songs. The 'o' letter plays the rim slot, which `pack.other_slot` fills with the snare sample.
- `DRUM_LENGTH = 1.0` (56) — **C**/**R** (#3): 8 % of written hits cut by it; FFVI's cymbals ring 1.2 beats at the median, 3 at the upper quartile.
- `WANTS` (57), `allot` (315-347) — **F**: the voices a part takes without balance counts; never fires with the FFVI pack (the balance word carries counts; the trim past eight voices fired in 0 songs).
- `LEVELS` (58) — **F**: never fires (the levels word). `TOP_LEVEL = 0.85` (59) — **C**: hand-set; FFVI's loudest part sits at 0.28 of full by the readings' levels, so the absolute level could be counted, though headroom is the product's choice.
- `PANS` (60-61) — **R** (#2).
- `POOLS`, `BASS_POOLS` (62-63), `samples_for` 1180-1185 — **R**: a part's pool by its part, the bass's by its weight, the accompaniment's by its motion. The pack's three bass pools are identical (`pack.POOLS` maps the bass to all three), so the weight choice is a no-op. The arpeggiated accompaniment takes the arp pool (built from FFVI's four arp parts, 6 samples): FFVI's accompaniments play 59 % of their notes on samples its arps never play. The harmony shares the accompaniment's pool: harmless (1 % of FFVI's harmony notes are on samples the accompaniment never plays). Word: the sample by part and motion, or simply the part's own pool. Small.
- `SENDS` (64) — **R** (#1).
- `DEFAULTS` (65-71), `_draw` (148-161) — **F**: a value where the pack has no table; no "no X table" line in any plan log over the seeds (the FFVI pack carries 80 tables).
- `FORM_TRIES = 20` (72), `plan_form` 169-219 — **M**: the form drawn again outside 12 to 48 bars (the listening round's bounds, not FFVI's: its jingles are shorter); fired in 5 of 20 songs (2 to 4 draws). The last try cuts the form.
- `SECOND_MEMO = False`, `SECOND_ANY_TONE = True` (73-75) — **M** flags; the tone-up-the-voicing path they govern runs only without the voice words (never now).
- `PLAN_FLOOR = 1`, `PLAN_SONGS = 2` (76-79) — **M**: chosen on a measure (a register draw had reached the root in a third of draws).
- `TOGETHER` (81, `harness.py:75` 0.67), `NEAR` (82, 0.06) — **M**/**D**: the shared-hit threshold is a hand number from the substitution harness.
- `MASK_FLOOR = 4` (144) — **M**: set on a fault (a mask read around a longer line).
- `loop_bar_of` (222-226) — **R**: the loop returns after the intro where the first part never comes back, else to bar 0. FFVI (61 songs with a loop and a form): bar 0 in 22, the second part's start in 33, another part's start in 6; the rule agrees in 40. Word: the loop's part (the readings keep `loop_bar`). Small.
- `chord_of`, `plan_chords` (229-277) — **F**: an unreadable numeral or no chord takes the previous chord or the home chord (0 times over the seeds); the loop's chord is drawn from `loops` only when the loop bar is not 0 (an intro), so a song looping to its start never uses the loops word. **R**: a chord a bar; the `changes` word is counted and not drawn (VOCABULARY), and the readings' chord spans here are one a bar (0 of 2029 bars hold two).
- `plan_texture` (280-312) — **M**: twenty draws until a texture leaves some part playing, else the whole band; `form` place classes only/first/last/middle — **D**.
- `habit_near` (353-363) — **M**: a second line's habit drawn until its density tier matches the layer word's, the last draw kept after twenty; 4 calls, never fell through.
- `layer_of` (375-384) — **F**: "stack" where a part has no layer word (never: `layers` exists).
- `diatonic` (387-390) — **R** (#9).
- `THEME_TRIES = 40`, `PLAN_TRIES = 10` (393-394), `plan` (397-418) — **M**, and the switches themselves a choice: `themed` forces a theme return into every song and `band_returns` a band behind it, where FFVI carries a tune back in 43 % of its songs and the return-band word has a "none" outcome. The plan was drawn again in 1 song of 20. A word for "themed or not" exists in effect (the letters table's own rate); the switch overrides it by the owner's design.
- `_plan_once` (421-608) — the registers from the balance word's layout else the registers word; `weights.get(role, "half")` (473) **F**; the counter's `echo`, `steps`, `repeats`, `chord_tones`, `repeat_rate` draws (480-486) drawn and unused since round 29; `"apart +0 like"` (490) **F** never; `feel` "duple" (494) **F** never. The counter's level draw here (`counter_levels`, a ratio to the tune drawn apart from the tune's own `levels` draw) — **replaced in round 31**: `counter_shares`, the counter's share of the song's loudest part drawn under the band of the tune's share, in `_plan_counter`; `counter_levels` retired.
- `song_of` (630-649) — chords as spans at fit 1.0.
- `locks_of` (668-692) — **M**/**R** (#4): the planned band's voice count makes the threshold; the accompaniment got a lock in 29 of 257 drawn bars, the harmony and drums in none, the bass in 72 of 346 (its own word's accents).
- `double_theme`, `carry_theme` (702-774) — **M**: the copied cell folded into the part's register by octaves; `(24, 100)` a fallback register; 23 bars doubled and 1 phrase carried over the seeds (the words' rates).
- `copy_repeats` (777-806) — a repeated part of the form note for note (20 parts).
- `write` (809-1011) — the order drums, bass, upper parts, tune, counter is a choice: the tune clears the band's tones, the band never follows the tune except by `theme_doubling`. `harness.UPPER_SOUNDS` (894, 898; `harness.py:649`) pins the harmony's sounded share at 1.0 over the `sounds` and `gap_sounds` words — **R** in form, nothing in effect: FFVI's harmony sounds 0.99 of its gap (431 of 478 notes at 1.0). The counter's second voice apart is not written (987-988): fired in 4 songs. The second counter-line of its own (989-1002) runs only when the counter is not written beside the tune (never now).
- `REACH = 7`, `SPEED_WEIGHT = 3` (1016-1020) — **M**, hand.
- `sample_speed`, `sample_floor` (1023-1041) — **M**: "faster" stands for 48 a second, "long" for 400 ms (bin tops as values).
- `best_sample` (1044-1094) — **M**: the fit is overlap minus twice the top's shortfall minus the bottom's (hand weights); the pool is left for the pack's other tonal samples in 17 of 86 choices (20 %: a fallback firing as a rule, mostly the counter's and second voices' registers the pool never reaches); the random draw with nothing known fired 0 times. The counter's "other" sample no longer comes through it except as the fallback (round 30, below); the second voices' choices still do.
- `sample_fits` — was dead, removed in 1.2.0rc4 with `sample_range`, `form_spans_of` and `rhythm.density_bin`.
- `reaches` (1136-1142), `pair_for` (1145-1160) — **F** firing often: the game's pair is drawn 9 times (accompaniment 5, bass 3, counter 1) and `reaches` refuses in 8 of 13 checks, so at most 2 pairs of 9 apply; a "same" pair 5 of 18 draws. The pair word is drawn without the registers it was played in; see the faults.
- `samples_for` (1163-1220) — the counter's sample rules (1190-1197): an "other" counter took the pool's best but the tune's by the written register and speed — **replaced in round 30**: `counter_pairs` (the counter's sample under the tune's sample id, 35 units of 35 FFVI songs), drawn by `whole.counter_pair_for` as the table's conditional over the samples the pack holds, not the tune's own, in reach of the written register; the pool rule stays only where no counted sample fits (5 of the 10 "other" counters over seeds 1-20 and 28, each for a written register 24 to 32 semitones wide; round 30's open item). `or names` (1194) **F** never (the counter pool has 9).
- `echo_of` (1227-1245) — **R** (#1): the pack's chance is counted; the delay is the generator's row name re-quantized to 16 ms steps, the wetness a name times `ECHO_WET` 0.4, the feedback uniform between the pack's quartiles. Over the seeds 18 songs wet (slap 17, row 1), 2 dry.
- `score_of` (1258-1351) — `loops`, `fade`, `tail_bars` are the listening page's; `level_of` (1296-1303) floor 0.05 and cap 1.0 **C**: the cap fired once (an accompaniment second voice; FFVI's `layer_levels` run over 1.18 in 25 of 96 units, so a loud line's second voice can clip); the counter's path to the cap (a `counter_levels` ratio multiplied past the loudest part, Whole 28 at 1.05 of the loudest) — **replaced in round 31**: `counter_shares` is in `levels`' own unit, so the counter never reaches the cap; the cap stands for a layered second voice. The envelope by sample **(word)**; `KIT_NOTE` 48 with the drum's rate set at its modal pitch (`pack.build` 310) **R** (#3); `ECHO_FILTER` (`score.py:37`) **C**: the SPC carries FFVI's own FIR taps.
- `SPAN = 32` (1406) — the measures'.

### writer.py

- `SHAPE`, `REST`, `DISCOUNT` (117-119) — tables.
- `LOW`, `SLACK`, `TIGHT`, `DOWNBEAT`, `ANCHORS`, `ROOTS`, `MARGIN`, `PEDAL`, `PEDAL_SHARE`, `RARE`, `REUSE`, `PERIODS`, `EARLIER` (120-133) — `Manner` and `_figures`, the substitution writer's; not on the whole-song path (`FreeManner`, `_free_figures`).
- `REACH = 16` (121) — **R** (#10): the bass's top above its floor, and the upper stack's bottom placed within it (`place` 1839, `stack` 376).
- `TRIES = 40` (134), `SOUNDS` (135), `sounded` (1915-1918) — **M**; the clamp is a fallback for a bass with no share given (never).
- `FREE_STRIKES`, `FREE_HITS` (301-305) — no envelope on a free part (chosen on a measure: an envelope by the habit had cut a dense part to three bars in 32).
- `ANY_TONE`, `VOICE_KINDS`, `VOICE_TRIES = 4` (336-338) — **M**.
- `DENSITY_CAPS` (339), `group_caps` (342-352) — **R** derived from the `DENSITIES` bins: a group's hits a bar capped at its tier's top (2, 6, 16). FFVI bars over the cap under the habit: sparse kick-snare-tom 13 of 164 (8 %), sparse hat 18 of 95 (19 %), sparse cymbals 27 of 590 (5 %), sparse other 27 of 267 (10 %), medium kick-snare-tom 42 of 244 (17 %). Word: the group's bar drawn under its own habit (the group tables have it; the kit is drawn as one). Small.
- `UPPER_LOW`, `UPPER_HIGH` (364-365) — **D**, the harness's registers.
- `stack` (369-379) — **R**: a close stack, the bottom nearest the note before; the `widths` word is counted and not drawn (VOCABULARY: "the stack's spread is set by the register for now"). Small-medium.
- `UPPER_LOCK` (395) — **R** (#4).
- `MOTION_STEP` (398), `upper` 566, 621, 634 — the motion word's realization: the voices walk up the stack one step a strike, always upward; a lone arp cycles its tones from the bottom (555). FFVI accompaniments move mostly up in 11 of 59 songs, mostly down in 6, mixed in the rest. Word: the order an arpeggiated line takes its tones in. Small.
- `CHORD_MARKS` (399-400), `voiced` (408-412) — **R**: the voicing table's "+" dropped as the chord reader's noise (FFVI's own accompaniment plays 4 % other tones); `["R", "5"]` after `TRIES` (543) **F**, uncounted.
- `CLASH` (401), `unclashed` (425-430) — **R** (#5); the upper parts' own tones are moved off a semitone from the tune too (630).
- `RICH_TONES` (404) — the richness word's realization as a minimum tone count; **D**-like, hand.
- `PEDAL_VOICE = 2` (405) — **R**: a voice with a register 2 semitones or narrower holds one note; fires only where the registers word's low equals its high.
- `upper` (433-636) — `last_chord` where a bar has no chord (511) **F**; `own_tone` drawn a span (525) **M**; spare voices doubled an octave up or dropped from the middle (561-565) a leftover: the line is always one voice now; `taken` guard (572, 610-616) **R**: a pitch another voice of the part holds is drawn again, the onset skipped after four. FFVI's voice beside the line sits on the line's own pitch at 5 % of shared onsets (accompaniment apart), 21 % (arp apart), 0 % (harmony).
- `PHRASE = 4` (641) — **D**. `CONTOUR_STEP` (642) — **F** never (`contour_sizes`). `DETACHED`, `HELD` (643-644) — **R** (#6). `COPY_TRIES = 12` (645) — **M**, never exhausted (the reference set is on this machine). `ARC_ABOVE`, `ARC_BELOW` (646-647) — the summit and arc classes' representative semitones ("6+" is 7, "10+" is 11), hand. `ARC_ROOM = 7` (648) — hand. `BESIDE_SPAN = 24` (649) — **R** (#7).
- `share_at` (652-656) — `0.8` where a gap class is missing **F**.
- `mask_figure` (659-670) — **R**: the second bass voice's own onsets take the root mark, re-pitched by its move; what mark FFVI's slap plays at its own onsets is countable from the bass figures. Small.
- `first_onset` (673-680), `beside_pitch` (683-719) — words.
- `counter` (722-807) — the unison redraw on the tune's sample (773-776) **R**: FFVI's counter on the tune's sample sits at the unison in 17 of 1836 shared onsets (1 %), on another sample 182 of 1845 (10 %), so the guard is near right in effect and still a rule; it skipped onsets in no song over the seeds. The first note the tune leaves it alone with is the chord's root nearest its register's centre (785-788) **R**: fired in 7 of 14 songs, one note each; FFVI's counter's first lone note is countable (its degree, or its interval to the tune's last note). The gap of a note before a rest bar runs to the bar's end (798) **M**.
- `MOVED` (808) — **F** never (`phrase_shifts`). `DEGREE_PCS` (809) — the ending degree's pitch classes ("3" either third) **D**. `STRONG_SCALE` (810) — **R** (#5).
- `contour_targets` (813-823) — the contour's thirds at 0, half, far: a shape's realization, hand.
- `CHORD_ON_BEAT` (836), `REPEAT_RATE` (837) — **F** never (`chord_tones`, `repeat_rates`). `CONTOUR_RANGE = 5` (839) — hand: the line is steered back once 5 semitones off its contour's third. `LEAP`, `MOVES` (840-841) — **D**. `ECHO_SHARES` (842) — **F** never (`melody_recall`). `CONTINUE = 0.8` (843) — hand: after an echoed bar, an "earlier" draw goes on with the source's next bar at 0.8. FFVI by a near measure: of 633 echoed tune bars with a bar after, the next bar echoes too in 469 (74 %) and of those goes on with the source's next bar in 384 (82 %). A word (the recall's continuation) is cheap and would settle it. Small.
- `Urn` (893-923) — **M**: the first bar's "same" share goes to "new", an empty pool's "earlier" to "new".
- `draw_move` (936-1000) — the filters (register, `CLASH`, `STRONG_SCALE`, the contour aim) **R**/**M**; the repeated note's weight `r * rest / (1 - r)` and the chord weighting gated by the running share: controllers holding counted rates **M**. No move fit in 5 of 1187 draws (a 0 returned).
- `melody` (1008-1459) — the tune's first note at the register's centre (1104) **R**: FFVI's first tune note is the tonic in 18 of 66 songs, the fifth in 16, the seventh in 8, off the scale in 8, the fourth and third 5 each, the sixth 4, the second 2; `phrases.KEY_NAMES` reads it, no table keeps it. Small. The arc's ceilings (1082-1096) words with `ARC_ROOM`. `again` (1249-1290): the cell moved within 4 semitones to land the most beats on the chord (1284) hand; the endings onto the nearest option (1331-1336, 1426-1432) **M**; AGAIN takes the last non-theme phrase (1342-1344) **R**, the letters word says "an earlier head" not which. The bar-final note cut at the bar line (1452) **R** (#6).
- `habit_rel` (1462-1469) — a fault: the `relations` table's habit conditioning (`phrases.REPEATS`, a song's share of repeated or moved phrases) is taken as the table's commonest value, never drawn once a song as `step_habits` is.
- `LOCK_DRUMS = 2/3` (1477) — **R** (#4), dead on this path: the drums are written first and `_free_figures` saw a lock in 0 of 229 drum bars.
- `locked` (1480-1487) — **M**.
- `FORM_PERIOD = 4`, `form_spans` (1490-1514) — dead: `_free_figures` discards the span's period (1551); the `periods` word carries the riff.
- `THIN`, `BREAKDOWN`, `thinned` (1521-1530) — dead on this path: `whole.write` never passes `energy` (the band's energy is not read, by the module's own note).
- `_free_figures` (1533-1597) — the ladder **M**: rung 0 (manner, envelope and lock) in every accompaniment (257), harmony (75) and drum (229) bar drawn; the bass rung 1, the lock dropped, in 11 of 72 locked bars (335 of 346 at rung 0); the raw-draw fallback (1589) never. Bars copied rather than drawn: the form's repeats (accompaniment 97, bass 93, drums 86, harmony 24), the period's holds (106, 53, 74, 69), the theme band (65, 62).
- `drums` (1683-1751) — `"medium mixed"` (1707) **F** never; the main group's fill where every group rested (1723-1743) **M**, never left a planned bar resting.
- `bass` (1759-1827) — `"medium roots no-octaves"` (1777) **F** never; `low` from the register word's floor alone (1780) **R** (#10); the second voice's span (1821) **R** (#7).
- `place` (1830-1840) — **M**: the octave nearest the note before within `REACH`, the first note lowest, "r" an octave up. `passing` (1843-1855), `realize` 1879-1886 — **R** (#10): a bar-final "+" with nothing after it passes on two semitones in the line's direction.
- `tone` (1896-1912) — the marks' pitch classes by the chord's shape (a "3" the shape's third, else major; "5" 7 / 6 / 8; "7" 10 / 11; "s" 5 / 2; "+" the second if in the scale else the seventh) **D**/**R**, small.

### rhythm.py (writer-facing)

- `NEAR = 0.06` (85) — **D**. `DENSE = 6` (88) — the hat's threshold, the namer's. `SHORT = 0.75` (91) — **D**: the `values` word's detached cut, hand ("the readings: under 0.75").
- `BANDS` (101) — **D**: tempo tertiles of 1562 songs (on the data).
- `HABITS`, `REPEATS`, `DENSITIES`, `TONES`, `OCTAVES` (399-403) — **D**: the habit words' bins, thirds and 2 / 6 onsets a bar, 0.8 of marks, 0.2 octaves: hand.
- `WEIGHTS` (440) — **D**: 0.2 / 0.5 of the pitched strikes, hand.
- `WIDTHS` (523), `RICHNESS` (577), `MOTIONS` (585), `ECHOES` (824) — **D**: hand bins (7 / 14 semitones; 0.4 / 0.6 of four tones; thirds).
- `REGISTER_BIN = 4`, `TEMPO_BIN = 5` (893-894), `SOUND_BIN = 0.1` (954), `CHORD_TONE_BIN = 0.1` (2139) — **D**: grains, hand. `register_units` (910-931): the melody's register is its whole ambitus, the others' 10th to 90th percentiles **D**.
- `GAP_CLASSES` (965) — **D**: 1 / 2 / 4 beats, hand (chosen on the bass's shares, round 26).
- `DENSITY_BINS`, `density_bin` (1174-1179) — unreferenced: the second-figure units carry the exact onset count.
- `COUNTER_KINDS`, `main_sample` (1247-1273) — **D**: "same" by the sample most of the line's notes play.
- `counter_level_units` cap 1.5 (1323), `layer_level_units` cap 1.5 (2399) — **D**, hand: FFVI's second voices run over 1.18 of the line in 25 of 96 units; the cap hides how far. The counter's builder is gone since round 31 (`counter_share_units` in its place, the share of the loudest in tenths under `TUNE_SHARES`' three bands, the bands themselves a **D** chosen on FFVI's terciles); the layer's cap stands, now as `rhythm.LAYER_LEVEL_CAP`, and since round 33 the balance token's sixth field (every voice beyond a line's level over the line's, `voice_level_shares`) is counted under the same cap: 22 of FFVI's 148 such voices run past it (Relm's accompaniment to 3.4).
- `LENGTH_BINS`, `SPEED_BINS` (1332-1333) — **D**, hand classes.
- `TRIPLE_SHARE = 0.25` (1518) — **D**, hand.
- `PERIODS`, `PERIOD_HELD = 0.6`, `PART_LENGTHS` (1551-1553) — **D**, hand.
- `LONG = 32`, `FORM_SIZES`, `PART_LENGTHS` (1861-1863) — **D**.
- `PRESENCE`, `SUSTAIN = 1.0`, `ECHO = 0.02` (1959-1961) — **D** (the texture readers').
- `RETURN_SAME = 0.5` (1104), `ROLL = 6`, `ROLL_PIECE = 4` (2165-2166) — **D**, hand.
- `LAYER_DENSITY`, `LAYER_OFFSET = 24` (2243-2244) — **D** and **R** (#7): the offset is counted within 24 and the same 24 widens the span the voice is written in. `VOICE_STEPS = 14` (2247) — **D**.
- `kit_accents` (2333-2345) — **D**: two or more pieces at one grid position.

### phrases.py (writer-facing)

- `MIN_NOTES = 3`, `SAME = 0.75`, `LEVEL = 2.0` (89-91) — **D**: a repeat at three quarters of the notes, a contour's thirds 2 semitones apart; hand.
- `REPEATS` (494) — **D**: the relations' habit in thirds, hand (and never drawn by the writer: `habit_rel`).
- `SIZE_BIN`, `CONTOUR_CAP`, `SHIFT_BIN`, `SHIFT_CAP`, `RATE_BIN` (550-614) — **D**, grains and caps, hand.
- `LEAP = 12`, `STEPS` (0.5 / 0.75), `NOTE_REPEATS` (0.05 / 0.2, "the games' quartiles"), `STRONG` (655-658) — **D**: the step habit's bins hand, the repeat habit's on the data.
- `PLACES`, `BELOW`, `ABOVE`, `place_of` (1063-1076) — **D**: the arc's classes and the 0.4 / 0.6 cut for early, middle and late; hand.

### pack.py

- `VOICES = 6`, `SHARE = 0.03`, `REPEATS = 4` (44-46), `pools` (123-147) — **M**/**R**: a pool is the part's six most-played samples over the game, the top repeated four times (the pool's share decides ties in `best_sample`); every tonal pool of the FFVI pack is headed by the same sample (f89f5aedfd, four copies in lead, harmony, counter and arp). The weighting is hand; the count behind it is the game's.
- `LONG = 0.5` (47), `kit` 229-254 — the brightness kit, never used for FFVI (the namer names its kit).
- `POOLS` (51-52) — **R**: the harmony and accompaniment in one pool, the bass's three names one pool (see `whole.POOLS`).
- `RELEASE` (53-54) — **C**: a release class by pool, the generator's; the envelope word now carries the game's sustain-release in ADSR2.
- `TEMPOS` (56) — the generator's bands, unused by the whole writer (the tempos word). `DELAYS`, `ROWS_PER_BEAT`, `WET` (57-59), `habits` (267-289) — **R** (#1): the echo delay snapped to the nearest named row delay, the wetness binned at 0.35 / 0.7 of main, the feedback kept as its quartiles.
- `gather` (82-120) — keeps each drum's pitches (`g.pitches`, 107) and each sample's envelopes by notes (98); `build` plays a drum at its modal pitch (310) and a sample with its modal envelope (`envelope_of` 179-190) — **R**: a drum's pitch and a sample's envelope vary by song in FFVI; what to count: the share of hits off the modal pitch, the share of notes on a non-modal envelope, both from the SPCs.
- `kit_from_names` (153-164), `drum_uses` half (167-176), `other_slot` (193-201) — **R** (#3): one kit a game by the most-played sample a name.
- `"volume": 58` (325) — **C**: every tonal sample's IT default volume, hand; the whole render sets each note's volume itself (`score_of`), so its effect on this path is doubtful (not verified by ear).

## Faults rather than rules

- **The bass's top is a constant where a word has it.** `writer.bass` takes `register` as a floor only (1780) and `REACH` 16 as the ceiling; the registers word (and the balance's layout) gives the bass a top, 8 semitones over the floor at the median. The written line's 90th percentile sits 12 above the floor, FFVI's 9. Closed in round 34: the bass writes within the range the `ranges` word drew for its sample.
- **The pair word is drawn without its registers and then refused.** `pair_for` draws `layer_samples` by the part alone and `reaches` refuses the pair unless both samples reach the voices' registers within 7 semitones: 8 of 13 checks refused, at most 2 of 9 drawn pairs applied. FFVI played those pairs in registers the plan did not draw with them; either the pair's registers come with it (the balance's shape) or the choice is the owner's. Standing; round 30's `counter_pair_for` runs the same check against the counter's written register and leaves half the "other" counters to the pool rule for it (its open item, the owner's).
- **The relations' habit is never drawn.** `habit_rel` hands the `relations` table its commonest habit value for every song; the conditioning is a once-a-song habit like `step_habits` and should be drawn once (a small fault, one draw). Standing.
- **Two pieces on one voice drop 7 % of the kit's drawn hits.** The drum figure tables count FFVI's kits as the game voices them (the kick and snare on separate voices in 37 of 47 songs); `DRUM_VOICES` puts the kick, snare and toms on one voice and `write` (838) keeps the first at a shared position, so a drawn bar is altered after the draw. Standing.
- **`harness.UPPER_SOUNDS` bypasses `gap_sounds` for the harmony** (894, 898): no audible effect on FFVI (0.99), but a word the writer does not read. Standing.
- **Dead code on the whole-song path:** `FORM_PERIOD` (the span's period discarded by `_free_figures`), `THIN` / `BREAKDOWN` / `thinned` (`energy` never passed), `LOCK_DRUMS` (the drums written first lock to nothing), `BASS_POOLS` (three identical pools); `sample_fits`, `sample_range`, `form_spans_of` and `density_bin` removed in 1.2.0rc4; the energy path (`THIN`, `BREAKDOWN`, `thinned`) is fed by the harness, not by the whole-song writer, and stays, the counter's `echo` / `steps` / `repeats` / `chord_tones` / `repeat_rate` draws and its layer word (known since round 29), and the multi-voice stack branch of `writer.upper` (561-565: the line is always one voice now). Standing.
- **Known and still open, not re-listed above:** the second counter voice apart (4 songs of 20, logged and not written); the counter's clash against the accompaniment not read (its intervals are to the tune only; FFVI's counter sits a semitone from an upper tone at 11 % of its onsets, the tune 9 %). Standing. Rounds 30 and 31 left open besides the tune's rest share (the bar-final cut, the ten's #6); the reach check against a wide written register closed in round 34 (the sample is fitted to the planned register before anything is written). The counter's pitch range over its sample's played range was closed by round 32a's fold (item 7) and then by round 34, which writes every voice inside its sample's drawn range. **Decided, not open:** the fold's hard edge (round 32a: a note one semitone past the `ranges` word's widest band for its sample moves a whole octave, where FFVI keeps 8 to 13 % of such notes a little past the band) is kept as built, by the owner's decision of 2026-10-25: engineered music cannot do every nuance a composer does, and the squeaks are gone; to be looked at again only if something is found missing. Round 34 retired the fold itself; the edge stays in kind at the drawn range's limits (`writer.in_register` folds a draw past the bound by octaves), under the same decision.
