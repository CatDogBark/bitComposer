# The vocabulary: every table, what it counts, what it controls

The idiom writes a song from tables. A table is a count of one kind of
thing (its *unit*) over a game's readings: each unit has an *outcome* (what
was there) and the *values* it may be conditioned on (the part, the tempo
band, the bar before's outcome). A writer draws from a table by naming the
values it has in hand; the table answers from the most specific context it
has enough songs for, backing off toward the part and then the whole table
(Witten-Bell). Some tables are drawn **once a song** (a habit, a key, a
band); others **once a bar** as a *mixture*, where the song's own bars so
far are drawn again (the same as the bar before, an earlier bar, or new)
at the game's rates, so a written part repeats and varies as the game's
parts do.

This file lists every table a pack keeps (`packtables.KEPT`), what its unit is, what conditions it, when it is drawn, and what
the writers do with what it says. The rule of evidence (`../IDIOM.md`): a
writer is never patched past what its vocabulary says; a missing thing is
a new table here, and a table that exists but misleads is fixed as a
drawing fault. The numbers quoted are Final Fantasy VI's (67 songs) unless
said otherwise. Counting code: `translate/rhythm.py` and
`translate/phrases.py`; the plan: `translate/whole.py`; the parts:
`translate/writer.py`.

## The song, drawn once

- **keys** — a song's key (tonic and mode). Drawn once; the plan's key,
  which the chords are spelled in and the tune's scale comes from.
- **tempos** — a song's tempo to five beats a minute. Drawn once; sets the
  tempo band that conditions the habits and the length tables.
- **sizes** — how many parts a song's form has. Drawn once; the fallback
  when no `letters` table can give the form whole.
- **length_habits** — a song's part-length habit (short, medium, long).
  Drawn once; conditions `lengths`.
- **balance** — the song's band with each pitched part's weight, register,
  sounded share, voices, level and, where it holds two voices or more,
  its second voices' levels, and the drums' level
  (`accompaniment=half:56-68:0.8:2:0.6:1.2 bass=half:28-40:0.3:1:1.0
  drums=::::0.8 melody=main:64-84:0.9:1:0.7`).
  Drawn once, whole: which parts the song has, their weights, their
  registers, how long their notes sound, how many voices each part gets
  (`allot` trims the total to the SNES chip's eight), and since round 32
  each part's level as a share of the song's loudest part's in tenths
  (the `levels` unit, the readings' median note level by part; the fifth
  field, the drums' in the same field of a token with no weight), so a
  song's level layout is one FFVI song's whole, as its registers, sounds
  and voice counts already were, and FFVI's joint of the parts' levels
  holds by construction. The plan keeps its `levels` draws on the stream
  and overwrites them with the token's for the parts the token's song
  has (`Plan.level_from`; the log line "levels from the balance: ...; the
  loudest bass"); a part the token lacks (a token without the field: a
  pack built before round 32, the default balance) keeps its draw, the
  counter its `counter_shares` draw. Since round 33 (2026-10-25) a part
  with two voices or more carries a sixth field too: each voice beyond
  the line's level over the line voice's in tenths (the `layer_levels`
  unit, capped at 1.5; `rhythm.voice_level_shares`), the busiest voice
  first, joined by "/" (`accompaniment=main:56-64:1.0:4:0.5:1.0/1.3/1.3`),
  so the line and the voices beside it are one song's together; the
  plan keeps its `layer_levels` draws on the stream and overwrites each
  covered part's with the token's first share (`Plan.voice_levels` by
  rank, `Plan.layer_from`; the log line "second voices from the balance:
  accompaniment=1.2/0.7 bass=0.7"), and `whole.note_level` plays voice
  j beside the line at the token's entry j (a doubling voice at the
  line's level, as before); a part the token's song has as one voice,
  or a token without the field, keeps the `layer_levels` draw. One share
  a voice beyond the line rather than the second's alone: the token's
  voice count is the song's, and a third or later voice's share differs
  from the second's in 23 of FFVI's 52 (Gau 1.5 then 3.2 before the cap).
  Why the sixth field: a second voice at its own `layer_levels` draw on
  a line whose level was the token's had stacked to 1.8 times the tune
  (Whole 03) and the cap of full (Whole 15 and 20), where FFVI's loud
  second voices (1.5 or more, 12 of 43 layered accompaniments) sit on
  lines at 0.59 of the tune and reach 1.21 times it at the median; over
  seeds 1-20 and 28 (15 accompaniments with a second voice) the second
  voice strictly above the tune fell from 5 to 2 (FFVI 10 of 43), the
  stack's maximum over the tune from 1.50 to 1.30 (FFVI's band-themed
  1.21), the notes at the cap of full from 379 to 0; 20000 tokens drawn
  the plan's way put the accompaniment's second voice strictly above the
  tune in 0.21 against 0.29 with an independent draw (FFVI as the token
  plays it 0.21), the bass's second voice at 1.2 times the tune or more
  in 0.31 against 0.44 (0.31). The cost, by design: the token's share is
  capped at 1.5 as `layer_levels` is (22 of FFVI's 148 voices beyond a
  line run past it, Relm's accompaniment to 3.4), and the line plays at
  the part's level (the fifth field, the median over all the part's
  voices), which in 8 of FFVI's 43 layered accompaniments is over 1.2
  times the line voice's own (Epitaph 2.8), so the stack is the song's
  own to within those two. Why: drawn a part at a time, the
  accompaniment's share and the tune's were independent, and 20000 plans
  drawn that way put the accompaniment strictly above the tune in 0.30
  against FFVI's 0.17 (0.12 in tenths; its band-themed songs 0.06, 0.00)
  and at 1.2 times the tune or more in 0.24 against 0.12 (0.09; themed
  0.00), the harmony above the tune in 0.38 against 0.07, and the loudest
  part was the accompaniment in 0.21 of plans against 0.14; Whole 02's
  accompaniment was the loudest voice in the song at 1.67 times the tune
  (+4.7 dB in the stems where both sound), and round 31 had fixed the
  counter alone. Conditioning the accompaniment's share on the tune's
  band gained nothing held out (the accompaniment's share is not told by
  the tune's in FFVI), so the shape that reproduces the joint is the
  song's layout as one unit. The cost, by design: a song's balance is one
  of 66 FFVI layouts (Whole 20 draws The Prelude's, every part at 1.0;
  Whole 28 Dancing Mad's, the drums the loudest alone with the tune at
  0.6). After, over seeds 1-20 and 28 (20 with both parts): the
  accompaniment strictly above the tune in 0.10, at 1.2 or more in 0.05
  (Whole 13, Fanatics' layout, as FFVI has it), the loudest part in 0.10
  tied and never alone, its share 0.60 at the median against FFVI's 0.60;
  the loudest part the bass in 0.57, the tune 0.29, the drums 0.24 (FFVI
  0.61, 0.26, 0.21).
- **weights** — a part's weight in the band (minor, half, main). The
  fallback for a part the balance did not name; a weight conditions the
  rhythm, bass and echo habits.
- **parts**, **voices** — whether a song has each part by the band's size;
  how many voices a song uses. The fallbacks for the band and its voice
  count when the balance table is missing.
- **registers** — the register a part plays in (midi low–high; a layered
  part's line voice's, not the span of all its voices: FFVI's layered
  accompaniments span 16 semitones merged and 12 as a line, and the merged
  span handed to every voice had put one voice over four octaves). The
  fallback register for a part; the writers keep their notes inside it,
  and the voices beside a line sit at their layer offsets from it. The
  `balance` table's registers are counted the same way.
- **sounds** — the share of its gap a part's note sounds. Drawn once a part;
  the writers' note lengths.
- **habits** — a part's density and repetition habit (sparse / medium /
  dense × repeating / mixed / varied), by the tempo band and the part's
  weight. Drawn once a part; conditions the figure tables (`rhythm`,
  `drums`) so a dense part draws dense bars.
- **bass_habits**, **drum_habits**, **drum_group_habits** — the bass's
  habit (density, tones, octaves); the kit's density habit; each drum
  group's own habit given the kit's. Drawn once; condition `bass`, `drums`
  and the group figures.
- **voicing_habits**, **motions** — an upper part's richness (thin, full,
  rich) and how it moves through its tones (block, mixed, arpeggiated).
  Drawn once a part; condition `voicings`, and the motion walks the voices
  along the stack a step a strike.
- **layers** — what each voice of a part beside its line does, by its rank
  (the busiest first): doubling at an interval, alternating, or apart (how
  far off, how dense). Drawn once a voice for a part with two voices or
  more: a doubling voice is written diatonically at the interval; an
  alternating or apart voice becomes a line of its own under the line's
  bars (`second_figures`), in its register, on a tone of the line's own
  voicing (drawn a span) with the line's lengths and the pair's second
  sample. An upper part is the line plus its voices so drawn, never a
  stack: FFVI's accompaniment voices strike together 1.2 to 1.5 to an
  onset, and a stack of voices all striking at every onset had been three
  to four notes loud where the tune has one (Song Check 11's Whole 01).
- **doubles** — what a song's double voices double and how. Counted; the
  plan's second voices are drawn from `layers` instead.
- **articulation**, **step_habits**, **repeat_habits**, **echo_habits**,
  **chord_tones**, **repeat_rates** — the tune's habits: held or detached,
  how stepwise, how often a note repeats, how much a bar echoes earlier
  bars, the share of strong-beat notes on the chord, the share of moves
  that repeat the note. Drawn once a song for the melody (and the
  counter-line); they condition `values`, `moves`, `melody_recall`, and
  the two rates are held by running-share controllers while the tune is
  written (a draw is weighted toward the chord, or the repeated note, only
  while the tune is under its rate).
- **ranges** — the register a sample is played in, by the sample. Drawn at
  rendering: a part's sample is the one of its pool whose game-played range
  covers the part's register best, the part's top weighing most, and one
  of the pack's other tonal samples when the pool reaches nowhere near the
  top; never a random one (`whole.best_sample`). FFVI plays a sample more
  than an octave above its recording in 0 to 2 % of notes; the written
  songs had in 8 to 10 %, the shrillness the owner heard: the old fit had
  asked only that the register's centre lie near the range, and by the
  pack's prefixed names it had found no range at all. A voice written
  beside a line (the counter-line, a chord part's voice apart or
  alternating, the bass's second voice) is kept, once its sample is
  chosen, within the sample's widest band over the word's songs, a note
  outside moved in by octaves (`whole.fold_to_samples`, round 32a): the
  span those voices are written in is the line's register widened by two
  octaves, and it had let Whole 28's counter climb to 94 on a sample the
  game plays between 48 and 72, past the SNES chip's pitch ceiling. The
  band is a hard edge (a note one semitone past it folds a whole octave)
  where FFVI keeps 8 to 13 % of such notes a little past it; the owner
  decided (2026-10-25) to keep it as built.
- **feels** — a song's feel, duple or triple (triple where a quarter of its
  onsets or more fall on thirds, sixths or twelfths of a beat: 6/8 read on
  a 4/4 grid, a shuffle). Drawn once a song; every figure table (`rhythm`,
  `bass`, `drums`, the drum groups) is conditioned on it, so all of a song's
  parts draw bars of one feel. FFVI's bass bars on triplet positions, 18 %
  of them, came only from its compound and shuffle songs; drawn into
  straight songs unconditioned they stumbled against straight drums.
- **layer_sounds** — for a layered part (two voices or more), the share of
  its gap a note sounds, for the line and for the second voice apart. Drawn
  once a part; the line and the second line take their own lengths (FFVI's
  two-voice bass is a sustained line under a staccato voice; the part's one
  share had given both the same).
- **layer_samples** — the samples a layered part's line and second voice
  play, as a pair of the pack's sample names, for every part the plan
  gives layers (the chord parts, the counter-line, the tune, the bass).
  Drawn once a song at rendering, from the part's own pairs alone and
  taken whole or not at all (a pair of one sample, which FFVI plays in
  half its layered chord parts, gives the second voice the line's sample
  whatever the pack gave the line): the line and the second voice take the game's
  pair where the pack holds both samples and each reaches its voice's
  register by the ranges table; otherwise the second voice's sample is
  chosen as the line's is, by its own register and speed (FFVI's bass: a
  long sustained sample under a short one, the same long sample in ten of
  its thirteen two-voice songs). On one sample for both, the busy voice
  had played on the long bass; a pair applied by halves had put Dancing
  Mad's low second-bass sample an octave and a half above its range, and
  a counter-line with no pairs of its own had drawn an accompaniment's
  (round 24).
- **voice_intervals** — a voice beside the line (apart or alternating), in
  the chord parts and, since round 26, the bass, and since round 29 the
  counter-line beside the tune (part counter; its "relation" the sample
  relation `counter_samples` draws, same or other, which splits FFVI's
  intervals: on the tune's sample a third off in 36 % of shared strikes,
  on another an octave or a unison in 37 %), at each onset it strikes
  WITH the line: its interval from the line's note in
  scale steps (7 an octave, 2 a third, signed), by the part, the relation
  and its interval at the previous such onset (the chain). FFVI's voice
  beside an arpeggiated line sits a third below most, an octave off in
  13 % of these onsets, on the line's own pitch in 5 %, and keeps its
  interval 37 % of the time; the writing had taken a tone up the line's
  voicing, never at the octave, holding its interval 54 % (round 23).
  Held out, the chain is worth 0.7 bits a unit; the layer word, the line
  note's chord role and the line's own move add nothing to it.
- **voice_moves** — the same voice at every onset (the counter-line beside
  the tune too, since round 29): its move from its own
  previous note in scale steps, by the part, the relation and the place
  (with the line, or alone where the line is silent). FFVI's voice is a
  melody of its own: with the line it repeats its note 37 % of the time
  and moves a step 21 %, two 17 %, five or more 11 %; alone it repeats
  29 % and steps 37 %. Held out, the move is surer than the interval (3.4
  against 3.9 bits a unit with the line, 3.3 against 4.5 alone), and the
  two words' product is surer than either (3.4 bits). So `writer.upper`
  draws the note both words agree on: with the line, each candidate
  interval weighs its own probability under voice_intervals times the
  probability, under voice_moves, of the move it implies from the voice's
  last note (the line's own move between the two onsets known); alone,
  the move alone. The second bass voice takes the same two words
  (`writer.beside_pitch`, over the figure the second_figures word gave
  it): FFVI's slap plays the sustained line's pitch class at 78 % of their
  shared onsets, a second bass drawn on its own chord roles had at 31 %
  (round 26). Never an interval or a move the game never made; a
  pitch another voice of the part holds at that onset is drawn again,
  and the onset skipped when every try lands on one. The voice sits in
  the span FFVI's voices beside a line sit in (the line's register widened
  by the layer offset's cap), not folded into its own offset register,
  which had turned a drawn third below into a sixth above. A voice placed
  against the line alone, without its move, had leapt five steps or more
  at 43 % of its onsets, FFVI 11 %; with the product 3 %.
- **gap_sounds** — the share of its gap a note sounds, by the part, the
  voice (only; line or second where the part has two) and the gap's
  length to the voice's next onset (under a beat, one to two, two to four,
  a bar or more); counted a note on the chord parts and the bass. Drawn
  once a song for each part, voice and gap class; the bass and upper
  writers take the share by each note's gap (`writer.share_at`), and a
  bar's last note runs to the next bar's first onset, the gap the share
  was counted against (`writer.first_onset`). FFVI's bass plays half of a
  gap under two beats and nearly all of one from two beats on (one voice:
  0.83 under a beat, 0.46 at one to two, 0.97 at two to four; the second
  of two: 0.50, 0.45, 0.97); the one share a voice had (`sounds`,
  `layer_sounds`, which stay for the parts without this word) left the
  slap bass a hole where the game holds, and a note ended at the bar line
  had dropped into a hole when the next bar began late (round 26).
- **bass_locks** — the share of the kit's accents (positions where two
  drum pieces strike together, `rhythm.kit_accents`) that carry a bass
  note, in tenths, by the part. Drawn once a song; the bass writer's lock
  (the figure ladder's `locked`) then asks each bar's figure to strike
  that share of the kit's accents in the bar. FFVI's bass sits on 0.94 of
  them at the median and strikes with some drum at three quarters of its
  notes; by pattern it repeats itself less than the written bass did (a
  recent pattern held in 0.29 of bars against 0.59, the downbeat rested on
  in 0.38 against 0.07), so holding the rhythm is being on the drums, not
  repeating. The writer's lock had counted the whole planned band, which
  the bass, written second with two drum voices to hand, met in no bar:
  0.67 of the accents, 0.44 of its notes with a drum; with the lock 0.78
  and 0.52 on seeds 1-20 (round 28). The word is silent where the kit
  never strikes two pieces at once: 17 of FFVI's 45 kits with a bass, and
  its themed kits in particular (kick and snare nine times a bar, a hat
  under once; four of twelve never stack), so a written kit of that kind
  (Whole 28) locks to nothing. What holds there is label-free: the bass's
  strikes fall on a kit onset at 0.77 of its notes (by bar: all of them in
  0.58 of bars, none in 0.16), and the bass keeps its density from bar to
  bar (0.59 of FFVI's bar pairs within one strike under the walking habit,
  0.18 jumping four or more); neither is counted yet.
- **levels** — a part's level as a share of the song's loudest part's, in
  tenths ("1.0" the loudest part), by the part; from the readings' own note
  levels. Drawn once a song for every part; the loudest plays at
  `whole.TOP_LEVEL` and the rest at their share (`whole.note_level`; the
  band's loudest sits under it where the token's loudest part was left
  out of the band by the textures, 2 plans of 200 seeds).
  Since round 32 the draw is overwritten by the `balance` token's level
  for every part the token's song has, so with a pack built since then it
  covers only a part the token lacks (a token without the field); the
  draw stays on the plan's stream so every draw after it is what it was.
  The unit is the token's and `counter_shares`'. FFVI's parts sit close,
  the bass loudest (0.28 of full), the tune 0.22, the chord parts and the
  counter-line 0.19, the harmony 0.18; the hand-set mix had the tune at
  1.4 times the accompaniment and the pads at 0.6 of it, a lead over a
  backing (round 25). Drawn a part at a time the shares were independent
  across the band, which FFVI's are not (the `balance` entry).
- **layer_levels** — a layered part's second voice's (the busiest beside
  the line) level against its line voice's, in tenths, capped at 1.5
  (`rhythm.LAYER_LEVEL_CAP`), by the part. Drawn once a song for every
  pitched part; since round 33 the draw is overwritten by the `balance`
  token's sixth field (the same unit, one share a voice beyond the line)
  for every part the token's song holds two voices or more in, so with a
  pack built since then it covers only a part the token's song has as one
  voice or a token without the field (a pack built before round 33); the
  draw stays on the plan's stream so every draw after it is what it was.
  Over seeds 1-20 and 28 every layered part (31 of 31) takes the token's
  shares and this draw fires 0 times. FFVI's second voice sits at 1.0 of
  its line in 43 of 96 layered parts, under in 22, over in 31 (13 past the
  cap, Relm's accompaniment at 3.4); drawn apart from the line's level it
  had stacked past the tune where FFVI's loud second voices sit on quiet
  lines (the `balance` entry).
- **counter_shares** — the counter-line's level as a share of the song's
  loudest part's, in tenths (the `levels` unit), by the part and the band
  the tune's own share falls in (`rhythm.TUNE_SHARES`: under 0.7, 0.7 to
  0.8, 0.9 and up; FFVI's terciles over its 52 songs with both parts, 20,
  15 and 17 songs); one unit a song with both parts and a level for each.
  Drawn once a song in `_plan_counter`, after the tune's `levels` draw and
  under that draw's band, in place of the counter's own `levels` draw
  (`extras.counter.level`; `note_level` plays it as any part's share)
  where the `balance` token's song has no counter level (round 32: the
  token's counter level stands, as the rest of the band's do, and the
  draw is made all the same so the stream is as it was; with a pack
  built since round 32 this word fires only for a token without the
  field). A
  share of the loudest never passes 1.0, so the counter can never be
  louder than the loudest part, as FFVI's is not: its counter is strictly
  the loudest in 2 songs of 52 and tied at the top in 5, at 0.60 of the
  loudest at the median, 0.9 or more in 6 of 52; under a tune under 0.7
  its share is 0.50 at the median (the one 1.0 there is The Serpent
  Trench), under a tune at 0.7 to 0.8 0.70, under a tune at 0.9 or 1.0
  0.70 with four at 0.8 and three at 1.0. This word replaces
  `counter_levels` (round 29: the counter's level over the tune's in
  tenths, by the part alone), which was a right word with a right table
  but was drawn apart from the tune's `levels` draw and multiplied into
  it, and FFVI's joint does not allow what the product allows: 20000
  plans drawn that way put the counter above the loudest part in 0.037
  and at 0.9 or more in 0.240 (FFVI 0 and 0.115), and Whole 28 drew 1.5
  (FFVI's one song in 52) on a tune at 0.7, the counter at 1.05 of the
  loudest, the loudest voice in the song, +3.5 dB over the tune by level
  alone. The ratio under the tune's band (shape A) was weighed against
  this shape by the same simulation: A 0.017 above the loudest and 0.171
  at 0.9 or more, since the ratio's own votes under a band still multiply
  past 1.0 (Dark World's 1.3 on a tune at 0.8 gives 1.04 even from FFVI's
  own song), and a leave-one-song-out likelihood prefers the share by 0.3
  bits a song under these bands (by 0.11 to 0.46 under the other splits
  tried); what A keeps and this shape loses is the counter exactly
  at the tune's level (FFVI 24 of 52, A 0.46 of plans, this word 0.23),
  and the counter over the tune at the median is 0.87 against FFVI's 1.00
  (round 31).
- **counter_samples** — whether a song's counter-line plays the tune's
  sample (`same`: the sample most of its notes are on is the tune's) or
  another (`other`), one unit a song with both parts, by the part. Drawn
  once a song (`extras.counter.sample`): the kind the counter's
  `voice_intervals` and `voice_moves` are drawn under, and at the
  rendering a `same` counter takes the tune's sample whatever its pool
  says, an `other` counter the pool's best but the tune's, chosen for the
  register it was written in (beside the tune, not the register the plan
  drew for it). FFVI: 18 of 52 by the merged notes (17 of 52 by the line
  voice the unit counts); the pool's own choice had given the written
  songs 3 of 14, and 10 of 14 once the counter sat where the tune is
  (the pool's favourite sample is the tune's), so the word has to be
  honoured both ways (round 29). Which other sample is `counter_pairs`'.
- **counter_pairs** — the counter-line's sample where it plays another
  than the tune's, as the pack's sample id, by the part and the tune's
  sample id; one unit a song whose `counter_samples` kind is `other`
  (FFVI: 35 of 52, 23 of them with both samples in the pack). Drawn once
  a song at the rendering, after the tune's sample is chosen
  (`whole.counter_pair_for`): the table's distribution under the tune's
  sample as a plan draw sees it (the tune's context mixed with its
  back-off, the counter's sample over all tunes, which is still a count),
  restricted to the samples the pack holds, not the tune's own, in reach
  of the register the counter was written in (`reaches`, the check
  `layer_samples` makes through `pair_for`); the old pool rule by register
  and speed remains only where no counted sample fits, and the plan's log
  says which of the three the sample came from and what was passed over.
  FFVI's counter sample is darker than the tune's in 17 of the 23 pairs
  the pack holds (its body louder in 15); for a tune on sf89f5aedfd its
  partners are sfd6accf98a four times in ten, s256b199ccf three, then
  s605f200105, s8320f1bea2 and s4fd4b0992b. The rule had given Whole 28's
  counter sdbd05ab4d5 beside that tune at a 0.28 chance, a sample 4.2 dB
  louder in its body and nearly twice as bright, which FFVI never plays as
  a counter against another tune sample; the pair word gives it
  sfd6accf98a. A first cut drew once and refused at the first misfit (a
  sample the pack lacks, a drawn range short of a wide written register)
  and left eight songs of ten to the rule, Whole 28 among them (round 30).
- **climax** — which of a song's tune phrases holds the tune's highest note,
  by its place among them (opening, early, middle, late, closing). FFVI's
  tune peaks at 0.45 of the song at the median; the written tunes had
  peaked at 0.24. The melody writer draws it once and gives that phrase the
  song's peak as its ceiling.
- **arc** — how far a tune phrase's highest note sits under the song's peak
  (0, 1-2, 3-5, 6-9, 10+ semitones), by the phrase's place. Drawn a phrase:
  the phrase's ceiling in the arc.
- **summit** — how far the tune's highest note sits above the tune
  register's top (the 90th percentile, the registers table's), in
  semitones (0, 1-2, 3-5, 6+). Drawn once a song: the climax may rise above
  the register as FFVI's does (its tunes span 22 semitones; the written
  ones had spanned 16).
- **sample_lengths** — the shortest note a song plays a sample at, as a
  class of its tenth-percentile note length in ms (40, 60, 80, 120, 160,
  240, 400, long), by the sample. Drawn once a song for each sample the
  rendering uses: a note on the sample is never shorter than that (its
  voice's next key-on still cuts it). A note shorter than the game ever
  plays a sample never reaches the sample's body (a pad with a 39 ms
  attack had been played at 50 ms sixteenths; FFVI plays it at 65 ms at
  the shortest).
- **sample_speeds** — the fastest bars a song plays a sample in, as a class
  of the ninetieth-percentile bar rate in notes a second (2, 3, 4, 6, 8,
  12, 24, faster), by the sample. Read in the sample choice for a part
  (`whole.best_sample`) beside the ranges: of the samples covering the
  part's register, one a song of the game plays as fast as the part's
  fastest bar comes first, then one some song plays that fast in its
  fastest bars, and where none does the excess over the game's fastest on
  the sample weighs against the range's fit. FFVI keeps its slow-attack
  pad under six notes a second; a written part had it at eight.

## The form

- **letters** — a song's form as its parts' letters in order (`A B A B C`),
  drawn whole. The form's shape: which parts repeat which.
- **form** — a part of the form as new, again or back, by its index. The
  fallback chain when no `letters` table exists.
- **lengths** — a part's length in bars, by the meter and the song's length
  habit. Drawn a part; a repeated part is as long as the part it repeats.
- **loops** — the chord the loop returns to. Where the loop starts (after an
  intro); the render plays the loop's first bars again at the end of a
  listening page's song.
- **part_textures** — the texture a part of the form keeps (which parts
  sound: `all`, `no drums melody`), by its place in the form and the part
  before's. Drawn a part: a part keeps one texture (FFVI's parts do), an
  intro leaves parts out, a repeated part keeps its texture.
- **texture**, **presence** — which parts sound in a bar after the bar
  before's; a part playing or resting in a bar. Counted; the whole-song
  writer uses `part_textures` (a part keeps its texture) instead.

## The harmony

- **chords** — a bar's chord as a numeral in the key, after the bar
  before's. Drawn a bar as a chain; a repeated part keeps its chords; a
  theme return brings the theme's chords back when `return_band` says so.
- **changes**, **cadences** — where in the bar the chord changes; how a
  part's progression ends. Counted, not yet drawn (the written chords
  change on the bar line).

## The riff: a backing part's period

- **periods** — a backing part's (drums, bass, accompaniment, harmony,
  arp) period inside a part of the form: the lag in bars at which its bars
  repeat (1, 2, 4, 8; the bass by its figure, the drums by their pieces,
  an upper part by its pattern, so a riff that moves with the chord keeps
  its key) or none, by the part of the form's length and the tempo band.
  Drawn once a backing part for each new part of the form; a repeated part
  of the form replays anyway. The riff under the tune, which the parts'
  mixtures (a bar the same as the one before, an earlier one, new) never
  held at a fixed lag: a third of FFVI's bass and accompaniment parts and
  two fifths of its drum parts have one, and the share is much the same
  across the 39 games read.
- **period_holds** — inside a period, whether a bar plays the bar a period
  before again (held) or varies (a fill, a turnaround), by the part and
  the period. Drawn a bar inside a period; the writers play the bar a lag
  before again where it is held (the figure, re-realized on the bar's
  chord; an upper part takes its source bar's voicing too on the same
  chord) and draw the bar fresh where it varies.

## The drums

- **drums** — the kit's bar as one figure, every piece. Drawn a bar as a
  mixture under the kit's habit: the kit repeats and varies as a kit does
  (the groups drawn apart had changed every bar). The drum group habits
  the plan draws (the hat's, the cymbals', the rest's) cap each piece's
  hits a bar at its density tier's top in the draw (`writer.group_caps`):
  "sparse" cymbals had come up as a ride in sixteenths in five songs of
  twenty against four of FFVI's 67.
- **drums-KSt**, **drums-h**, **drums-c**, **drums-o** — the kick, snare and
  toms' bar; the hat's; the cymbals'; the other sounds'. The group figures,
  drawn by the slice writer (`tools/slice1.py`); the whole-song writer
  draws the kit as one.

## The bass

- **bass** — the bass's bar as a figure: positions with chord-tone marks
  (root, fifth, octave, passing). Drawn a bar as a mixture under the bass
  habit, realized on the bar's chord in the bass's register; a second bass
  line apart (from `layers`) is written the same way in its own register.

## The upper parts (accompaniment, harmony, arp)

- **rhythm** — a part's bar as an onset pattern; for an upper part holding
  two voices or more, its own line's bar (the voice with the most notes),
  not the voices merged. Drawn a bar as a mixture under the part's habit:
  the line's figures. (Counted merged, a dense bar held two voices'
  onsets, and a line written to it with a second line beside struck 10.3
  times a bar against FFVI's 7.3.)
- **second_figures** — a voice beside a layered part's line, bar by bar,
  where the part holds two voices or more, by the song's feel and tempo
  band, the line's onset count and its pattern. The voice is a mask over
  the line's onsets, which of them it strikes with and any onsets of its
  own (`1 0 1 0 | 7/2`; `-` resting), for the chord parts and, since round
  27, the bass (its second voice had been a figure of its own drawn under
  the line's bar, and where the written line's bar was one FFVI never
  played, which is most bars, the draw backed off and came back unrelated
  to the line: FFVI's slap strikes with three quarters of the sustained
  line's notes and twice as often in all, the written one had struck with
  two fifths; `writer.mask_figure` keeps the line's marks where the slap
  strikes with it and gives its own onsets the root, both re-pitched by
  the voice words; the bass mask's floor steps down where its context
  holds under two songs, the thirteen two-voice basses being thin at the
  onset count, which had doubled the line where FFVI fills: round 28):
  FFVI's voices
  beside an arpeggiated line strike with a sparser subset of the line's
  own rhythm (two thirds of their onsets on the line's, 0.6 of its
  density), on other tones of the same voicing, with the line's note
  lengths; drawn as a pattern of their own they had fallen with the line
  a seventh of the time, four unrelated lines in one register (Song Check
  12). The draw never backs off below the line's onset count (a mask from
  a shorter line read around a longer one had filled it). Without the
  tempo, Dancing Mad's 60 BPM tremolo bass bar had landed in a 115 BPM
  song at ten notes a second, twice FFVI's fastest bass. FFVI's
  second accompaniment voice strikes 4.5 times a bar beside a line of 6.6,
  two of five of its onsets with the line's; its second bass voice is the
  busy staccato one under a sustained line in the same register (the bass
  figure table counts that line).
- **voicings** — which chord tones an upper part holds in a span, by the
  chord's shape and the part's richness. Drawn a span as a mixture; the
  tones are stacked on the voices, lowest first.
- **widths** — how wide the upper voicing sits. Counted; the stack's spread
  is set by the register for now.
- **values** — a melody note held or detached, by its value and the song's
  articulation habit. Drawn a note; the tune's note lengths.

## The tune (the melody; the counter-line is written beside it, below)

- **moves** — the tune's move note to note (semitones, to an octave), under
  the song's stepwise habit, by where the arriving note falls in its beat
  (strong or weak), the tone the note left stands on against the chord
  (root, third, fifth, another tone, no chord) and the move before. Drawn
  a note for a new cell: the move is chosen among the moves that fit (the
  register, no clash with what sounds, the scale on a strong beat, the
  phrase's contour) with the table's weights. The landing was counted from
  the start but not drawn by; drawn by it, the table carries the game's
  own approach to the chord (FFVI's: by step). The chord weighting on
  strong beats, which holds the song's drawn chord-tone rate, acts on such
  a table only while the tune is under its rate (with no weighting at all
  the written tunes landed on the chord 0.48 against FFVI's 0.56; steps
  inside a bar 0.67 against 0.65; with the gate 0.57 and 0.61).
- **contours**, **contour_sizes**, **peaks** — a four-bar phrase's contour
  (rising, arch, falling…); how far it goes in semitones by its shape;
  where it peaks. The contour and its size steer a new phrase's line
  (`contour_targets`); the peaks are counted, not yet drawn.
- **relations**, **phrase_shifts** — how a phrase stands to the one before
  (new, repeated, moved up or down, answered); how far it sits above or
  below the one before, by that relation. Drawn a phrase: a repeated or
  moved phrase is the last phrase again, moved; a new phrase sits where the
  shift says and the line is steered there over its first third (taken as
  a jump, the phrase-start moves had been a quarter steps against FFVI's
  half).
- **endings** — the note a phrase ends on, against the key. Drawn a phrase;
  the last note is placed on the degree.
- **melody_recall** — the tune's urn: a bar the same as the one before, an
  earlier one again, or new, by the song's echo habit. Drawn a bar: an
  echoed cell is re-rooted on the bar's chord, its intervals kept whole,
  the whole cell moved to the start that lands the most strong beats on the
  chord (bending single notes had cost the melody its steps).
- **cell_rhythms** — a new cell's rhythm: new to the tune, the bar before's,
  or an earlier one's. Drawn for a new cell; the rhythm itself then comes
  from the part's `rhythm` table.
- **phrase_letters** — a part's phrases as letters: the theme head again
  (`T`), an earlier head again (`r`), or new (`n`), by how many phrases the
  part has and its place in the form. Drawn a part of the form; the first
  phrase the tune plays is the song's theme. With the *carry a theme*
  switch the letters are drawn again until the theme comes back.
- **theme_body** — how much of the theme phrase comes back with its head.
  Drawn a return: the theme's head, then that many of its bars, then new.
- **return_band** — which of the chords, the bass and the accompaniment come
  back with the theme. Drawn a return: the theme's chords are copied under
  the return and the bass and accompaniment play their theme bars again
  (`song.copies`). With the *band comes back* switch a return with nothing
  behind it is drawn again.
- **theme_doubling** — where the tune plays its theme cell (its statement,
  or an echo later), which other parts play the same cell with it and how
  far from the tune (`counter:+12`, `bass:-24`, `none`), by place. Drawn a
  theme-cell bar after the parts are written: the drawn parts play the
  tune's bar at the interval, in their register. FFVI doubles the hook in
  a third of its theme-cell bars, the bass two octaves down most often.
- **theme_carrier** — the part that carries the theme phrase under a phrase
  whose tune is not the theme (the bass, the counter, the accompaniment;
  almost always none). Drawn a phrase: the carrier plays the theme phrase
  in its register while the tune plays what it drew. Rare in FFVI (one
  phrase in a hundred), and kept at that rate.

## The counter-line, beside the tune

- **counter_figures** — the counter-line's bar as a mask over the tune's
  bar, counted as `second_figures` counts a voice beside its part's line
  with the tune's line as the line (the melody's line voice where it holds
  two): which of the tune's onsets the counter strikes with and any onsets
  of its own (`1 0 1 0 | 7/2`; `-` resting under the tune), by the part,
  the song's feel and tempo band, the tune's onset count and its pattern;
  where the tune rests the pattern is `-` and the count 0, and the outcome
  is the counter's own onsets alone (`| 0 2`); a bar both rest in is the
  texture's and not counted. Drawn a bar after the tune is written, in
  the bars the plan has the counter play, with the floor never below the
  tune's onset count (`MASK_FLOOR`) and stepping down where its context
  holds under two songs (`PLAN_SONGS`), as the second bass voice's mask
  is; `rhythm.apply_mask` makes the counter's positions, its own onsets
  standing alone at a resting tune. The pitch over those positions comes
  from `voice_intervals` and `voice_moves` under the `counter_samples`
  kind (`writer.counter`, with `writer.beside_pitch`: with the tune, the
  tune's note and the interval both words agree on; alone, its own move;
  the first note of a song the tune leaves it alone with is the chord's
  root nearest its register), kept by octaves in the tune's register
  widened by the layer offset's cap (a drawn third below folded into the
  counter's own register had turned into a sixth above, round 23); on
  the tune's sample a drawn unison is drawn again (two copies of one
  sample on one pitch), the onset skipped after four. The lengths are the
  `values` word's under the counter's articulation habit, a bar's last
  note running to the next bar's first onset, the gap the word was counted
  against (the melody writer still cuts its own at the bar line). FFVI's
  counter plays WITH the tune, not in its rests: 0.67 of its onsets on the
  tune's, 0.82 of its sounding time under the tune's notes, 1.42 times
  its notes, as loud, 64 % of its notes below the tune, 2.5 semitones
  under at the median, and it fills 0.61 of the tune's resting time;
  written by running the melody writer a second time with its own random
  stream, knowing nothing of the tune but the planned register, the
  counter had 0.43 of its onsets on the tune's (seeds 1 to 20) and Whole
  28 0.19, on the tune's sample in the tune's register: two tunes
  interleaved on one timbre, "competing for air time" (round 29). What
  the old path gave the counter and this word does not: its phrase arc,
  contours and endings, the echo urn (`melody_recall`; the `echo` habit
  is still drawn, unused), the chord-tone and repeat-rate controllers,
  the step habit, the reference-set check, and a second counter voice
  apart (its layer word is drawn and logged, the voice not written: no
  word counts a voice beside a counter that follows the tune); the
  articulation, echo and sounds draws stay in the plan as they were.

## What a written song records

A song's plan (`Plan.to_json`) keeps every once-a-song draw, the form, the
chords, the textures, the theme and its returns, the switches under
`options`, and a log line a draw; each written part keeps its figures and
a log of what it drew and copied (a second line, a doubled theme bar, a
part played again note for note). The Song Check pages show the plan's
draws on each card so a strange choice can be told from a bug.
