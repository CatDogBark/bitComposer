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
- **top_levels** — a song's loudest part's median note level of full
  (the readings' scale, the SNES chip's voice volume over 128), to 0.05,
  one unit a song (round 52, 2026-10-28). Drawn once a song on its own
  stream (`Plan.top_level`); every part's share from the balance token is
  a share of it (`whole.note_level`), the TOP_LEVEL constant (0.85)
  standing without the word. Why: rendered through the same player as
  FFVI's converted songs, the written songs sat 5 dB hotter (-19.6
  against -24.5 dBFS over the first minute) because the loudest part
  always played at 0.85 of full where FFVI's sits at 0.2 to 0.4.
- **ranges (by the part)** — since round 55 (2026-10-29) a sample's home
  band is counted by the sample alone and by the sample with the part
  playing it (`sample_range_units`, shape part + role; the draw backs off
  to the sample alone where the pair has under two songs), and every
  draw names the part (`whole.range_context`). Why: a sample shared by
  parts sits 9 semitones apart by part at FFVI's median, a bass sample 54
  (as a bass at 32, as an accompaniment at 86), and a part drawing a
  shared sample could take another part's register. And since round 53 a
  chord part's home band narrower than MIN_SPAN gives way to the sample's
  whole played range (`whole.wide_enough`, the `sample_ambitus` word):
  Searching for Friends strikes one sample at one pitch as accompaniment,
  and that band had bound Whole 67's three-voice accompaniment to a single
  pitch for 45 bars; a sample the game only ever plays at one pitch keeps
  it (a drum sample as a rhythmic chord part, 0.08 of FFVI's
  accompaniments).
- **tempos (under the token's class)** — since round 54 (2026-10-29) the
  balance token ends with its song's tempo class (`tempo=slow`, `medium`,
  `fast`: under 85, under 130, over) and the `tempos` word is counted by
  the class; where a plan's tempo draw falls outside its token's class the
  tempo is drawn again under the class on an own stream (the log line
  "tempo 160 BPM is outside the band's class (slow): 75 BPM drawn under
  it"). Why: the tempo drawn apart had put Relm's band (70) at 160 and
  Slam Shuffle's (114) at 70, only 14 of 45 plans sat in their token
  song's class, and the fastest written tune ran 8.2 notes a second
  against FFVI's 4.7 (after, the plans sit in class 0.82 of
  the time, the fastest tune 4.8, the fastest accompaniment 12.4).
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
  so the line and the voices beside it are one song's together (the cap
  1.5 until round 51, 2026-10-28, then 4.0, past the readings' 3.35: 27
  of FFVI's 148 voices beside a line ran past 1.5, and in every one the
  line was a quiet inner voice at 0.42 of the song's loudest with the
  voice beside it at 0.99, the part's melody-level voice, which the cap
  had played 4 dB under; the note level's cap of full stands); the
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
  Since round 39 (2026-10-27) the counter's token carries a seventh
  field too: whether it plays the tune's sample (`counter_kind`, same or
  other: `counter=minor:56-72:0.9:1:1.0::other`), so what the counter is
  and how loud it is are one song's together; the plan makes its
  `counter_samples` draw and overwrites it with the token's
  (`Plan.kinds`, `extras.counter.sample_from`; the log line "counter
  beside the tune: other sample with the band's, ..."). Why: Whole 33's
  band was The Serpent Trench's whole, the one FFVI song whose counter
  is the loudest part (1.0 to the tune's 0.6), where that counter is 28
  held notes on another sample in 14 of the tune's 33 bars; its level
  came from the token and its kind from its own draw ("same"), so the
  descant's level sat on a thirds doubling of the tune on the tune's
  sample, +4.4 dB over it in the stems (20·log10(1.0/0.6) exactly).
  FFVI's counters on the tune's sample at its onsets (16) sit at 1.0
  times the tune in 13 and never above 1.21; its 7 counters louder than
  the tune are, bar one, on another sample. The table's 66 outcomes keep
  their order and votes with the field stripped, so every balance draw
  lands where it did; 17 tokens say same, 34 other (the Dancing Mad pair
  share one).
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
  fallback register for a part where the `balance` token has none; since
  round 34 it is the register a part's sample is fitted to, and the voice
  is written in the range the `ranges` word drew for that sample
  (`whole.bound_of`). The `balance` table's registers are counted the
  same way.
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
  pack's prefixed names it had found no range at all. Since round 34 the sample comes before the
  notes: `whole.samples_for` runs before the writing, fitted for speed to
  the part's drawn fastest bar (`part_speeds`), and the range the word
  draws for the chosen sample is the register the voice is written in
  (`plan.bounds`, `whole.bound_of`: the overlap with the planned register,
  a sliver widened to two of the register word's bins, the sample's range
  alone where the two miss, the planned register where the word knows
  nothing of the sample). The melody, the chord parts and their voices
  beside the line, the counter, the bass and its second voice all take
  that bound, so every voice plays where the game plays its sample by
  construction. Retired with it: the span a voice beside a line wrote in
  (the line's register widened by two octaves), the second bass voice's
  span, the bass line's floor plus REACH as its ceiling, and round 32a's
  fold to the sample's widest band (which had covered the beside-line
  voices only: the bass line still wrote 24 % of its notes past its
  sample's widest band, the melody 2 %; Whole 02's counter at 84 on a
  sample one song plays to 88 and eleven to 80 or under was its blip).
  The edge the owner kept in round 32a stays in kind: a draw past the
  bound folds by octaves into it (`writer.in_register`).
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
  had dropped into a hole when the next bar began late (round 26). Since round 35 the word is counted under the part's speed class as
  well (its fastest bar: slow to 3 notes a second, medium to 6, fast
  beyond; `rhythm.speed_tier`), between the voice and the gap, and the
  plan draws it again under the part's drawn speed (`part_speeds`) once
  that is known. FFVI's string pad played fast sounds a fifth to a third
  of its gap (Battle Theme 0.24, Save Them! 0.40), the battle tremolo,
  and played slow nearly all of it; one share by the gap alone had put
  Whole 02's fast arpeggio on that pad between the two, 90 ms notes at
  0.7 of the gap, a staccato pad neither held nor tremolo.
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
  honoured both ways (round 29). Which other sample is `counter_pairs`'. Since
  round 39 (2026-10-27) the draw is made and overwritten by the balance
  token's seventh field where the token's song has a counter (every FFVI
  token with one): the kind is one song's with the level
  (`extras.counter.sample_from`: `balance` or `counter_samples`).
- **counter_figures (the counter's weight)** — since round 47 (2026-10-28)
  the mask is counted and drawn under the counter's weight in the band
  (the balance token's) before the song's feel and tempo band, and its
  draw never backs off below the tune's onset count with the weight in
  front (`COUNTER_MASK_FLOOR`). Why: FFVI's minor counter plays 0.74 of
  the tune's notes a bar, its half one 0.91, its main one 1.45 (3.5, 8.6
  and 16 notes a played bar), and the mask drawn without the weight had
  every written counter at about six notes a bar whatever its label
  (minor 6.2, half 6.4, main 5.6); after, 4.7, 7.1 and 6.2.
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
- **section_levels** — a part's median note level in a section over its
  median level in the whole song, in tenths between 0.3 and 2.0 (`1.0`:
  its usual level; `0.5`: half of it, an intro's bass; `1.5`: a swell),
  by the part and the section's place in the form (round 48, 2026-10-28;
  counted from the readings' note levels, `Song.note_levels`, which
  `rhythm.load` now keeps). Drawn a part an own section it plays in
  (`whole.plan_section_levels`, `Plan.section_levels`: a multiplier a
  bar), a repeated section copying its source's, the drums at one level;
  `whole.note_level` takes the note's bar and multiplies the part's level
  by it, within the cap of full. The log line: "levels by section
  (section_levels): accompaniment 0.5 in A; bass 0.8 in A". Why: FFVI's
  parts hold one level at the median but a quarter move by 1.5 times or
  more across the song; 0.7 to 0.9 of a part's sections sit at 1.0, and
  first sections sit under it (the bass's 0.3 to 0.8 in 0.22 of songs,
  the melody's under in 0.23), last and middle ones over it now and then
  (the accompaniment over in 0.15 of middle sections); the written parts
  had played one level all song. After, over seeds 1-45, 40 plans move a
  part in some section, with the parts' sections at 1.0 in 0.77 to 0.86.
- **part_entries** — where inside a section a part present in it enters
  and leaves: `whole` (its first bar to its last), `enters:k` (its first
  sounding bar k bars after the section's start), `leaves:k` (its last k
  bars before the end), or both, k to ENTRY_CAP (8); by the part, the
  section's place in the form and the section's length class (short to 4
  bars, medium to 8, long) (round 46, 2026-10-28). Drawn in
  `whole.plan_texture` for each part the section's texture has, after the
  texture; the part's bars before its entrance and after its exit are
  turned off; a draw no section this short can hold is drawn again, then
  the part plays it whole; a repeated section copies the bars, entrances
  and all. The log line: "entrances (part_entries): counter enters 2 in
  B; bass leaves 1 before the end of C". Why: FFVI's parts join inside a
  section more often than at its edge (61 late entrances inside, 45 at a
  boundary; early exits 14 and 12), where one texture a section had let
  them join at its lines alone; after, seeds 1-45 have 37 inside and 40
  at a boundary (exits 12 and 6). FFVI by part: the melody plays its
  section whole 0.81 of the time, the counter 0.86, the bass 0.89, the
  accompaniment 0.90; the rest enter a bar or two in, or leave a bar early.
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
  the shortest). Since round 36 the word is counted under the sample's speed class in
  the song as well (slow, medium, fast by its fastest bar, `speed_tier`),
  and a chosen sample's floor is drawn under the speed class of the
  fastest part it serves. A floor drawn by the sample alone had taken a
  slow song's 120 ms for Whole 02's string pad at sixteenths and raised
  the notes round 35 had shortened to 50 ms back past where they were;
  FFVI's fast uses of that pad have 40 to 70 ms notes.
- **sample_speeds** — the fastest bars a song plays a sample in, as a class
  of the ninetieth-percentile bar rate in notes a second (2, 3, 4, 6, 8,
  12, 24, faster), by the sample. Read in the sample choice for a part
  (`whole.best_sample`) beside the ranges: of the samples covering the
  part's register, one a song of the game plays as fast as the part's
  fastest bar comes first, then one some song plays that fast in its
  fastest bars, and where none does the excess over the game's fastest on
  the sample weighs against the range's fit. FFVI keeps its slow-attack
  pad under six notes a second; a written part had it at eight.

- **part_speeds** — a part's fastest bars, as a class of the
  ninetieth-percentile bar rate of its line in notes a second (the
  `sample_speeds` classes), by the part and its habit's density tier
  (sparse / medium / dense, as the habit words bin it). Drawn once a part
  after every other plan draw (`whole._plan_speeds`): what the part's
  sample is fitted to for speed before the part is written (round 34).
  The fit had read the speed off the written notes, so the sample was
  chosen after the writing and a voice's register could not come from
  the sample it plays.

- **cell_handoffs** — a tune's half-bar cell taken up by another part in a
  later bar: the first such part and how many bars on ("counter 2",
  "bass 1", "far" past eight bars; "none"), by the part (melody), the
  song's echo habit and the cell's place (theme: inside the tune's theme
  phrase; other). A half-bar cell is the half's onsets in twelfths and its
  intervals, two notes at least (`rhythm.half_cells`). Drawn once a cell
  of the written tune after the parts are written (`whole.hand_off_cells`,
  round 37): where the drawn part does not already play the cell later,
  its line's half bar there is replaced by the cell re-rooted on that
  bar's chord in the part's own register (`writer.cell_pitches`: the
  cell's offset from its own bar's root, then its moves as scale steps),
  the tune's note lengths kept. FFVI's themed songs hand half their
  tune's half-bar cells to the counter, the accompaniment or the bass in
  another bar (0.51; all songs 0.34); the written songs had 0.05, each
  part faithful to its own word and none to the theme.
- **half_recall (held halves)** — since round 47 (2026-10-28) the urn runs
  only on a half the drawn rhythm gives HALF_CELL_NOTES notes or more,
  as the word counts them; a half with fewer stays as drawn. Why: run on
  every half, it had replaced the tune's held halves with recalled two-note
  ones, and the written medium tune had 0.11 of its bars at one or two
  notes against FFVI's 0.27, a note a bar denser at every habit tier
  (sparse 2.7 against 2.0, medium 5.1 against 4.1, dense 8.2 against
  7.0); after, 2.0, 4.9 and 6.9, the medium tune's one-and-two-note bars
  0.17.
- **half_recall** — what a tune's half-bar cell is to the tune so far
  (same: the half before's cell again; earlier: one played before; new),
  by the part and the song's echo habit: the tune writer's urn at the
  half bar (`writer.new_cell_halves`, round 38). A new bar is drawn a half
  at a time: a recalled half comes back re-rooted on the bar's chord in
  the register with its moves as scale steps, a new half takes the drawn
  rhythm's onsets with new moves. FFVI's tune reuses half-bar cells more
  than bar cells (0.50 of halves heard earlier, themed 0.63; bars 0.32 and
  0.52): its cells are moved and re-intervalled inside the bar where a
  writer whose cell was the bar drew a whole new bar (0.39).

## The form
 The draw is floored at the part and its tier: a dense
  accompaniment had drawn 2 notes a second from the coarser level's
  mass, a value FFVI's dense accompaniments never have (round 35).
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
  chord (bending single notes had cost the melody its steps). Since round
  41 (2026-10-28) "kept whole" means exact: a cell that comes back is
  rebuilt from its intervals in semitones and folded into the register by
  whole octaves (`writer.fold_cell`), not from its scale steps with each
  note clamped, which had sent 0.46 of the written recalls back as a cell
  the tune never played (0.17 after; FFVI's moved cells keep their
  intervals, a rhythm with other intervals 0.06 of its bars). The half-bar
  urn's recalled halves are rebuilt the same way. Since round 49
  (2026-10-28) a recalled cell is folded into the part's whole room (its
  register up to the arc's peak), not the phrase's room under the arc,
  which had clamped a wider recall; and the `endings` degree is put on a
  phrase's last note only where that last bar is a new cell, a recalled
  last bar keeping its cell as FFVI's identical recalls do (the ending
  moved onto a recall had made 33 of 76 bent recalls). Recalls that come
  back as a cell the tune never played: 0.24 to 0.10 of recalls.
- **cell_rhythms** — a new cell's rhythm: new to the tune, the bar before's,
  or an earlier one's. Drawn for a new cell; the rhythm itself then comes
  from the part's `rhythm` table.
- **recall_continues** — whether a passage the tune recalls goes on with
  the bar after its source (`yes`, `no`), by the part and the song's echo
  habit (round 50, 2026-10-28): FFVI mixed 0.64, repeating 0.91, varied
  0.30. The melody writer draws it where the bar before was an "earlier"
  recall and its source has a bar after it (`continues()`); the CONTINUE
  constant (0.8) is the fallback without the table. Why: the constant was a
  rule standing where a count belonged (docs/idiom/rules-to-words.md).
- **pair_recall**, **pair_bar_recall**, **recall_sources** — the tune's
  memory at the two-bar pair, and where its echoes point (round 40,
  2026-10-28). `pair_recall`: what each two-bar group of the tune (a
  phrase's halves) is to the tune so far, the pair before's two cells
  again (`same`), a pair played earlier (`earlier`) or `new`, by the part
  and the song's echo habit, counted over the form's own parts (the
  writer draws there and plays a repeated part again); FFVI's mixed-habit
  tunes bring a pair back 0.19 of the time in their own parts, repeating
  ones 0.56. `pair_bar_recall`: the bar urn's shares (`melody_recall`'s
  kinds) counted over the bars inside NEW pairs only, since the bar urn
  over every bar includes the bars that come back as pairs and running
  both would echo twice. `recall_sources`: each echo (a bar whose cell
  was played before, not the bar before) by where it points: `section`
  (the same part of the form), `theme` (the tune's first phrase),
  `elsewhere` (another section); FFVI mixed 0.60 / 0.27 / 0.13, varied
  0.91 / 0.04 / 0.05. The melody writer (`writer.melody`): in a phrase
  that is neither the form's repeat, the theme's return nor an earlier
  phrase again, each pair of bars draws the pair urn first (`Urn` on
  `pair_recall`; the pair before's cells again, or an earlier pair from
  the pool the source word names, each bar re-rooted by `again`), and
  only a new pair runs the bar urn (`pair_bar_recall` where present,
  else `melody_recall`) and the half-bar urn inside it; an "earlier"
  draw at the bar or the pair takes its pool from a source drawn by
  `recall_sources` (a source with nothing in it gives its share to the
  others). The log: `pairs (pair_recall): same 1, earlier 1, new 10 over
  12 pairs drawn; echoes point (recall_sources): section 2, elsewhere 1`,
  and the phrase line's bars read `pair same` / `pair earlier`. Why: the
  owner heard no hook and no verse. Measured the same way on FFVI's 23
  themed tunes and the written themed songs (seeds 1-35), the written
  tune echoed as much as FFVI (0.71 of bars against 0.64) but by the bar:
  two-bar pairs heard earlier 0.19 against 0.40, whole phrases 0.18
  against 0.29, and a later section's bars found in an earlier,
  different section 0.21 against FFVI's 0.00 (B a reshuffle of A). After:
  pairs 0.28, whole phrases 0.25, sections sharing 0.10, distinct phrase
  heads 0.56 against FFVI's 0.62 (0.67 before). Open: 0.46 of the
  written recalls (theme returns, pairs, bars alike) come out with a cell
  the tune never played, `again` bending the strong beats to the chord,
  which is why a third of the written echoes are a rhythm with new
  pitches where FFVI has a tenth; and pairs inside the own parts 0.09
  against 0.18.
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
- **part_samples** — the sample a part's line plays (the melody, bass,
  accompaniment, harmony, arp; the counter's is `counter_samples` and
  `counter_pairs`', a second voice's `layer_samples`'), as the pack's id,
  by the part and the speed class of its fastest bar (round 42,
  2026-10-28). Drawn once a song before the writing
  (`whole.part_sample_for`), where the pack holds the sample; the pool
  rule (`best_sample`, the best range fit) chooses where it does not,
  logged. Why: the pool rule had put 0.73 of the written tunes on one
  string pad, whose wide played range wins every fit, where FFVI gives it
  0.31 of its tunes and spreads the rest over eight instruments and more;
  after, 0.40, with six instruments in the written forty.
  Since round 45 (2026-10-28) the draw is made over the samples the pack
  holds, the word's shares renormalised (`whole.part_sample_for`): a
  sample the pack lacks had sent the draw to the pool rule in 25 of 45
  plans (the pack holds 25 samples, 0.86 of the word's mass a part); the
  pool rule now chooses only where the pack holds none of the word's
  samples for the part. The better fix is in the pack build: importing
  the instruments FFVI's parts use (s9e298a0e24, s5d5fe2fd48, sb498c05828
  among the missing).
- **sample_ambitus** — the whole range a song played a sample over, lowest
  note to highest, by the sample (round 43, 2026-10-28). A tune's bound
  (the melody's and the counter's, `plan.bounds`) is the widest the game
  ever took its sample, the lowest low and highest high of the word's
  outcomes (`whole.ambitus_of`, not one song's draw: cut against the
  tune's own register, one song's draw had left Whole 38 the overlap of
  two songs' ranges), cut against the balance token's register for the
  part, which for the melody is its song's tune ambitus. The `ranges` word
  (the 10th to 90th percentile band) stays the bound of every other part.
  Why: bounded by the pad's home band (16 semitones), the written tunes
  spanned 15 where FFVI's span 21.5 (22 on that pad); after, 19.
- **tune_doubling** — in a bar of the tune that is not the theme's cell,
  which other parts play the same cell with it and how far from the tune
  (`theme_doubling`'s token: `bass:-24 counter:+0`; `none`), by the part
  (tune) and place (other) (round 44, 2026-10-28). Drawn a tune bar after
  the parts are written, in `whole.double_theme` beside the theme word:
  the drawn parts play the tune's bar at the interval in their register.
  FFVI doubles a non-theme bar in 0.23 of them; the written songs had the
  theme cell alone doubled (tune onsets doubled at the pitch class 0.22
  against FFVI's 0.40; after, 0.31).
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
