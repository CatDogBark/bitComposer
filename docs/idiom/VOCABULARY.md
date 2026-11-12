# The vocabulary: every table, what it counts, what it controls

The index and the wiring of every table, generated from the code, is [`vocabulary-map.md`](vocabulary-map.md) (`python tools/vocab_map.py`): each table's shape, where it is drawn and what it conditions. This page is the words themselves: what each counts and why it exists.

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
said otherwise. Counting code: `translate/rhythm/` and
`translate/phrases.py`; the plan: `translate/whole/`; the parts:
`translate/writer/`.

The words are grouped by where the writing draws them, in the order the song is written: the plan's one-draw-a-song words, the figure tables the parts' writers share, then the drums, the bass, the upper parts, the tune, the counter-line and the render; last, the words counted for the measures and never drawn. Under each word a line from the code gives its shape, the function that draws it and the tables it conditions (`tools/vocab_map.py`; the map page draws the same as a graph).

## Terms

- **unit** — one counted thing: a song, a bar, a phrase, a note, an onset. A table is a count of one kind of unit.
- **outcome** — what the unit was: a figure, a class, a token. The table's vocabulary is the set of outcomes it has seen.
- **values, conditionings, shape** — what a unit may be conditioned on (the part, the tempo band, the habit, the bar before's outcome); a table's shape is the ordered list of them, finest last.
- **context, backoff, floor** — a draw names the values it has; the table answers from the most specific context with enough songs behind it and backs off toward the part (Witten-Bell), never below its floor level (`floor_k`).
- **habit** — a song's way with a part, drawn once a song: a density tier (sparse, medium, dense) and a manner (varied, mixed, repeating; the bass's tones and octaves). Most figure tables are conditioned on it.
- **tier** — the density third of a habit; some words (the drums' entrances, the tune's grain) are conditioned on the tier alone.
- **token** — the balance word's outcome: one game song's whole band in one string, each part's weight, register, sounded share, voices, level, the voices beside its line, kind, sample and habit, then the top level, the loudness and the tempo class. A written song rides one token.
- **chain, previous** — a figure table conditioned on the bar before's outcome; the writer's bars form a chain through the game's.
- **mixture, urn** — a figure table drawn once a bar with the song's own bars so far: the same as the bar before, an earlier bar, or new, at the game's rates.
- **mask** — a second voice's or the counter's bar as which of the line's onsets it strikes with and which are its own (`second_figures`, `counter_figures`).
- **layer** — a voice beyond a part's line: its relation (lockstep, apart, alternating), its offset, its density and, since round 65, its sample and its notes over the line's; since round 90 the token says what it does beside which part stretch by stretch (a double, parallel, or its own line) and the writer follows.
- **lead** — the voice that carries the tune in a game song, decided by what is heard (round 64); every tune word counts on it.
- **own stream** — a draw on its own random stream (`whole:{seed}:name`), so a new word shifts no draw after it on the plan's stream.


## The song, drawn once: the plan's words

- **keys** — a song's key (tonic and mode). Drawn once; the plan's key,
  which the chords are spelled in and the tune's scale comes from.
  *`keys`: shape (part); drawn in _plan_once; conditions cadences, chords, contour_sizes, contours, endings, moves, peaks, phrase_shifts, relations.*

- **tempos** — a song's tempo to five beats a minute. Drawn once; sets the
  tempo band that conditions the habits and the length tables. Since
  round 54 a tempo outside the token's class is drawn again under it,
  and since round 137, where the token carries its song's own tempo
  (`tempo=fast:140`), one not within TEMPO_NEAR of that is drawn again
  among the class's tempos that are (`tempo_near`: by the word's own
  shares under the class, an own stream; the song's own tempo, kept
  inside its class, where the word has none so near). Why: a class is
  a third of the game's tempos wide, and a band written for 90 beats a
  minute (Edgar and Sabin's) played at 125.
  *`tempos`: shape (part, tempo); drawn in _plan_once, tempo_near; conditions bass, bass_habits, counter_figures, drums, drums-KSt, drums-c, drums-h, drums-o, echo_habits, habits, periods, rhythm, second_figures.*

- **sizes** — how many parts a song's form has. Drawn once; the fallback
  when no `letters` table can give the form whole.
  *`sizes`: shape (part); drawn in plan_form.*

- **length_habits** — a song's part-length habit (short, medium, long).
  Drawn once; conditions `lengths`.
  *`length_habits`: shape (part); drawn in plan_form; conditions cadences, part_entries, periods.*

- **top_levels** — a song's loudest part's median note level of full
  (the readings' scale, the SNES chip's voice volume over 128), to 0.05,
  one unit a song (round 52, 2026-10-28). Drawn once a song on its own
  stream (`Plan.top_level`); every part's share from the balance token is
  a share of it (`whole.note_level`), the TOP_LEVEL constant (0.85)
  standing without the word. Why: rendered through the same player as
  FFVI's converted songs, the written songs sat 5 dB hotter (-19.6
  against -24.5 dBFS over the first minute) because the loudest part
  always played at 0.85 of full where FFVI's sits at 0.2 to 0.4.
  *`top_levels`: shape (part); drawn in _plan_once.*

- **balance** — the song's band with each pitched part's weight, register,
  sounded share, voices, level and, where it holds two voices or more,
  its second voices' levels, and the drums' level with its kit, each
  piece's sample, level and, since round 75, the note the song strikes
  it at most, after the level's slot (`o=sf89f5aedfd@0.38@62`;
  `o=sid@@62` where the reading heard no level; nothing where it heard
  no note: a kit piece on a tonal sample, FFVI's "other" pieces in ten
  tokens of eleven, plays at the game's pitch and not the kit's one
  note, `render.kit_note_of`) (since round 70 the level and the sample
  fields are the LINE voice's, `readings.part_levels` and
  `part_sample_id`, so the line times each second-voice share reproduces
  every voice, and the kit's piece levels are in hundredths) (since round
  86 the sample field carries the range the song plays that sample over
  in the line voice, `s1d296a2572@32-52`, `rhythm.part_sample_field`, and
  each voice beyond the line its own sample's as a fourth slot of its
  entry, so a voice on the token's sample is written where its song
  played it, `Plan.sample_ranges`, `Plan.layer_ranges`, never in a range
  drawn for the sample from the other songs sharing it; the tune keeps
  round 43's wall, the sample's whole range)
  (`accompaniment=half:56-68:0.8:2:0.6:1.2 bass=half:28-40:0.3:1:1.0
  drums=::::0.2:::K=sbfe716b9b6@1.7,S=s1279e119a1@0.7,h=sd1c4c7ce33@0.2
  melody=main:64-84:0.9:1:0.7`).
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
  with two voices or more carries a sixth field too (since round 65 each
  entry is `level@sample@note share`, `1.3@s5a1fa4d5d3@0.33`: the voice's
  level over the line's, the pack id of the sample it plays most, its
  notes over the line's, so the second voice is the game's own sample at
  the game's density; FFVI's extra voices are on another sample in two
  accompaniments of three and every bass and play half to two thirds of
  the line's notes, where the written ones had taken the line's struck
  sample and played as much as the line, Whole 149's pad a riff over the
  tune): each voice beyond
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
  j beside the line at the token's entry j (since round 70 a doubling
  voice too, on the token's sample for that voice, `samples_for`'s
  `role:v`; it had played the line's level on the line's sample whatever
  the token counted, 163's counter second at 1.0 where Troops March on
  has it at 2.5 on sfd6accf98a); a part the token's song has as one voice,
  or a token without the field, keeps the `layer_levels` draw. One share
  a voice beyond the line rather than the second's alone: the token's
  voice count is the song's, and a third or later voice's share differs
  from the second's in 23 of FFVI's 52 (Gau 1.5 then 3.2 before the cap).
  Since round 86 each entry carries a fourth sub-field, where the song
  plays the voice's sample (`1.3@s5a1fa4d5d3@0.33@52-64`), and since round
  90 a fifth, what the voice does beside which part stretch by stretch
  (`rhythm.relation_words`: `dm-12x6>o`, the tune an octave under through
  the song's sixth bar and then its own line; `pc+4`, parallel with the
  counter's line a third up throughout; a kind, a part letter, semitones,
  the stretch's bars from the song's first bar as the pan word counts
  them, the last stretch open). A stretch is a run of notes on one sample
  (`roles.stretches_of`, blips under eight notes and eight beats folded),
  asked what it does beside each other voice (`roles.stretch_relation`): a
  double where 0.8 of its notes start with that voice's at the same pitch
  class (since round 96 a stretch's first or last bars that follow nothing
  bar by bar, two bars and eight notes or more, are a stretch of their own:
  Umaro's accompaniment voice reads `ox12>pm+24x5>o`, the tune two
  octaves up for five bars and then a run of its own, where the whole
  sample run had read as the parallel; 7 of FFVI's 128 words changed and
  no seed in 400 moved to another token), parallel where 0.8 start with that voice's at one generic
  interval over half the pairs (thirds alternate 3 and 4 semitones), its
  own line else, and either way only where it strikes with half that
  voice's notes within its span (a pad holding the root under a tune that
  lands on the root at its eight onsets follows nothing). The writer
  follows the word (`plan.stretched_notes`): the followed part's line again
  at the interval in the scale over those bars, the voice's own notes (its
  layer word's) over the rest, written after every line is in place; a
  voice of one own stretch, or of fewer than sixteen notes, has no word
  and takes the `layers` draw as before. With the stretches read, a voice
  that doubles the tune or runs parallel with it for half its notes or more
  is the tune's (role melody, `of` the tune's voice, from the counter and
  the chord parts; FFVI: 18 voices in 17 songs, read as counter-lines
  and chord parts before, Edgar and Sabin's and Dancing Mad's thirds, The
  Decisive Battle's and Metamorphasis's octaves), and the melody's line is
  the heard tune, not its busiest voice; 55 voices beyond a line carry a
  word in 38 songs. Kefka's three "counter" channels double its tune in
  octaves and thirds for whole stretches and the bass for another; read
  whole, they were a counter-line with two layers drawn from the pooled
  `layers` table, written as a three-voice block of their own at the
  song's loudest level over a one-voice tune (Song Check 72's The Sleeping
  Observatory).
  Since round 91 an eleventh field a pitched part whose line changes
  instrument (`rhythm.line_stretches`: `s77ca10e2568@52-64x6>sf89f5aedfd@60-80`,
  each stretch's sample, the range the line plays it over there and its
  bars from the song's first bar, the last stretch open; FFVI: 37 tokens,
  63 of 249 line voices, 25 tunes, 19 counter-lines, 12 chord lines, 6
  basses, two changes in three to another register, the centres 7
  semitones apart at the median, a stretch ten bars long). The writer
  registers each stretch's sample and bound (`render.samples_for`), writes
  the line over the union of its stretches' ranges, folds it by octaves
  into each stretch's range in its bars (`plan.fold_line`, the house
  fold) and plays each note on its stretch's sample (`render.sample_of`):
  Kefka's tune on its first instrument for five bars and its reed after,
  Overture's on three. The eighth field's sample stays the line's default,
  and a tune without the field keeps round 43's wall (the whole range the
  game took its sample over). Since round 92 the writers take a register
  a bar (`bounds_at` on the melody, the bass and the chord parts' line,
  `spans_at` on the counter): a line whose song changes instrument by
  stretch is written in each stretch's register, entering it by octaves,
  every move, recall and ending drawn inside it, so the fold after writing
  (`plan.fold_line`) has nothing left to move but the form's repeats
  (36 of 37 written tunes sat wholly inside their bounds in the
  measure; a counter's, a bass's or a chord line's stretch bound is often
  narrower than an octave and cannot hold every pitch class, as those
  parts' own narrow registers never could, and such notes sit where the
  nearest octave puts them);
  round 91 had written the line over the union of its stretches' ranges
  and moved it afterwards, bar by bar, which could break a phrase at a
  stretch line. Since round 104 a stretch's range is the ambitus of its
  own sample's notes: a blip of another sample folded into the stretch
  (`roles.stretches_of`) had widened it (Battle Theme's lead stretch read
  40-80 from one synth note at 42 before bar 1 where the lead plays
  64-79, and the written tune sat an octave under the lead, two thirds of
  its notes below the lead's lowest). The register field leaves such
  blips out too (`own_sample_notes`: Techno de Chocobo's tune had read
  28-80 from its effect notes on another sample where it plays 60-80).
  FFVI: 16 tokens' parts in 14 songs change, the register in 7, the
  stretches in 10, a voice's stretch sub-field in 4; the written tune on
  Battle Theme's token (seed 150) had two thirds of its notes under the
  lead's lowest and has 2 of 113 after.
  Since round 106 the token carries the riff as the song's own: a
  fourteenth field for a backing pitched part, its period and holds
  (`p2/83`: the lag in bars at which its bars repeat through the parts
  of the form that have one, the periods word's own reading, and the
  share of the bars inside it that play the bar a lag before again;
  Battle Theme's bass a two-bar riff held 0.83 in its riff section), a
  fifteenth for a chord part, how far its line rides the bass line
  (`b75/70`: the share of its onsets struck with a bass onset and, of
  those, the share at the bass's pitch class; Battle Theme's guitar
  0.75 and 0.70, which the layer words' relation reader, asking 0.8,
  had called neither a double nor a parallel), and a song-level
  `holds=0.53`, the share of its bar lines that keep the chord. The plan
  takes the period's lag and hold share where the pooled draw gives the
  part a period (the draws still made, the holds on an own stream), holds
  a chord at the song's share on an own stream (the chain's draw still
  made), and writes the chord part's line on the written bass's figure
  (`plan.ride_the_bass`: the bass's onsets and pitch classes in the
  line's register of the bar, on the bass's lengths, the voices beside
  the line seeing the riding notes) in the share of the form's parts
  the two shares' product gives (0.52 for Battle Theme: the half of the
  riff that is the bass an octave up), each new part drawn on an own
  stream, a repeated part as its source. Why: on Battle Theme's token
  the written bass and guitar shared a pitch class at 0.29 of their
  common onsets against the game's 0.69, the bass kept its main pitch
  class from bar to bar 0.25 against 0.74, and the owner heard every
  song on the token as a band whose players did not listen to each
  other.
  Since round 123 a chord part's token carries a twentieth field, where
  its line doubles the bass or runs parallel to it, stretch by stretch
  (`line_company_field`: the line voice's relation word, read by the
  form's parts since round 122, every stretch on anything but the bass
  as its own; `rdb+12x2>ox8>db+12x9>ox8>pb+12` for Battle Theme's
  guitar: the bass an octave up through A, its own riff through B, the
  bass again through C, the riff, and parallel to the bass an octave up
  to the end; six FFVI chord parts carry one). With it
  `plan.ride_the_bass` draws no parts: the line rides in the bars of the
  word's stretches on the bass and nowhere else, and plays the bass's
  notes at the stretch's semitones, moved by octaves only where that
  leaves where the token song plays the line's sample (the stretch's
  range, else the sample's); it rides once the line is held and folded,
  so the double stands as the bass's, and before the voices beside the
  line are written against it. Why: the rides field counts how much of
  the line strikes with the bass over the song, not where or at which
  octave, so the written guitar rode in parts the share drew and,
  folded into its register, sat at the bass's own pitch on 0.25 of the
  onsets they shared and an octave over it on 0.15 (Battle Theme: 0.04
  and 0.66); in the parts Battle Theme's band plays as one, the written
  guitar and bass were two lines.
  Since round 124 every part's token carries a twenty-first field, the
  parts of the form it sounds in by the form's letters, with where it
  enters and leaves inside one (`part_spans_field`: `eA+B2.0+D0.4`,
  through A whole, in B from its third bar, through D but its last four
  bars; a letter left out is a part of the form it rests through; a
  part sounds in a bar as the texture words count it, and its span runs
  from the first bar it sounds in to the last). 62 FFVI tokens carry it,
  the songs whose form the token carries: of 1058 cases of a part in a
  part of the form, 835 are whole, 120 enter late or leave early and 103
  rest through it. Where the plan's form is the token song's
  (`own_form`: the letters, as the loops ask) `whole.token_textures`
  sets the textures and every part's bars from the spans, a part of the
  form too short for an entrance played whole and a returning part
  copying its first statement; the `part_textures` and `part_entries`
  draws are made all the same, their lines unsaid, so no other draw
  moves, and the drums' own entrance draw is left out. Why: the form has
  been the token song's since round 113 and what sounded in each part
  of it a pooled draw by the part's place in the form, so a song on
  Edgar and Sabin's token, whose four parts play every bar, played its
  accompaniment and bass alone for fourteen bars and its tune alone for
  six (Song Check 100: "garbled noise, especially the beginning").
  Since round 125 a pitched part's token carries a twenty-second field,
  its line's onsets a bar by the form's letters (`section_onsets_field`:
  `nA6+B2!1+C4.5!7`, the median over the bars the line plays in the part
  of the form, onsets as the figure tables count them, and after a `!`
  its onsets in the part's last bar where that bar is a fill or a
  thinning as the `section_fills` word reads one); each voice beside a
  line carries the same as a ninth sub-field; and the kit's token
  carries each piece's hits a bar with the share of the part's bars it
  plays in (`kit_onsets_field`: `nAS28.5@100,c1@50+BS20@75`). FFVI: 129
  backing lines carry theirs over 422 parts of the form, 155 with a
  last bar of its own; of the 118 with two parts of the form or more,
  the busiest part is 1.5 times the sparsest at the median and at 1.5
  times or more in 66; 40 kits carry their pieces, 210 cases of a piece
  played through a part of the form, 52 in some of its bars, 13 rarely.
  Where the plan's form is the token song's, `whole.token_sections`
  sets `plan.section_onsets` (a backing part's line: the bass, a chord
  part) and `plan.kit_bounds`, and the writers take them through
  `habit_at_for` and `envelope_at_for`: a bar's figure is drawn under
  the density tier the section's onsets sit in and within the writers'
  own envelope of them (`writer.TIGHT`, half to one and a half times, as
  a part written over a game's bar keeps to that bar), the last bar by
  its own; a drum group's figure is drawn with each piece within its
  bounds (`kit_piece_bounds`: the envelope for a piece the song plays
  through the part, KIT_THROUGH; none to its most for one it plays in
  some bars, KIT_SOME; one at most for one it strikes more rarely; none
  for one the part never hears, whose hits are dropped if the draw's
  ladder lets them through), a group none of whose pieces sounds rests
  the bar, and a bar every group rests is the kit's to rest. Until
  round 138 the tune kept its own density and took the song's tier
  against its typical onsets a bar (DENSITY_STEP). Since round 138
  `plan.section_onsets` holds the tune's line too (the melody's, or the
  counter's in a band without one), its last bar its own where the token
  says a fill or a thinning, and every bar the tune's writer writes
  keeps within the same envelope (`keeps` in `tune.melody`): a new bar
  is drawn within it, asked neither the tier's running mean nor the
  `tune_grain` word, and among the bar table's bars that fit where no
  draw does (`parts.among`); a bar, a pair of bars or a half bar comes
  back, and a phrase's rhythm is answered, only where the bar still
  keeps; the letters' phrases as `phrase_letters` says below. Why: a
  medium tune is four to six notes a bar whatever the part of the form,
  and the written Blackjack's tune played 2.8 notes a second where the
  game's plays 1.4, seven notes a bar through a part of the form the
  game plays three in. The counter's last bar beside a tune,
  and the last bar of the first voice beside any line, take the song's
  fill or thinning. The `section_densities` and `section_fills` words
  are not drawn then (they draw on their own streams). Why: a part's
  habit (round 62) says how busy it is over the song, and where it
  thins or fills was the pooled words' draw by the section's place: the
  written Locke's snare ran through A and stopped for seven bars of B
  where the game's plays in fourteen bars of sixteen, its
  accompaniment played two notes a bar where the game's plays five or
  six, and
  the written Edgar and Sabin's accompaniment, drawn a tier denser,
  played seventeen notes a bar in each of three voices where the
  game's plays two to six.
  Since round 126 a bass's voice beside its line carries a tenth
  sub-field, what it does beside the line as the `layers` word names it
  (`layer_word`, the word's own outcome for the song: `vapart_+0_denser`,
  `vdoubling_+0`). FFVI's fifteen two-voice basses: a line of its own in
  twelve (in the line's register in six, busier than the line in
  five), the line again on a second sample in two (Returners, Overture
  part 3), alternating in one (Fanfare). The plan takes the word in
  place of the `layers` draw for the voice, the draw made all the same
  so no other draw moves (`BASS_LAYER_KINDS`: a word the bass writer
  writes; an alternating bass keeps the draw), and a second voice that
  doubles the line is written last (`whole.double_bass`): the line as
  finally played, after the theme band, the form's repeats and the
  bass's last pass, again at the word's interval. Why: the pooled draw
  gave a bass a doubling or an alternating as often as not, and the
  bass writer wrote a second voice only for a line of its own, so the
  second channel was silent in seven of Song Check 100's 68 songs;
  Gogo's bass is a held line under a busy one, and the written bass
  played the held line alone, a note a bar.
  Since round 111 a chord part and the bass carry a sixteenth field, the
  line's chord-tone profile (`line_tone_profile`: `t46/2/8/31/2/11` for
  Battle Theme's guitar, `t33/8/17/19/3/20` for its bass, the share of the
  line's notes on the chord's root, third, fifth, seventh and sus and off
  the chord, in hundredths; FFVI: 56 accompaniments, 58 basses, 10
  harmonies and 2 arps carry one). The chord-part writer and the bass
  writer hold the line's chord tones to it (`parts.profile_tone`): a
  chord-tone onset whose class, with the note counted, runs over its share
  by PROFILE_MARGIN takes the chord's own tone most under its share
  instead; the off-chord onsets stay the tone figure's and the passing
  marks'. Why: the voicings, the motion and the bass's marks said which
  chord tones a line walks, and none knew the token song's: FFVI's
  accompaniment lines play the seventh on 0.01 of their notes at the
  median and Battle Theme's riff on 0.30 (one other FFVI accompaniment
  reaches 0.2), so the written lines on its token played fifths and thirds
  and never the seventh, and the synth struck with them, whose landings
  the interval word conditions on the guitar's tone, drew from the cells
  where the game's synth leaps (Song Check 93).
  Since round 112 the token carries a song-level `shapes=` field, the
  song's chord shapes (`chord_shape_profile`: the share of its beats under
  each shape the reader heard, in hundredths, the largest first,
  `shapes=maj7:45/5:17/sus4:12/m:9/7:8/m7:3/maj:3/dim:3` for Battle Theme;
  67 of FFVI's 68 tokens carry one). `plan_chords` holds a changing
  chord's quality to it (`reshaped_name`): a quality that, with the bar
  counted, runs over its share by SHAPE_MARGIN gives way to the profile's
  quality most under its share on the same degree (`with_shape`: IV to
  IVmaj7, V7 to v), and a held or repeated chord keeps its quality. Why:
  the chord chain drew its qualities from the pooled chords word, and
  Battle Theme's reading has a seventh chord on 0.56 of its beats where
  FFVI's median song has one on 0.08 (7 songs over 0.3), so the songs
  written on its token had one on a tenth of their bars, the guitar held
  to the riff's chord tones (round 111) had no seventh to play, and the
  synth struck with it never saw the tone the game's synth sits still
  over.
  Since round 127 the token carries a song-level `quals=` field too, the
  qualities each degree of the song's key has (`chord_degree_shapes`:
  for each root the reader heard for DEGREE_BARS bars or more, by its
  semitones over the tonic, the shapes it has on DEGREE_SHARE of its
  beats or more with their share, the most heard first;
  `quals=1~maj7:92+0~5:44` for Battle Theme, whose major sevenths sit on
  its flat second; 67 tokens carry one, 182 degrees, 131 of them with
  one quality on 0.6 of their beats or more: the major triad 43, the
  power chord 40, minor 32, the major seventh 5). Once the chain is
  drawn (its draws, its holds and the profile's hold as before, so no
  other draw moves) `hold_chord_shapes` gives each chord as drawn one
  quality: its degree's own in the token song where the degree has one
  (DEGREE_OWN); else, of the qualities the profile's hold gave it bar
  by bar, the one it took in the most bars among those the song gives
  the degree and those that keep the chord's own third (`chord_third`:
  a major chord is not made minor, nor a minor one major; a shape with
  no third suits either; a minor key's dominant may be either), the
  name as drawn at a tie; a held bar follows the bar before, a returning
  part its first statement. Why: the profile's hold decides bar by bar
  from the shapes so far and knows no degrees, so one drawn chord came
  out in two or three qualities in a song (Gogo's G minor, G major, G5,
  G7 in four bars), a chord's third flipped on its own degree in 0.12
  of the written songs' chord changes against 0.06 of FFVI's, and
  Battle Theme's major seventh sat on the written tonic.
  Since round 128 the harmony's loops (`cycle=`, round 121) are read by
  the bars' roots: `chord_bar_keys` gives a bar the root of the chord at
  each of its beats, without the shape. 55 FFVI tokens carry a cycle
  where 48 did, over 140 parts of the form where it was 114 (a one-bar
  harmony in 110, two bars in 23, four in 7). Why: with the shape in
  the key a bar on the figure's root read as off the figure wherever
  the reader heard its quality another way, a triad one bar and its
  fifth alone the next; and since round 127 a written chord keeps one
  quality, so a bar on the figure takes the first bar's chord whole.
  Since round 129 the bass's token carries a twenty-third field, how
  often its line strikes a bar's first beat on the chord's root
  (`bass_downbeat_field`: of the bars the line strikes on the first
  beat, the share where its lowest note there is the root of the chord
  the reader hears, in hundredths: `d73`; 55 FFVI basses carry one, 0.78
  at the median, ten under a half and seventeen at 0.9 or more). The
  bass writer holds the line to it as it writes (`writer.bass`,
  `downbeat`): a bar's first-beat note off the root, where the share
  with the bar counted runs under the song's, moves onto the root in
  the octave nearest where it was, before the line's loop copies the
  bar and before the parts written after the bass read it. Why: the
  line's tone profile (round 111) holds how many of its notes are
  roots over the song and its continuity (round 114) pedals a bar on
  the bar before's pitch class; neither says where in the bar the root
  falls, and the written bass was on the plan's root on the first beat
  in half of the bars and off the chord in a sixth.
  Since round 133 it carries a twenty-fourth, how often its line
  strikes a bar's first beat at all (`bass_first_beat_field`: of the
  bars the bass plays in, any voice of it, the share struck on the
  first beat, in hundredths: `f93`; 63 FFVI basses carry one, 0.93 at
  the median, six under a half and 37 at 0.9 or more). The bass writer
  asks a new bar of its line
  the first beat while the share of the bars written so far, this one
  counted off it, runs under the song's (`_free_figures`, `first_beat`):
  the bar's envelope asks it, with the band's lock and then without,
  before the bar's other filters are loosened, and where no draw
  strikes it the figure is one of the known figures that do, by the
  table's own shares in the bar's context (`among`). Why: a
  free-written bar asks no first beat (`free_envelope`: the habit
  conditions the table), and since round 125 a bass's strikes a bar are
  its token song's by the part of the form, so a bar drawn off the
  first beat within them, then played again where the song's bass
  loops (round 121), put a whole part of the form off the first beat.
  Since round 135 the chord parts carry the same field (`first_beat_field`,
  the bass's reader for any backing part: 55 FFVI accompaniments, 0.83
  at the median and twelve under a half; 14 harmonies, 0.99; 2
  arpeggios) and `writer.upper` asks its line's new bars the same way
  (`first_beat`); the plan keeps a share a part (`first_beats`). Why:
  the chord parts' bars are drawn as the bass's were, within their
  strikes a bar with no first beat asked, and the written Terra's
  accompaniment struck the first beat in 17 of its 44 bars where the
  game's strikes it in 0.99.
  Since round 113 the token carries the song's form as a song-level
  `form=` field (`form_field`: the parts' letters in order, a returning
  part by the letter it returns to; `form=ABCBD` for Battle Theme, a two-
  bar A, B, C, B again, D; 67 of 68 FFVI tokens carry one), and the plan
  rebuilds its form from them once the balance is read: the form's own
  draw stands, so no other draw moves; each part takes the token's bars (a
  returning part its first statement's, played whole), a form past the
  bars asked is cut as any and one short of them leaves the draw standing;
  the loop's part is drawn again for the new form. Why: the form had been one of the
  game's forms whole from the pooled letters word, right in the aggregate
  (34 of FFVI's 67 songs repeat a part and 18 bring one back after
  another; 42 and 20 of sixty written songs) and wrong for the song, so
  four of the five Song Check songs on Battle Theme's token never came
  back to what they had played.
  Since round 117 a chord part's and the bass's token carry an
  eighteenth field, the line's step profile (`line_step_profile`:
  `j63/24/13`, the share of its note-to-note moves that repeat the pitch,
  step within a whole tone, or leap a minor third or more, STEP_CLASSES;
  Battle Theme's guitar 0.63/0.24/0.07... read `j63/24/13` as its reading
  rounds), and `plan.hold_line_steps` holds a chord part's line to it once
  the line is written and rides the bass, so every move counts as the
  reader counts them: a move whose class, the note counted, runs over its
  share by STEP_MARGIN gives way to the class most under, `same` the note
  before again, `step` the chord's tone within a whole tone of it (the
  scale's where the chord has none), a leap never forced; the voices
  beside the line see the held note. Why: the motion word (`line_motion`)
  says how often a line's pitch changes, not how far, so a chug with a
  semitone neighbour read "mixed" like a walking chord-tone line and the
  written guitar leaped between chord tones on 0.34 of its moves, a
  melodic voice driving the song where the game's is a rhythm part under
  it (Song Check 96).
  Since round 130 the melody's and the counter's token carry their own
  profile in the same field, of four classes (`tune_step_profile`:
  `j11/58/19/12`, the share of the line's moves that repeat the note,
  step within a whole tone, move a third, or go a fourth or more,
  TUNE_MOVES; 65 FFVI melodies carry one, 0.12, 0.56, 0.15 and 0.10 at
  the median, Locke's 0.44 repeated notes and 0.05 far, The Decisive
  Battle's 0.32 far; 50 counters). The tune writer keeps the written
  tune to it as it writes (`writer.melody`, `move_profile`): a drawn
  move (`draw_move`) is of no class the tune, its recalled bars counted,
  is over its share of (`third_over`, `far_over`), where a move of
  another class fits, and under its shares the moves fall as the table
  and the chord's share have them; the repeated note takes the song's
  own share in place of the pooled `repeat_rates` draw (the draw is
  still made); and a bar played again (`again`) that would enter by a
  move of a class the tune is over is weighed, one for one, with the
  chord and the over-share holds in its one move within a third. Why:
  `step_habits` says stepwise, mixed or leaping and conditions the moves
  table, and the table carries the game's own moves, but the chord-tone
  hold on the beat then drew the line to a chord tone a third or a
  fourth away where one lay a step off: the written tunes went a fourth
  or more onto a beat in 0.28 of their moves there against FFVI's 0.14
  and stepped there in 0.48 against 0.67.
  Since round 136 the melody's and the counter's token carry a
  twenty-fifth field, the line's shortest usual note
  (`tune_shortest_field`: how long the note at the fifth percentile of
  its notes sounds, SHORT_NOTE, in milliseconds to the nearest ten:
  `m150`; 65 FFVI melodies carry one, 120 ms at the median, seventeen
  under 80 ms and 27 at 150 ms or more; 51 counters, 130 ms). The plan
  keeps it (`tune_shortest`) and hands the writers its length in beats
  at the song's tempo (`shortest_beats`); a tune note then sounds its
  gap's share (`tune_sounds`, round 98) or the song's shortest usual
  note, whichever is longer, and never past its gap (`tune.sounded`).
  Why: the share is one pooled draw for a detached note whatever its
  gap, so a detached eighth at 0.3 of its gap sounded 62 ms at 145
  beats a minute, where the game's Terra's tune sounds no note under
  152 ms.
  Since round 140 the tune's gap is measured across the bar line, as
  the counter-line's and the bass's are and as the `values` and
  `tune_sounds` words count it (`rhythm.tune_gap`: to the line's next
  note where that starts in the note's bar or the next, else to its
  bar's end). A bar's last note runs to the next bar's first onset,
  so a note held before a bar that opens with a rest sounds over the
  bar line: the game's Terra sounds 0.24 of its tune's notes past
  their bar's end, and the written one had none. The last note of a
  part of the form played again sounds the share of its gap it sounds
  in the part it repeats, measured to the note that follows the
  repeat (`copy_repeats`).
  Since round 141 the melody's and the counter's token carry a
  twenty-sixth field, how the line sounds its notes by the gap to the
  next (`tune_lengths_field`, the gap as `tune_gaps` measures it):
  after an `h`, an entry for the whole line and one for each gap
  class (`GAP_CLASSES`: under half a beat, half to one, one to two,
  two to four, four and more), each `held~share~share`: the percent
  of the notes held (sounding 0.75 of the gap or more), then the
  median share of its gap a held note sounds and a detached one (to
  LENGTH_BIN, 0.05; `-` where the line has none of the kind); a class
  of fewer than LENGTH_NOTES (four) notes is `-`.
  `h100~0.80~-/-/100~0.80~-/-/100~0.95~-/100~0.95~-` is Terra's tune,
  every note held; `h41~0.90~0.30/55~0.85~0.35/0~-~0.20/62~0.95~0.30/31~1.00~0.15/-`
  Gogo's, its eighths all cut to a fifth of the gap; 116 of the 118
  melody and counter tokens carry one. The plan keeps it
  (`tune_lengths`, read by `lengths_of`) and the tune's and the
  counter-line's writers sound a note by it (`tune.own_length`): held
  at the song's rate for its gap's class (the whole line's where the
  song has too few notes of the class), drawn on the lengths' own
  stream and kept within a note of the song's share of the class's
  notes so far; sounding the song's share for its kind at the class,
  at the nearest class that has one where the song has none there
  (the longer of two as near), the whole line's where no class has.
  The pooled `values` draw is made all the same and the `articulation`
  and `tune_sounds` words are drawn as before, so no draw moves; they
  still sound a voice beside a line, a second counter-line and a line
  whose token carries no field. The render does not raise such a
  line's notes to its sample's floor (`score_of`). Why: the pooled
  words give a tune one habit a song and one share for a detached
  note whatever its gap, and the game's tunes differ song by song and
  gap by gap: Terra's holds every note, Locke's a quarter of its
  eighths and half its quarters and every longer note, and a cut note
  before a beat or more sounds a fifth of the gap at the game's
  median where the pooled share is two fifths.
  Since round 142 a chord part's token carries a twenty-seventh
  field, how often it sounds again the pitch classes it played on a
  root before (`tones_kept_field`): of its bars with an earlier bar
  on the same root within eight (TONES_BACK) in which it sounds, the
  percent that sound one of those bars' pitch classes again (a bar's
  set: the classes with 0.15 of the beats the part sounds in it,
  `bar_tones`; a bar's root: the bass's most-sounded class,
  `bass_roots`, the one reading of a root to be had alike of the
  game's song and of a song being written), then of those the
  percent that sound the bar before's (the rest match a bar further
  back: a figure of two bars or more), after a `c`: `c75/82` for
  Terra's accompaniment, `c60/25` for Locke's; none under eight such
  bars. 49 of FFVI's 57 accompaniment tokens carry one, 10 of its 16 harmony tokens and 1 of its 3 arp tokens. The plan keeps it (`tones_kept`) and holds each
  chord part to it once the tune and the counter-line are written
  (`hold_chord_tones`), counting as the token counts and the song as
  it will be played (a part of the form played again counts with the
  bars it plays, and is left as it is): while the part's share over
  the whole song is under the song's, a bar that sounds none of the
  pitch classes of the earlier bars on its root takes voice by voice
  the notes of one of them that is on the plan's same chord in its
  part of the form and has its rhythm: the bar before's while the
  share of the kept bars that are the bar before's runs under the
  song's, else a bar further back that sounds another set (a figure
  of two bars). A bar on its loop's figure, a bar the line rides the
  bass in and a bar that would then sit a semitone from the tune
  stand, and a bar with no earlier bar of its rhythm stands. Why: a
  chord part's tones are drawn a bar at a time (the voicing, the
  motion's walk along it, the tone figure, the profile's hold), so
  under one chord two bars seldom sounded one set of pitch classes,
  and the game's accompaniments do in three such bars of five.
  Since round 143 the counter-line beside a tune is written to its
  token's own words where it had been to the pooled ones. Its bar's
  mask (the `counter_figures` word) is drawn within its line's onsets
  a bar by the form's letters, the token's twenty-second field
  (`counter_mask`: half to one and a half times them, and the part of
  the form's bars so far kept at them within `MASK_SLACK`), the word
  drawn again on the bar's own stream. Its note is drawn among the
  notes its span holds (`beside_pitch`'s `span`), the interval and
  the move weighed as they sound. Its moves of a fourth or more are
  held to its line's share, the token's eighteenth field. Why: the
  mask word is pooled over the game and knew nothing of the song's
  counter-line's pace (the written Locke's ran 4.4 notes a bar where
  the game's plays 2.8, a quarter of its moves a sixteenth apart
  where the game's has none), and a note drawn outside a span under
  an octave came back in at its other end, a seventh for a step.
  Since round 144 a chord part's token, and the counter-line's in a
  song with a tune, carries a twenty-eighth field, how often the part
  comes back with its lead (`together_field`): of the bars in which
  its lead (`lead_of`: the bass for a chord part, the tune for the
  counter-line) plays an earlier bar again note for note, the
  nearest within eight (`bar_cells`, `bar_back`: a line's bar is the
  onsets and the pitches of the notes begun in it), and the part
  plays in both, the percent in which the part's line plays that bar
  again too, after a `w`: `w57` for Terra's accompaniment, `w60` for
  its harmony; none under four such bars (TOGETHER_BARS). 36 of FFVI's 57 accompaniment tokens carry one, 10 of its 16 harmony tokens, 1 of its 3 arp tokens and 30 of its 52 counter tokens.
  The plan keeps it (`together`) and holds each such part to it once
  the tune and the counter-line are written (`hold_together`),
  counting as the token counts and the song as it will be played:
  while the part's share over the whole song is under the song's, a
  bar in which its lead plays an earlier bar again and the part
  plays another takes the part's earlier bar whole, every voice with
  its onsets and lengths, where the plan's chord is the same under
  both, the bar keeps within the part's own onsets for its part of
  the form, and it sits a semitone from no more notes over it (under
  it, for the counter-line) than the bar's own did. A bar on its
  loop's figure and a bar the line rides the bass in stand. A chord
  part is then held to its pitch classes on the root (round 142).
  Why: in the game a bar comes back whole, and the written parts
  each came back by their own draws, so under a tune's bar played
  again the band played another bar.
  Since round 147 the melody's and the counter's token carry a
  twenty-ninth field, where in the beat the line's notes fall
  (`tune_places_field`): after a `p`, the percent of its onsets on a
  quarter of the beat, on a third or a sixth, and finer than either
  (`FINE_PLACES`; `beat_place`: an onset is on a place within
  PLACE_NEAR, 0.03 of a beat, of it, counted where it is played and
  not where the reading's grid puts it; notes struck together are one
  onset). `p0/0/0` is Locke's tune and Terra's, on the beat and the
  half beat alone; `p42/3/3` Spinach Rag's; none under sixteen
  onsets. 65 of the 66 melody tokens carry one and 51 of the 52
  counter tokens; 35 tunes play on no quarter of the beat and 14 on
  nothing finer than the half beat. The token also says its song's
  feel where that is not duple (`feel=triple`, `cells.song_feel`: 14
  of the 68 songs). The plan keeps both (`tune_places`, `token_feel`)
  and, where the song is written in its token song's feel, hands the
  shares to the tune's writer (`own_places`, `held_places`: in a
  triple feel the third is the feel's own division of the beat and is
  not held). Each share is a ceiling on the written tune over the
  song (`keeps_places`: of its notes so far, or of the least it will
  play where that is more, so a figure its song opens with need not
  wait; a bar in a part the form plays again counts once for each
  time). A bar is written as it was, new or come back, and where it
  would put the tune over a share its notes are moved onto the
  nearest rhythm the table knows that keeps the places
  (`tune.on_places`): as many onsets as the bar has notes, the notes
  in their order, each onto the beat, the half beat or a place it was
  on (`adds_places`), with the least moving in time; of the rhythms
  within a quarter of a beat of the nearest (PLACE_SLACK), the one
  that brings the fewest notes onto a beat off the chord, then the
  one that bends the figure least. A note is left out only where no
  rhythm of as many onsets keeps the places, and never the bar's
  last. The counter-line beside a tune is held through its bar's mask
  (`counter_mask`'s `placed`): the nearest mask the table knows that
  keeps the places (the same of the tune's onsets struck with, as
  many of its own), else the word drawn again on the bar's own
  stream. No draw is made for a tune's bar, so a tune the places
  leave alone is the tune it was. Why: the `rhythm` table is pooled
  over the game, and a bar kept its song's count of notes (round 138)
  and not where in the beat they fall: of 276 tunes written in their
  token song's feel, 133 ended over their song's share of a place and
  79 played on a quarter of the beat where their song's tune never
  does.
  Since round 145 the kit's bar tables are kept a second time with a
  song the reading has at half its speed counted in double time
  (`packtables.DOUBLE_TIME`: `drums@2`, `drums-KSt@2`, `drums-h@2`,
  `drums-c@2`; a table that comes out as the one as read is left out,
  the other sounds'), and a song whose token is counted in double
  time (round 131, `Plan.beat`) draws its kit from them. Why: such a
  song's kit bars were asked of tables that hold its token song at
  half speed, its snare's march left out as rolls, so the written
  Locke took a fast song's bars within the strikes its token asks
  and never its own march.
  Since round 131 a song the reading has at half its speed is counted
  for its token in double time (`token_song`): `half_time` says which
  (a song in the slow tempo class one of whose kit voices plays in
  HALF_TIME_STEADY of the song's bars or more and strikes more than
  HALF_TIME_HITS times, the writers' sixteen, in HALF_TIME_SHARE of the
  bars it plays or more, on a grid that halves: Locke at 70 beats a
  minute and Blackjack at 72), and `readings.double_time` gives the
  song as it reads at twice the tempo: every time in beats doubled, a
  bar of the song's meter two bars and a shorter one one, the bars
  numbered on with the form's parts and the loop's bar, the grid's
  division halved; the reading itself is not changed, and the other
  tables count the song as read. The token of such a song says
  `tempo=fast`, its form in twice the bars (`form=A8A8B16` for Locke),
  every count by the bar the double-time bar's (the snare `S14.5@100`
  where it was `S28.5@100`), and a song-level `beat=2`, on which the
  plan lets the token song's form run to twice the bars asked
  (`own_max`): the same music in twice the bars. Why: the kit's bar is
  written sixteen strikes to the bar at most, and a snare that keeps a
  march's sixteenths at 140 was read as thirty-seconds at 70, so the
  token asked a slow song with a kit no writer could strike, and the
  written Locke ran at 80 with its snare at the cap.
  Since round 132 the token carries, with its form, the part of it the
  song's loop returns to (`loop_part_field`: a song-level `loop=1`, the
  index of the form's part that holds the loop's bar, 0 the first; none
  without a form or a loop read), and where the plan's form is the
  token song's own the loop's bar is that part's first bar, set once
  the chords are drawn: the pooled `loop_parts` draw is still made and
  the chain's draw at its bar stands, so no other draw moves. Why: the
  form was the token song's (round 113) and the loop's part the pooled
  word's by whether the form opens with an intro, right for half of
  the songs on their token song's form; the written Edgar and Sabin
  came back to its last four bars.
  Since round 121 the token carries each backing voice's loops by the
  form's letters: a part's nineteenth field for its line and for the kit
  (`loop_field`: `lB1~100`, in B a one-bar figure on every bar the voice
  plays), a voice beside the line's as its eighth sub-field
  (`lB1~75!3.7`: on three bars in four, off it in the part's bars 3 and
  7 counted from 0) and the harmony's as a song-level `cycle=` word
  (`chord_cycle_field`: `cycle=B1~88!7`). A voice's bar is read note for
  note (`voice_bar_keys`: each note's place in the bar with its pitch, a
  kit hit with its sample, a bar of the harmony the chord at each beat);
  the figure at a length of 1, 2 or 4 bars is the bar the voice plays
  most at each place of it, twice or more (`loop_of`: a longer figure
  only where it holds LOOP_GAIN more of the bars, a loop where the
  figure holds LOOP_SHARE of the bars the voice plays in a part of
  LOOP_BARS or more), and the bars off it are named (`loop_breaks`).
  Where the plan's form is the token song's (`Plan.loops`, by the
  letter; none where the form's draw stands), `plan.hold_loop` makes a
  bar on a figure the figure again, the first such bar the voice plays
  at that place of the figure copied whole, pitch and place and length:
  the kit's once its hits are drawn, the bass's and a chord part's
  line's once the line is held and folded, before the voices beside it
  are written against it, and each voice's beside it once it is
  written. A bar the token song has off its figure and a bar the voice
  rests in stay as written. `plan_chords` gives a bar on the harmony's
  figure the chord of the first bar at its place once every bar is drawn
  as before, so no other draw moves; the lines the loop holds come on
  top of the song's chord-hold share. The passes after the writing leave
  a figure's bars as they are: the theme band, the hand-offs
  (`_on_figure`) and the bass's last pass with the voices riding it
  (`hold_bass_pitch`, `held`). Why: the periods word (round 30) reads
  an upper part's onset pattern and the bass's chord-tone marks, so a
  held bar was a bar on the same rhythm whose notes the writers drew
  again, and every hold since (the chord-tone profile, the bass's
  continuity, the steps, the cell) kept a share over the song while no
  bar came out twice. FFVI's backing voices loop in 0.45 to 0.69 of the
  parts of the form they play four bars or more in; the written ones
  did in 0.05 to 0.37 (`docs/LIMITS.md` for what the loop does not yet
  do).
  Since round 114 the bass's token carries a seventeenth field, its pitch
  continuity (`bass_continuity_field`: the share of its bar lines across
  which the bass keeps the bar's main pitch class, in hundredths, `k58`
  for Battle Theme; FFVI's basses 0.30 at the median), and the bass holds
  its line to it twice: the writer (`bass`, `continuity`), while the share
  runs under the token's with the bar line counted, realizes a bar on the
  bar before's main pitch class as a pedal, the figure's marks from it as
  from a root and the fewest notes moved onto it until it is the bar's
  main pitch class (`realize`'s `root_override`, `pedal`: a passing mark
  first, then the class most over the song's chord-tone profile, the
  earliest first, the classes written kept counted); and `hold_bass_pitch`
  walks the line as finally played, after the theme band, the hand-offs
  and the form's repeats have rewritten bars of it, pedaling bars the
  writer's own notes still stand in where the share runs under, a chord
  part riding the bass moving with it and the voices its relation words
  have following the line moving the same. And `parallel` draws a line
  note that is off the chord but on the pitch class the written bass
  sounds under it as over the chord's root: a part riding the pedal is on
  the riff's root whatever the chain's chord, and drawn as "other" the
  synth struck with it had taken the cells where Battle Theme's synth
  leaps over the riff's neighbours. Why: the bass had walked the chord
  chain's roots, keeping its pitch class across 0.29 of its bar lines at
  the median, where Battle Theme's riff hammers one pitch under the
  changing chords the reader hears in its chromatic neighbours and keeps
  it across 0.58; the five Song Check basses on its token kept 0.17 to
  0.41 and keep 0.53, 0.53, 0.50, 0.39 and 0.50 now.
  And each
  layer entry carries a sixth sub-field, the
  voice's own instrument by stretch (`stretch_word` with "~" between a
  sample and its range: `s605f200105~56-72x14>sf89f5aedfd~60-68`; FFVI:
  32 voices in 22 songs): `samples_for` registers each stretch's sample
  (`samples["part:v:stretch:i"]`) and `sample_of` plays the voice's note
  on it; the voice's register stays its relation's.
  Since round 107 the relation word has a third kind, struck with
  (`w`): a voice that strikes with another on 0.8 of its notes
  (`roles.with_relation`) but at no one interval, with the line
  (`wl+19`) or with a sibling voice beside the line, named by its rank
  (`w1-7`); a double or parallel of a sibling names the rank too. Battle
  Theme's synth is two voices struck as one on the riff's accents, a
  fourth or a fifth apart by the chord (78 fifths, 64 fourths, 25
  thirds of 202 onsets), the lower with the guitar on 0.89 of its notes
  at chord tones an octave and more up; the relation reader's one
  generic interval had called each its own, and the layers table then
  drew them anything a seed at a time (a double of the riff a third
  under, a line in the bass register). The writer plays a struck-with
  voice on the followed voice's onsets, thinned by the second_figures
  word, placed on the chord by the parallel_intervals word, each note
  the voice's share of its gap (`plan.struck_with`); a double or
  parallel of a sibling follows the sibling's written notes. FFVI: 39
  own-reading stretches of voices beside a line strike with the line, 9
  with a sibling, 71 stay their own.
  Since round 122 what a voice does is read part by part of the form
  (`_split_by_parts`): a stretch is a run of notes on one sample, so a
  voice on one sample all song had one reading, and each part of the
  form the stretch plays eight notes or more in (roles.STRETCH_NOTES)
  is now asked on its own, the tune's voices first of those it strikes
  with equally (LEAD_ORDER), a part of fewer notes taking its
  neighbour's reading; parts alike run together, a stretch whose parts
  all read alike stays whole, and a song whose token carries no form is
  read whole as before. Battle Theme's synths: `wl+19x27>pm+12` and
  `w1-7x10>da+12x9>w1-7x8>pm+4`, struck with the guitar's riff through
  B and C (the lower doubling the guitar an octave up through C) and in
  D parallel to the tune an octave and a third over it, every note on a
  tune onset; read whole they were `wl+19` and `w1-7`. The writer had
  left a struck voice's stretches on another part's line as the voice's
  own notes; they are written once every line is
  (`plan.late_stretch_notes`), the line again at the interval, and
  folded into where the token song plays the voice's sample, the struck
  stretches standing as they were written in place. FFVI: 58 of 157
  voices beside a line read differently, 99 carry a word (88 before);
  the interval word is counted over the stretches as now read (7,372
  onsets in 50 songs; 8,281).
  Since round 116 the struck sub-field carries a ninth part, the voice's
  cell (`...~4.9~0.49~0.49`: of its notes with a note of its own at the
  same position of the bar before, the share that sound that note's
  pitch again), and `struck_with` repeats the cell to it: a stab with a
  stab at the same place of the bar before takes that stab's pitch while
  the share so far, this stab counted, runs under the token's by
  STRUCK_MARGIN, and the interval word's landing otherwise. Why: Battle
  Theme's synth hammers one cell (C D E F) bar after bar, the hook, and
  the written stabs, each landing drawn anew by the interval word, changed
  their pitches every bar, loud and never the same (Song Check 96).
  Since round 115 the struck sub-field carries an eighth part, the
  voice's sounding share (`w0.73~0.7~0.2~0.9~-~-~4.9~0.49`: the beats it
  sounds, each note to the line's next onset at most, over the beats of
  the bars it strikes in), and `struck_with` holds the stabs to it: a
  stab whose length by its gap class would put the share so far, this
  stab counted, over the token's by STRUCK_MARGIN sounds the token's
  shortest class share of its gap instead, a stab. Why: the gap-class
  shares are Battle Theme's, but its riff is dense and its stabs almost
  never fall in the one-to-two-beat class where it held 0.9; a sparser
  written line put most of the synth's gaps there, and Journey of the
  Quarry's synth sounded 0.68 of its bars' time at 0.9 beats a note, a
  held organ tone on a brass sample that holds till key-off, where Battle
  Theme's sounds 0.49 at 0.19 (Song Check 96).
  Since round 108 a struck-with voice carries a seventh sub-field, how it
  strikes (`_struck_text`: `w0.73~0.7~0.2~0.9~-~-~4.9` for Battle Theme's
  synth): the share of the followed voice's onsets it strikes, its sounded
  share of the part's line's gap by gap class (a stab's length measured
  against the line it rides, as the line's own lengths are in field 2,
  never against the voice's own next stab) and its longest note in beats.
  The writer holds the `second_figures` mask toward the share (under it a
  bar strikes every followed onset; over it a mask that thins nothing is
  drawn again, `STRUCK_TRIES` times), takes the voice's share by the
  line's gap where the token has the class, and lets no stab ring past the
  longest. Why: measured against its own next stab, a stab's gap ran to
  bars wherever the part rested or the mask thinned whole bars, and the
  pooled second voice's share of a gap over four beats (0.9) made it a
  drone: Journey of the Quarry's two synth voices (Song Check 90, seed 18)
  each held one note for 45 beats through the twelve bars the
  accompaniment sits out, Lunar Island's for 30, and nine of the twenty
  struck voices in seeds 1-60 held a note two bars or longer, where Battle
  Theme's synth never rings past 4.9 beats and its own gaps never pass
  9.9. FFVI: 44 struck-with voices in 32 songs strike 0.78 of the followed
  onsets at the median (0.12 to 1.00), sound 0.8, 0.4, 0.9, 1.0 and 0.9 of
  the line's gap by class, and their longest notes run from 0.6 to 15.9
  beats (median 4.5).
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
  Since round 84 (2026-11-06) a pitched part's token carries its voices'
  pans as a tenth field (`rhythm.pan_field`: the line voice's median
  right-side share, then each voice beyond the line's in the sixth field's
  rank order, kept to twentieths and joined by "/":
  `accompaniment=half:56-68:0.8:2:0.6:1.2@s5a1fa4d5d3@0.33::s8320f1bea2:dense+varied:0.35/0.65`),
  and since round 85 a voice's two places where its song has them
  (`rhythm.pan_word`, `readings.pan_moves`: stays of a bar or more at
  exactly two pans a tenth or more apart; `0.60x5|0.45x13` sits at 0.60
  for five bars and 0.45 for thirteen, again and again; `0.35x4>0.65`
  moves once, after four bars; FFVI's 44 such voices of 406, a stay ten
  bars at the median), placed bar by bar by `render.pan_at`),
  and `render.pan_of` pans each written voice there (`Plan.pans`; the log
  line "pans from the balance: accompaniment=0.35/0.65 melody=0.50 kit
  K=0.50 h=0.60"), the writer's fixed pans (`plan.PANS`) standing for a
  token without the field or a voice past its list. Why: every written
  song had one stereo picture, the tune at centre, the counter at 0.6, the
  accompaniment's voices at 0.6 and 0.4, where FFVI sits half its voices
  0.1 or more off centre (the melody in 37 of 76, the counter 63 of 111,
  the accompaniment 72 of 153) and a part's voices 0.15 to 0.18 apart at
  the median (the second rules audit, `rules-to-words.md`).
  Since round 87 (2026-11-06) the drums' token carries the kit's channels
  as its fourth field, the voices field a pitched part fills with a count
  (`rhythm.kit_channels`: the slot letters each game channel plays, a
  slot's channel the one its sample is struck on most, "KS|h", "S|c",
  "K"); the kit takes as many voices as channels (`allot`), each piece
  plays on its game channel (`plan.drum_voice_of`), and the fixed split
  (`plan.DRUM_VOICES`) stands for a token without the field. FFVI puts 19
  of 47 kits on one channel, 20 on two, 8 on three or more; the fixed two
  had cost a pitched voice in 9 of 40 written songs and dropped kick hits
  under a snare the game had on its own channel.
  Since round 63 (2026-10-29) the drums' token carries the song's kit as
  its eighth field (`rhythm.kit_token`: each piece letter with the pack
  id of the sample the song strikes it with most, `K=sbfe716b9b6,S=s1279e119a1`,
  in LETTERS' order), so the written kit's pieces and samples are one
  song's with its levels (`samples_for` takes each sample where the pack
  holds it; the `kit_pieces` word stands without the field). Since round
  68 (2026-10-30) each piece carries its own level beside its sample, after
  an `@`: the median level of the notes struck on that sample, the
  loudness factor applied as the part's level has it (`Song.kit_levels`),
  as a share of the song's loudest part's level in tenths
  (`K=sbfe716b9b6@1.7,S=s1279e119a1@0.7,h=sd1c4c7ce33@0.2`; a piece whose
  level the readings never heard keeps the old form, and the drums' fifth
  field stays as the fallback). The plan keeps them
  (`extras.drums.kit_levels`, `plan.kit_piece_level` by kit slot, the
  open hat at the hat's; the log line "kit from the balance: KSh (K
  sbfe716b9b6 at 1.7, ...)") and `whole.note_level` plays a drum note on
  a kit slot at its piece's share over the top level, a slot without one
  at the part's share. Why: the part's one level is the median over every
  note of every drum voice, the most frequent piece's, and FFVI's hat is
  the most frequent and its strike the quietest, so Blackjack's token
  said drums at 0.2 where its kick plays at 1.7 of the bass and its snare
  at 0.7, and the render, bringing every piece to that one heard loudness
  over its own strike, played the kick as quiet as a hat (Whole 169's
  kick at volume column 6 and hat at 28 against Blackjack's 64 and 24,
  its drums -25.6 LUFS under the whole against -9.4). Over FFVI's 46 kits
  with a level the kick sits at a median 1.6 of the loudest pitched part
  (15 of 17 over 1.0), the snare at 0.3, the hat at 0.2, the crash at 0.6,
  and in 22 of the 46 the loudest piece is twice the part's one level or
  more. After: Whole 169's kick at 64 and hat at 27, its drums -10.7
  under the whole; seeds 161-170's kits a median -15.5 under from -21.3
  (FFVI -9.5), the rest of it the one-piece kits, which the field cannot
  move (one piece's median is the part's).
  Since round 75 a slot carries the note the piece is struck at (a tonal
  piece's as a degree of the song's key since round 79, `d-7`, `c+11`; a
  drum piece's chip rate as a note, `r48`, `r63t` where the game tunes it
  from song to song), since round 77 how long the song keys it for, since
  round 80 the sample the kit leans on (the loudest with a fifth of the
  letter's hits, the most struck within a decibel), and since round 81
  its strike class (`@m`: the sample's hits a bar in its song, rare under
  half, an accent under one, sparse to two, medium to six, dense over),
  and since round 82 an echo mark where the game sends the slot's sample
  (`@e`: the sample's own share of notes that send, which the readings
  keep beside the voices' since the chip toggles a channel's echo note by
  note), and since round 84 its pan after the mark (`@0.45`: the median
  right-side share of the hits struck on the sample, kept to twentieths,
  `rhythm.PAN_BIN`; `@m@@0.45` where the slot is dry), and since round 88 a
  tuned slot's rate, moved with the written key, stays inside the rates the
  game struck the sample at as that piece (the `kit_rates` word,
  `render.kit_rate_wall`: three tuned pieces since round 102; the "pitched
  snare" the wall was built for, struck within -4 to +3 and moved to -10,
  was the game's guitar, read as a snare until then), and since round 99 a slot whose letter the
  song strikes on a second sample carries that sample after a `+` with its
  level, note or rate, hold and share of the letter's hits
  (`h=sd1c4c7ce33@0.14@r60@0.43@d@@0.50+s831784ce4b@0.14@r60@0.44@0.14`,
  the open hat beside the closed one; `kit_seconds`); the song's key
  (`key=9:minor`) stands before the top, and since
  round 82 its echo word before the key
  (`echo=0.20:80:0.78:melody:bass+drums`, the echo table's outcome), which
  the writer takes in place of a draw, a marked kit piece's notes sent and
  the piece beside it dry. The drum figures count each letter's slot's
  sample's hits (round 81) and its second sample's (round 99), and a kit
  whose token carries classes is written from its limbs' tables under them. Since round 83 a tonal sample
  a drum voice strikes on three pitches or more, no one of them half its
  notes, is read as a voice of its own by the role reader
  (`roles.split_melodic_pieces`: a counter-line, or a bass where it sits
  low), so Wild West's blip on fifteen pitches is a part with the
  channel's echo and no kit slot. Since round 89 a bass or chord
  channel's second instrument in a register of its own is a voice of its
  own too (`roles.split_second_instruments`), kept beside the counts
  until its word, so the channel's register and sample fields are its
  main instrument's (Wild West's bass 28-36, not 28-80), and a snare that
  shared a channel with a pitched part is in the kit (Kefka's, Dancing
  Mad (part 1)'s, Overture (part 3)'s).
  Since round 95 the sounded share (the third field) is the line voice's
  (the part's merged voices had put the gap to the other voice's note
  under a note's length: Umaro's accompaniment read 0.8 where its line
  pecks 0.4), and for the chord parts and the bass it carries the line's
  share by gap class after an `@` (`0.4@0.8/0.4/0.2/-/-`: under half a
  beat, half to one, one to two, two to four, a bar or more; `-` where
  the class has fewer than two notes), which the plan keeps for the part's
  only and line voices over the `gap_sounds` draws.
  *`balance`: shape (part); drawn in ?, _plan_once; conditions bass, bass_habits, cell_handoffs, changes, counter_figures, counter_pairs, counter_shares, drum_group_habits, drums, drums-KSt, drums-c, drums-h, drums-o, echo_habits, habits, half_recall, kit_pieces, lengths, melody_recall, moves, pair_bar_recall, pair_recall, part_entries, part_speeds, part_textures, parts, periods, recall_continues, recall_sources, relations, rhythm, second_figures, tempos, tune_grain, values, voice_intervals, voice_moves, voices, voicings.*
  Since round 103 a chord part's token carries two more fields, its
  line's own motion class and its own off-chord tier
  (`rhythm.line_motion`, `rhythm.line_tone_tier`: the line alone, by the
  `motions` thresholds (a third of its strikes moving, two thirds) and
  the `tone_tiers` ones (a tenth of its onsets off the chord, 0.3); FFVI's
  56 accompaniment lines with the field 29 arpeggiated, 18 mixed, 9
  block, and 31 some, 14 many, 11 rare; its 10 harmony lines 8
  arpeggiated and 2 block). The plan takes both where the token has them
  (`plan.extras[role]["motion"]` and `["tone_tier"]`; the draws are still
  made and kept as `motion_drawn` and `tone_tier_drawn`, so no other
  draw moves), the voices beside the line keep the drawn motion, and a
  token without the field (a line under sixteen pitched notes, or
  without tone bars) keeps the draw. Why: both had been drawn from the
  pooled tables once a part, so Battle Theme's token, whose riff moves on
  0.37 of its strikes and rarely leaves the chord, was written
  arpeggiated and decorated on seed 150 (The Terminal of Glass, "spastic
  and clashing" to the owner on Song Check 85) while every other field
  of its accompaniment was Battle Theme's own. Over seeds 1-60, 62 of 67
  chord parts took both fields; the accompaniment's motions went from
  33 arpeggiated, 9 mixed, 5 block as drawn to 28, 13, 8 as used (FFVI
  29, 18, 9), and every one of 400 seeds kept its token song (the fields
  sit last in the token, so the table's order held).

- **parts**, **voices** — whether a song has each part by the band's size;
  how many voices a song uses. The fallbacks for the band and its voice
  count when the balance table is missing.
  *`parts`: shape (part, band); drawn in compose; conditions voices · `voices`: shape (part, band); drawn in compose.*

- **registers** — the register a part plays in (midi low–high; a layered
  part's line voice's, not the span of all its voices: FFVI's layered
  accompaniments span 16 semitones merged and 12 as a line, and the merged
  span handed to every voice had put one voice over four octaves). The
  fallback register for a part where the `balance` token has none; since
  round 34 it is the register a part's sample is fitted to, and the voice
  is written in the range the `ranges` word drew for that sample
  (`whole.bound_of`). The `balance` table's registers are counted the
  same way.
  *`registers`: shape (part); drawn in _plan_once.*

- **sounds** — the share of its gap a part's note sounds. Drawn once a part;
  the writers' note lengths.
  *`sounds`: shape (part); drawn in _plan_once.*

- **habits** — a part's density and repetition habit (sparse / medium /
  dense × repeating / mixed / varied), by the tempo band and the part's
  weight. Drawn once a part; conditions the figure tables (`rhythm`,
  `drums`) so a dense part draws dense bars.
  *`habits`: shape (part, tempo, weight); drawn in _plan_once, compose, game_habits, habit_near, melody_models, write_melody, write_upper; conditions bass, cell_handoffs, changes, drum_group_habits, drums, drums-KSt, drums-c, drums-h, drums-o, half_recall, kit_pieces, lengths, melody_recall, moves, pair_bar_recall, pair_recall, part_entries, part_speeds, part_textures, recall_continues, recall_sources, relations, rhythm, tune_grain, values, voicings.*

- **bass_habits**, **drum_habits**, **drum_group_habits** — the bass's
  habit (density, tones, octaves); the kit's density habit; each drum
  group's own habit given its backbone slot's strike class (round 81) and
  the kit's. Drawn once; condition `bass`, `drums` and the group figures.
  *`bass_habits`: shape (part, tempo, weight); drawn in _plan_once, write, write_bass; conditions bass, cell_handoffs, changes, drum_group_habits, drums, drums-KSt, drums-c, drums-h, drums-o, half_recall, kit_pieces, lengths, melody_recall, moves, pair_bar_recall, pair_recall, part_entries, part_speeds, part_textures, recall_continues, recall_sources, relations, rhythm, tune_grain, values, voicings · `drum_habits`: shape (part); drawn in _plan_once; conditions bass, cell_handoffs, changes, drum_group_habits, drums, drums-KSt, drums-c, drums-h, drums-o, half_recall, kit_pieces, lengths, melody_recall, moves, pair_bar_recall, pair_recall, part_entries, part_speeds, part_textures, recall_continues, recall_sources, relations, rhythm, tune_grain, values, voicings · `drum_group_habits`: shape (part, classes, habit); drawn in _plan_once; conditions bass, cell_handoffs, changes, drums, drums-KSt, drums-c, drums-h, drums-o, half_recall, kit_pieces, lengths, melody_recall, moves, pair_bar_recall, pair_recall, part_entries, part_speeds, part_textures, recall_continues, recall_sources, relations, rhythm, tune_grain, values, voicings.*

- **voicing_habits**, **motions** — an upper part's richness (thin, full,
  rich) and how it moves through its tones (block, mixed, arpeggiated).
  Drawn once a part; condition `voicings`, and the motion walks the voices
  along the stack a step a strike.
  Since round 103 a chord part whose balance token carries its line's
  own motion class (the token's twelfth field, `rhythm.line_motion`)
  takes it in place of the draw for the line's walk; the voices beside
  the line keep the draw, and a part without the field draws as before.
  *`voicing_habits`: shape (part); drawn in _plan_once, write_upper; conditions voicings, widths · `motions`: shape (part); drawn in _plan_once, write_upper.*

- **layers** — what each voice of a part beside its line does, by its rank
  (the busiest first): doubling at an interval, alternating, or apart (how
  far off, how dense). Drawn once a voice for a part with two voices or
  more: a doubling voice is written at the interval, since round 97 by the
  chord where the `parallel_intervals` word reaches (the line again in the
  scale without it); an
  alternating or apart voice becomes a line of its own under the line's
  bars (`second_figures`), in its register, on a tone of the line's own
  voicing (drawn a span) with the line's lengths and the pair's second
  sample. Since round 70 an apart or alternating voice of an upper part
  is written in its own span (`render.voice_bounds`, `plan.bounds`'s
  `role:v`): the line's written span at the word's offset, within the
  whole range the game plays the voice's sample over; every such voice
  had been folded into one `:second` bound, the first extra voice's
  sample's home band, so Whole 166's "apart +8" voices sat at a median 0
  semitones from the line (round 69), and now sit at +8 and +9. A pedal
  line (a one-pitch register) shares its note with the voices beside it,
  which had written nothing under it (Whole 167's accompaniment). An
  upper part is the line plus its voices so drawn, never a
  stack: FFVI's accompaniment voices strike together 1.2 to 1.5 to an
  onset, and a stack of voices all striking at every onset had been three
  to four notes loud where the tune has one (Song Check 11's Whole 01).
  Since round 90 the draw stands for a voice's own stretches only where
  the balance token says what the voice does by stretch (its layer
  entry's fifth sub-field, above): a doubling or parallel stretch is the
  followed part's line again, in the scale, over its bars.
  Since round 95 a voice written by its relation word is folded by
  octaves into where the token song plays its sample in each stretch
  (`plan.fold_voice`, `voice_bound_at`: the stretch's range, else the
  token's range for the voice's sample, else the voice's span), bar by
  bar as a line is: the word's semitones give the interval class and the
  sample's range the octave. Before, the voice sat at the word's
  semitones wherever the written line was (First Meridian Return's
  accompaniment voice at midi 112; 45 % of such notes outside their
  sample's range over sixty seeds, 10 % after, where the range is
  narrower than the line).
  Since round 120 no voice is written over what the SNES chip can play
  of its sample (four times the recording's rate; `plan.ceilings`, each
  chosen sample's ceiling as a note, set by `samples_for`): a voice the
  fold above never sees, one written by its layer word alone or struck
  with another voice, is folded the same way once it holds a note over
  its ceiling (`plan.hold_under_ceilings`), into where the token song
  plays its sample and under the ceiling; a voice with no such note
  stays where its word put it (`docs/LIMITS.md`).
  Since round 126 a bass's voice takes its token song's own word (the
  balance token's sixth field, a tenth sub-field); the draw is made
  all the same.
  *`layers`: shape (part, rank); drawn in _plan_once, layers_of; conditions second_figures, voice_intervals, voice_moves.*

- **articulation**, **step_habits**, **repeat_habits**, **echo_habits**,
  **chord_tones**, **repeat_rates** — the tune's habits: held or detached,
  how stepwise, how often a note repeats, how much a bar echoes earlier
  bars, the share of strong-beat notes on the chord, the share of moves
  that repeat the note. Drawn once a song for the melody (and the
  counter-line); they condition `values`, `moves`, `melody_recall`, and
  the two rates are held by running-share controllers while the tune is
  written (a draw is weighted toward the chord, or the repeated note, only
  while the tune is under its rate). Since round 96 the `chord_tones` word
  is counted for the counter-line too (FFVI's counters land on the chord
  on 0.6 of their strong beats at the median, as its tunes do), drawn for
  it on an own stream and held by the counter writer: on a beat, while
  the line is not over its share, the interval entries (and the moves it
  takes alone) landing on the chord take the share of the draw's mass
  (`hold_shares`, as the tune's draw_move holds it); the written counter,
  its notes the voice words' intervals from the tune with no chord word,
  had sat at 0.37, and sits at 0.51 over sixty seeds.
  *`articulation`: shape (part); drawn in _plan_once, melody_models, write_melody · `step_habits`: shape (part); drawn in _plan_once, melody_models, write_melody · `repeat_habits`: shape (part); drawn in _plan_once, melody_models, write_melody · `echo_habits`: shape (part, tempo, weight); drawn in _plan_once, melody_models, write_melody · `chord_tones`: shape (part); drawn in _plan_once, write · `repeat_rates`: shape (part); drawn in _plan_once.*

- **tune_sounds** — the share of its gap a tune's or counter-line's note
  sounds, its held notes and its detached ones apart (round 98; the
  `values` word says which a note is: held sounds 0.75 of its gap or
  more), the median to a tenth, by the part and the note's kind. Drawn once a
  song for each line on its own streams; the melody and counter writers
  sound a note by them (`writer.sounded_share`) in place of the constants
  0.95 and 0.5, which had sounded every written tune slightly legato:
  FFVI's tunes hold 0.91 of a gap and detach 0.40 at the median, its
  counter-lines 0.92 and 0.41 (the written ones 0.95 and 0.5 before;
  0.9 and 0.4, 0.9 and 0.4 after). The chord parts and
  the bass have had theirs since round 26 (`gap_sounds`, by the gap
  class) and the token's own since round 95.
  *`tune_sounds`: shape (part, note); drawn in _plan_once, write.*

- **off_scale** — a part's share of notes off the song's natural scale
  (major, or natural minor), by the part, the mode and the beat (strong:
  the onset on a beat; weak: off it), to a twentieth (`rhythm.OFF_SCALE_BIN`);
  for the melody and the counter the line's notes (the heard tune, or the
  voice with the most notes), since the writer holds the word on the line
  it writes and the voices beside it follow their relation words. Counted
  since round 93 for the melody, the counter, the bass, the chord parts
  and the arp (sixteen notes and more); drawn once a song for the melody
  and once for the counter, each on its own stream, one share a beat
  class, and held by the melody writer in place of the STRONG_SCALE ban:
  in `draw_move` an off-scale move takes the drawn share of the fitting
  moves' mass while the line is under it and none while over, on and off
  the beat, the share fitted together with the chord-tone rate
  (`hold_shares`: fitted before it, the chord weighting had thinned the
  off-scale moves again, a tune drawn at 0.30 reaching 0.10); and a
  recalled cell or half-bar comes back moved within a third, after the
  chord, to the place that adds least to a share the line is over. FFVI,
  the melody's line: 0.09 of its strong-beat notes off the scale in major
  and 0.18 in minor (0.10 and 0.24 off the beat; a song's share from none
  to 0.55, Mt. Koltz and Metamorphasis the top), the counter's line 0.14
  and 0.22 (0.26 and 0.26), the bass 0.20 and 0.15, the accompaniment 0.07
  and 0.13, the arp 0.13 and 0.42 (harmonic-minor arpeggios, the raised
  seventh 0.80 of its off-scale notes); a minor tune's off-scale notes
  spread over the flat second, the raised seventh and sixth, the raised
  fourth and the major third in near-equal shares, a major tune's lean to
  the flat seventh, and the written tunes land them in the same
  proportions without a degree word. The written minor tune had sat at
  0.07 on the beat under the ban and the major at 0.29 off it; round 93's
  count (sixty seeds, the line) puts the minor tune at 0.15 on the beat
  and 0.21 off it (FFVI 0.18 and 0.24), the major at 0.11 and 0.17 (0.09
  and 0.10: nine major songs' shares, drawn by the song). The counter's
  line stays at 0.06 to 0.08 (its voice words put it on scale steps from
  the tune's note; only a counter written as a line of its own holds the
  draw), and the voices beside the tune stay on the scale (LIMITS).
  *`off_scale`: shape (part, mode, place); drawn in _plan_once; conditions nothing.*

- **clashes** — a part's share of onsets that fall under a sounding
  note of a part written before it and sit a semitone (one or eleven, mod
  12) from it, by the beat, to a fiftieth (`rhythm.CLASH_BIN`), for every
  pitched part but the bass. The parts are written in a fixed order
  (`rhythm.CLASH_ORDER`: the bass, then the harmony, the accompaniment and
  the arp, then the tune, then the counter), and each is counted against
  the ones before it (`rhythm.clash_under`), which its writer sees; the
  melody and the counter as their lines, the chord parts every note.
  Counted since round 93 (the tune alone, against every other part) and
  by the order since round 94; drawn once a song for each part on its own
  stream and held by its writer in place of the CLASH ban: the melody
  writer in its draws (fitted with the chord and off-scale shares) and in
  placing its recalls; the counter writer by drawing an interval again
  while the line is over its share and the drawn note sits a semitone
  from a part under it (VOICE_TRIES draws, the last kept); the upper
  writer by giving such a tone, while over, to the nearest tone of the
  voicing clear of the parts under it. A voice that doubles a line at a
  unison or octaves copies it exactly, off the scale where the line is
  (round 94: put back on the scale, a double had sat a semitone from the
  tune's altered notes). FFVI: the accompaniment a semitone from the bass
  or the harmony on 0.04 of its strong onsets under one and 0.04 of its
  weak ones (a song's share from none to 0.26), the tune 0.08 and 0.11
  against the bass and the chord parts (to 0.38: Mt. Koltz 0.33 on 116
  onsets, Searching for Friends, Dark World), the counter 0.11 and 0.20
  against all of them (to 0.62), the harmony 0.04 (twelve songs), the arp
  three songs. The written songs (sixty seeds): the counter 0.23 on the
  beat before the round and 0.15 after (0.24 and 0.13 off it; its pairs
  halved, against the tune 0.06 where FFVI has 0.05); the accompaniment
  0.10 to 0.08 (FFVI 0.04: a voicing of one tone has nowhere to go); the
  tune 0.13 both sides (FFVI 0.08: its draws hold the share, its returning
  cells and endings do not). What remains sits in the voices beside the
  lines: a parallel at a third follows its line into the band's semitones
  with no word of its own, and an apart voice in a dense band finds no
  clear tone in VOICE_TRIES draws (LIMITS).
  *`clashes`: shape (part, place); drawn in _plan_once; conditions nothing.*

- **tune_grain** — the tune's grain, since round 66: the share of its
  onsets off the beat as a class (`rhythm.GRAINS`: on-beat under 0.25,
  eighths to 0.5, fine over), by the part (melody, counter) and its habit's
  density tier, drawn once a song on its own stream and held by the melody
  writer over its new rhythms from the first (the running share within the
  class, GRAIN_SLACK either side; the density tier is held the same way
  after TIER_AFTER draws, `writer.tier_bounds`). FFVI's medium tunes sit at
  0.33-0.51 off the beat (quartiles), a median gap of half a beat; four of
  Song Check 52's seven medium tunes sat at 0.15-0.21, where five of
  FFVI's 39 are, with 3.3-3.6 onsets a bar against FFVI's 3.4-5.1: the bar
  chain, conditioned on the bar before, locks a tune into the grain of its
  first draws, and the theme's echoes multiply them. The tier alone
  conditions the draw: under the whole habit it backed off to the part and
  gave a dense tune "on-beat", which no dense tune of FFVI is.
  Since round 138 a bar drawn within its token song's own onsets for the
  part of the form (the balance token's twenty-second field) is not held
  to this word. Why: the share is one over the tune, and a bar's density
  decides it more than the tune does (of FFVI's tune bars of one note
  0.10 are off the beat, of its bars of five to eight notes 0.51); with
  every bar the song's own, no running share was left to hold, and the
  word held to a bar by itself refused every bar of one note (none or
  all of it off the beat) and put one note of each bar of two off it:
  the written tunes' bars of one note fell from 203 to 110 where the
  game's songs have 214, and their bars of two notes all on the beat
  from 0.40 to 0.22 against the game's 0.53. Not held, the bar table's
  own context (the bar's density tier, the feel, the tempo class) gives
  0.88 of the bars of one note on the beat (FFVI 0.90), 0.57 of the
  bars of two (0.53) and 0.34 of the bars of three or four (0.35).
  Since round 147 the places finer than the half beat are the token
  song's tune's own (the `balance` entry's twenty-ninth field), in a
  song written in its feel; the share on the half beat is still the
  bar table's.
  *`tune_grain`: shape (part, habit); drawn in _plan_once.*

- **feels** — a song's feel, duple or triple (triple where a quarter of its
  onsets or more fall on thirds, sixths or twelfths of a beat: 6/8 read on
  a 4/4 grid, a shuffle). Drawn once a song; every figure table (`rhythm`,
  `bass`, `drums`, the drum groups) is conditioned on it, so all of a song's
  parts draw bars of one feel. FFVI's bass bars on triplet positions, 18 %
  of them, came only from its compound and shuffle songs; drawn into
  straight songs unconditioned they stumbled against straight drums.
  Since round 147 the balance token says its song's feel where that is
  not duple (`feel=triple`). The plan still draws this word, and holds
  a tune to its token song's places in the beat only where the two
  agree (`held_places`).
  *`feels`: shape (part); drawn in _plan_once; conditions bass, counter_figures, drums, drums-KSt, drums-c, drums-h, drums-o, rhythm, second_figures.*

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
  *`layer_samples`: shape (part); drawn in pair_for.*

- **gap_sounds** — the share of its gap a note sounds, by the part, the
  voice (only; line or second where the part has two) and the gap's
  length to the voice's next onset (under half a beat, half to one, one
  to two, two to four, a bar or more; the split under a beat since round
  95: FFVI's accompaniment sounds 0.76 of a gap under half a beat, a run,
  and 0.63 of one at half to one, a peck, the arp 0.67 and 0.40, the bass
  0.83 and 0.72); counted a note on the chord parts and the bass. Drawn
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
  Since round 95 the balance token carries the token song's own shares
  for its line voice by gap class (the `balance` entry), and the plan
  keeps them for the part's only and line voices over the draws, which
  are still made so the stream is as it was; the second voices keep the
  pooled word. A song on Umaro's token had held every accompaniment note
  to the next (the pooled share for a layered line, 1.0) where Umaro's
  line pecks 0.4 of its gap.
  *`gap_sounds`: shape (part, voice, speed, gap); drawn in _plan_once, _plan_sounds.*

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
  *`bass_locks`: shape (part); drawn in _plan_once.*

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
  *`levels`: shape (part); drawn in _plan_once; conditions counter_pairs, counter_shares.*

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
  *`layer_levels`: shape (part); drawn in _plan_once.*

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
  *`counter_shares`: shape (part, tune); drawn in _plan_counter.*

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
  *`counter_samples`: shape (part); drawn in _plan_counter; conditions voice_intervals, voice_moves.*

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
  *`counter_pairs`: shape (part, tune); drawn in counter_pair_for.*

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
  *`section_levels`: shape (part, form); drawn in _plan_once, plan_section_levels.*

- **section_fills** — what a voice does in a section's last bar against
  the section's bars before, by its part, whether it is the part's line
  or a voice beside it, and the section's place in the form (round 118):
  `fuller` where its notes there are `rhythm.DENSITY_STEP` times the
  median of the other bars it plays in or more, `thinner` at the inverse
  or less (a rest among them), `same` between; a section under
  `FILL_BARS` bars counts nothing. The plan draws it a section for the
  part's line and for its voices beside the line (`plan_section_fills`),
  a repeated section copying its source's: `fuller` is a fill on the
  section's last bar, a tier denser for the line through the density
  shift its writer reads (`habit_at_for`, `envelope_at_for`) and, for a
  struck voice, every followed onset and one between each pair half a
  beat or more apart (`struck_with`, `fills`); `thinner` the line a tier
  sparser and the struck voice on the bar's first onset alone. Why:
  Battle Theme's synth plays 15 notes into C against its 8 a bar and 7
  into D against 4, the flourish at the transition, while its guitar
  chugs on; the written synths never filled, their mask drawn bar by
  bar from the pooled second_figures word alone (Song Check 96).
  Since round 125 a song whose form is its token song's takes that
  song's own (the balance token's twenty-second field) and does not
  draw this word.
- **section_densities** — a part's density tier in each own section of
  the form against its song density, by the part and the step the
  section's level makes, round 101: `d+` where the part's notes a bar in
  the section (over the bars it plays in) are 1.5 times its song median or
  more, `d-` at the inverse or less, `d=` between; the step `up` where the
  section's level (section_levels) is 1.5 or over, `down` at 0.67 or
  under, `same` between (`rhythm.DENSITY_STEP`, `level_step`). Why: Song
  Check 82's Inner River Crossing doubled its accompaniment for its last
  part on the same figure, a bare volume move the owner heard as strange.
  The level step came from The Mines of Narshe, whose accompaniment doubles
  in its last section while going from 2 notes a bar to nearly 8 and up an
  octave; counted over all of FFVI's 803 part-sections, a level step up
  rides a density or register change in 7 of the accompaniment's 8 but is
  bare in 7 of the counter's 10 (Overture part 3's counter steps to 1.9
  four times on the same figure), and at level 1.0 the accompaniment
  changes density tier in a quarter of its sections (22 sparser, 17 denser
  of 176), the bass in a sixth, the melody and counter in a sixth; a tier
  up is 1.8 times at the median, a tier down 0.5. So the word is the
  density tier by the step, not a rule that a step must change the figure.
  The plan draws a tier a part an own section it plays in
  (`plan_section_densities`, an own stream `whole:{seed}:section
  densities`, a repeated section copying its source's, `Plan.section_densities`
  as a shift a bar), and the writers take a habit a bar (`habit_at_for`,
  `rhythm.shift_habit`: the song's habit with its density tier moved one
  along sparse, medium, dense, for the table's conditioning) and an
  envelope a bar (`envelope_at_for`, `rhythm.density_bounds`: a tier
  denser, 1.5 times the part's own onsets a bar in its unshifted bars so
  far or more, the tier's FFVI median standing in before two bars are
  written, `DENSITY_TYPICAL`; a tier sparser, the same over 1.5 or fewer)
  for the chord parts' and the bass's figure draws and the tune's new
  rhythms, a shifted bar kept out of the tune's running tier; the counter
  follows the tune's figures through its masks and draws none; the register
  is the token song's own by stretch (round 92), so a step's register
  change is not drawn twice. The habit alone had capped at the dense tier
  (a dense accompaniment drawn denser stayed as it was), and the tier's
  typical alone had left a part already over it unmoved. Over sixty seeds
  36 songs carry a level step (62 steps), 20 of the steps now carry a
  drawn density change (the counter's draw none); a section drawn denser
  sits at 1.63 times the part's unshifted sections at the median (q25 1.17,
  q75 2.58; FFVI's tier up 1.8), one drawn sparser at 0.78 (q25 0.48;
  FFVI 0.5: the manner's figures thin less readily than they thicken);
  Inner River Crossing's accompaniment goes from 4 notes a bar to nearly 8
  where it doubles in level.
  Since round 125 a song whose form is its token song's takes that
  song's own (the balance token's twenty-second field) and does not
  draw this word.
  *`section_densities`: shape (part, step); drawn in _plan_once, plan_section_densities.*

- **part_entries** — where inside a section a part present in it enters
  and leaves: `whole` (its first bar to its last), `enters:k` (its first
  sounding bar k bars after the section's start), `leaves:k` (its last k
  bars before the end), or both, k to ENTRY_CAP (8); by the part, for the
  drums the kit's density tier (round 59; NO_TIER, `-`, for every other
  part), the section's place in the form and the section's length class
  (short to 4 bars, medium to 8, long) (round 46, 2026-10-28). Drawn in
  `whole.plan_texture` for each part the section's texture has, after the
  texture; the drums' apart (`whole.drum_entrances`), once the kit's habit
  is drawn, on an own stream and from the tier's own entrances alone
  (DRUM_ENTRY_FLOOR): FFVI's dense kits play 101 sections of 106 whole,
  its sparse kits 20 of 27, and the word by part, place and length alone
  had a dense kit leave eight bars before a section's end; the part's
  bars before its entrance and after its exit are turned off; a draw no
  section this short can hold is drawn again, then the part plays it
  whole; a repeated section copies the bars, entrances and all. The log line: "entrances (part_entries): counter enters 2 in
  B; bass leaves 1 before the end of C". Why: FFVI's parts join inside a
  section more often than at its edge (61 late entrances inside, 45 at a
  boundary; early exits 14 and 12), where one texture a section had let
  them join at its lines alone; after, seeds 1-45 have 37 inside and 40
  at a boundary (exits 12 and 6). FFVI by part: the melody plays its
  section whole 0.81 of the time, the counter 0.86, the bass 0.89, the
  accompaniment 0.90; the rest enter a bar or two in, or leave a bar early.
  Since round 124 a song whose form is its token song's takes that
  song's own entrances (the balance token's twenty-first field); the
  word is drawn all the same and stands for a song whose form is drawn.
  *`part_entries`: shape (part, habit, form, length); drawn in _plan_once, plan_texture.*

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
  *`sample_lengths`: shape (part, speed); drawn in sample_floor.*

- **sample_speeds** — the fastest bars a song plays a sample in, as a class
  of the ninetieth-percentile bar rate in notes a second (2, 3, 4, 6, 8,
  12, 24, faster), by the sample. Read in the sample choice for a part
  (`whole.best_sample`) beside the ranges: of the samples covering the
  part's register, one a song of the game plays as fast as the part's
  fastest bar comes first, then one some song plays that fast in its
  fastest bars, and where none does the excess over the game's fastest on
  the sample weighs against the range's fit. FFVI keeps its slow-attack
  pad under six notes a second; a written part had it at eight.
  *`sample_speeds`: shape (part); drawn in sample_speed.*

- **part_speeds** — a part's fastest bars, as a class of the
  ninetieth-percentile bar rate of its line in notes a second (the
  `sample_speeds` classes), by the part and its habit's density tier
  (sparse / medium / dense, as the habit words bin it). Drawn once a part
  after every other plan draw (`whole._plan_speeds`): what the part's
  sample is fitted to for speed before the part is written (round 34).
  The fit had read the speed off the written notes, so the sample was
  chosen after the writing and a voice's register could not come from
  the sample it plays.
  *`part_speeds`: shape (part, habit); drawn in _plan_speeds; conditions gap_sounds, part_samples, sample_lengths.*

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
  *`cell_handoffs`: shape (part, habit, place); drawn in hand_off_cells.*

- **letters** — a song's form as its parts' letters in order (`A B A B C`),
  drawn whole. The form's shape: which parts repeat which.
  *`letters`: shape (part); drawn in _plan_once, carry_theme, plan_form, write; conditions part_entries, part_textures, phrase_letters, section_levels.*

- **form** — a part of the form as new, again or back, by its index. The
  fallback chain when no `letters` table exists.
  *`form`: shape (part, meter, index); drawn in plan_form; conditions part_entries, part_textures, phrase_letters, section_levels.*

- **lengths** — a part's length in bars, by the meter and the song's length
  habit. Drawn a part; a repeated part is as long as the part it repeats.
  *`lengths`: shape (part, meter, habit); drawn in plan_form; conditions cadences, part_entries, periods.*

- **loops** — the chord the loop returns to. Where the loop starts (after an
  intro); the render plays the loop's first bars again at the end of a
  listening page's song.
  *`loops`: shape (part); drawn in plan_chords.*

- **loop_parts** — the part of the form the loop returns to (0 the first,
  1 the second), by whether the song opens with an intro, a first part the
  form never comes back to (round 98). Drawn once a song on an own stream
  (`plan.plan_loop`) in place of the rule that sent every loop to the
  second part after an intro and to the first bar without one: the rule
  was right for 40 of FFVI's 61 loops, and FFVI returns to the intro
  itself in 15 of its 53 intro songs, to the second part in 33, further
  on in 5, and to the first part in 7 of 8 songs without an intro. Over
  sixty written seeds the loop went back to the intro in 19
  intro songs and to the second part in 37, moving from
  the rule's bar in 23; a part the form lacks leaves the rule's
  bar. The `loops` word's chord stands at the loop bar as before.
  *`loop_parts`: shape (part, intro); drawn in plan_loop.*

- **part_textures** — the texture a part of the form keeps (which parts
  sound: `all`, `no drums melody`), by the kit's density tier (round 59;
  NO_TIER where the song has no drums), its place in the form and the
  part before's. Drawn a part: a part keeps one texture (FFVI's parts
  do), an intro leaves parts out, a repeated part keeps its texture. The
  kit's habit is drawn before the textures, on an own stream, so the tier
  can condition them: FFVI's dense kits sit out a whole section in one bar
  of a hundred, its sparse kits in fifteen, and the written dense kits had
  sat out one in ten. After round 59 the written kits sound in 0.94 of
  the bars (dense; FFVI 0.97), 0.75 (medium; 0.83) and 0.64 (sparse;
  0.69). Since round 124 a song whose form is its token song's takes
  that song's own textures (the balance token's twenty-first field);
  the word is drawn all the same and stands for a song whose form is
  drawn.
  *`part_textures`: shape (part, habit, form, previous); drawn in plan_texture.*

- **chords** — a bar's chord as a numeral in the key, after the bar
  before's. Drawn a bar as a chain; a repeated part keeps its chords; a
  theme return brings the theme's chords back when `return_band` says so.
  Since round 106 the chain holds a chord at the token song's share of
  bar lines (`holds=0.53`, Battle Theme) on an own stream, its own draw
  still made.
  *`chords`: shape (part, mode, previous); drawn in plan_chords.*

- **period_holds** — inside a period, whether a bar plays the bar a period
  before again (held) or varies (a fill, a turnaround), by the part and
  the period. Drawn a bar inside a period; the writers play the bar a lag
  before again where it is held (the figure, re-realized on the bar's
  chord; an upper part takes its source bar's voicing too on the same
  chord) and draw the bar fresh where it varies.
  Since round 106 the token song's own hold share stands in for the
  draw where the token carries it (the draw still made, so no other
  draw moves).
  *`period_holds`: shape (part, period); drawn in _plan_once.*

- **kit_pieces** — (since round 63 the balance token's kit field gives
  the pieces where it has one; the word stands as the fallback) which
  pieces a song's kit strikes at all, as letters
  (`KSh`, `Sc`, `c`), by the kit's density tier (round 58). FFVI's kits are
  their tiers': a sparse kit is a cymbal, a kick or one other sound; a
  dense kit the kick, snare and hat, or snare and cymbal. Drawn once a
  song on its own stream, from the tier's own kits alone (seven medium
  songs hold seven kits, and the table's smoothing had handed a medium
  song a dense kit); the writer's kit is these pieces, a hit on any other
  dropped.
  *`kit_pieces`: shape (part, habit); drawn in _plan_once; conditions drums.*

- **phrase_letters** — a part's phrases as letters: the theme head again
  (`T`), an earlier head again (`r`), or new (`n`), by how many phrases the
  part has and its place in the form. Drawn a part of the form; the first
  phrase the tune plays is the song's theme. With the *carry a theme*
  switch the letters are drawn again until the theme comes back.
  Since round 138, where the tune's bars have their token song's own
  onsets, a phrase comes back only where its bars keep within them
  (half to one and a half times): `T` brings back the theme's latest
  statement whose head keeps within the phrase's first bar, bar by bar
  while its bars keep, and where no statement's head does the phrase is
  written new and stands as a statement of the theme for the phrases
  after it; `r` brings back the last earlier phrase every bar of which
  keeps, and is a new phrase where none does. Why: the theme is the
  first phrase the tune plays, and where that falls in an intro the
  game plays a note a bar in, the letters brought a note a bar back
  through parts of the form the game plays three in (a song on
  Searching for Friends: 31 bars of whole notes).
  *`phrase_letters`: shape (part, phrases, form); drawn in _plan_once.*

- **return_band** — which of the chords, the bass and the accompaniment come
  back with the theme. Drawn a return: the theme's chords are copied under
  the return and the bass and accompaniment play their theme bars again
  (`song.copies`). With the *band comes back* switch a return with nothing
  behind it is drawn again. Since round 134 a bar plays its theme bar
  again only where that bar is within the token song's own onsets for
  the part of the form the return falls in (round 125's envelope, which
  `envelope_at_for` marks `own`; `_free_figures`): elsewhere the bar
  keeps the figure it was drawn, so no draw moves. Why: since round 124
  the tune rests where its token song's rests, a theme stated over an
  intro is stated over the intro's band, and the return put the intro's
  one-note bars over a part of the form the song plays full (the
  written Terra's bass and accompaniment struck the first beat and
  stopped, four bars, twice).
  *`return_band`: shape (part); drawn in _plan_once.*

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
  *`sample_ambitus`: shape (part); drawn in ambitus_of.*

- **tune_doubling** — in a bar of the tune that is not the theme's cell,
  which other parts play the same cell with it and how far from the tune
  (`theme_doubling`'s token: `bass:-24 counter:+0`; `none`), by the part
  (tune) and place (other) (round 44, 2026-10-28). Drawn a tune bar after
  the parts are written, in `whole.double_theme` beside the theme word:
  the drawn parts play the tune's bar at the interval in their register.
  FFVI doubles a non-theme bar in 0.23 of them; the written songs had the
  theme cell alone doubled (tune onsets doubled at the pitch class 0.22
  against FFVI's 0.40; after, 0.31).
  *`tune_doubling`: shape (part, place); drawn in double_theme.*

- **theme_doubling** — where the tune plays its theme cell (its statement,
  or an echo later), which other parts play the same cell with it and how
  far from the tune (`counter:+12`, `bass:-24`, `none`), by place. Drawn a
  theme-cell bar after the parts are written: the drawn parts play the
  tune's bar at the interval, in their register. FFVI doubles the hook in
  a third of its theme-cell bars, the bass two octaves down most often.
  Since round 139 a drawn part with its token song's onsets a bar for
  the part of the form (round 125: the bass, a chord part) plays the
  tune's bar only where that bar is within half to one and a half times
  them (`whole.own_keeps`), and keeps the bar it wrote elsewhere; the
  word is drawn all the same. The same holds for `tune_doubling`, for
  `theme_carrier` (every bar of the phrase) and for `cell_handoffs`
  (the bar with the cell in its half). Why: since round 138 the tune's
  bars are as thin as its token song's, and the written Terra's bass,
  doubling a tune's bar of one note, stopped for four bars where the
  game's bass plays six or seven.
  *`theme_doubling`: shape (part, place); drawn in double_theme.*

- **theme_carrier** — the part that carries the theme phrase under a phrase
  whose tune is not the theme (the bass, the counter, the accompaniment;
  almost always none). Drawn a phrase: the carrier plays the theme phrase
  in its register while the tune plays what it drew. Rare in FFVI (one
  phrase in a hundred), and kept at that rate.
  *`theme_carrier`: shape (part); drawn in carry_theme.*

## The parts' bars: the figure tables the writers draw from

- **layer_sounds** — for a layered part (two voices or more), the share of
  its gap a note sounds, for the line and for the second voice apart. Drawn
  once a part; the line and the second line take their own lengths (FFVI's
  two-voice bass is a sustained line under a staccato voice; the part's one
  share had given both the same).
  *`layer_sounds`: shape (part, voice); drawn in write.*

- **bass** — the bass's bar as a figure: positions with chord-tone marks
  (root, fifth, octave, passing). Drawn a bar as a mixture under the bass
  habit, realized on the bar's chord in the bass's register; a second bass
  line apart (from `layers`) is written the same way in its own register.
  *`bass`: shape (part, meter, tempo, habit, feel, previous); drawn in fit, write, write_bass.*

- **rhythm** — a part's bar as an onset pattern; for an upper part holding
  two voices or more, its own line's bar (the voice with the most notes),
  not the voices merged. Drawn a bar as a mixture under the part's tempo
  class (round 61: a dense bar at 170 BPM had come from slow songs'
  sixteenths, 7 tune notes a second against the game's 2.9 in its fast
  songs; the bass and drums tables take the class the same way) and habit:
  the line's figures. (Counted merged, a dense bar held two voices'
  onsets, and a line written to it with a second line beside struck 10.3
  times a bar against FFVI's 7.3.)
  *`rhythm`: shape (part, meter, tempo, habit, feel, previous); drawn in melody_models, write, write_upper.*

- **second_figures** — a voice beside a layered part's line, bar by bar,
  where the part holds two voices or more, by the voices' note share over
  the line (sparse, half, full; round 65, the token's share class for a
  written song), the song's feel and tempo band, the line's onset count
  and its pattern. The voice is a mask over
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
  *`second_figures`: shape (part, layer, feel, tempo, onsets, line); drawn in write.*

- **voicings** — which chord tones an upper part holds in a span, by the
  chord's shape and the part's richness. Drawn a span as a mixture; the
  tones are stacked on the voices, lowest first.
  *`voicings`: shape (part, shape, habit); drawn in write, write_upper.*

- **tone_tiers**, **tone_figures**, **tone_degrees** — where a chord part's
  line leaves the chord, and to which tone (round 96). `tone_figures`: a
  bar of the line as its onsets' tone classes against the chord sounding
  at each, `c` a tone of the chord and `x` a tone off it (`c c c x`), by
  the part, the song's tier, the onset count and the line's own pattern;
  the upper writer draws it under the line's bar as a second voice's mask
  is drawn (never below the part, the tier and the onset count), read
  around the line's onsets where the drawn count differs. `tone_tiers`:
  how much of the line leaves the chord over the song (rare: under a
  tenth of its onsets; some: under 0.3; many), drawn once a song a part
  on an own stream and conditioning the figure's draw, so a song is pure
  or decorated as a whole: FFVI's 58 accompaniments spread from none to
  0.72 (10 songs rare, 29 some, 19 many; their medians 0.04, 0.23 and
  0.45), and a draw from the pooled bars alone had put every written song
  at the pooled 0.28. Since round 103 a chord part whose balance token
  carries its line's own tier (the thirteenth field,
  `rhythm.line_tone_tier`) takes it in place of the draw, so the song is
  as pure or decorated as its token song, and a part without the field
  draws as before. `tone_degrees`: the degree an off-chord onset plays,
  as semitones over the chord's root (2 a ninth, 5 a fourth, 9 a sixth, 10
  a seventh over a triad), by the part, the chord's shape (which decides
  which degrees are off it) and the bar's previous off-chord degree, drawn
  an onset and chained within the bar (FFVI keeps the degree from one such
  onset to the next 0.52 of the time: an ostinato pecks one tone off the
  chord, a fill walks; drawn once a bar it had repeated always, and
  'repeat' was 0.42 of the written off-chord notes against FFVI's 0.22);
  the onset takes the drawn degree nearest the voicing tone it replaces,
  and the voices beside the line see the note played. FFVI's
  accompaniment line leaves the chord on a quarter of its notes (the
  songs' medians 0.12 to 0.38), in 768 of its 1,447 bars, mostly on
  extensions and ostinato tones rather than neighbors (a leap to the tone
  0.39 of such notes, a repeat 0.22, a step in or out 0.38; the ninth 0.17
  of them, the fourth 0.12, the sixth 0.11, the flat sixth 0.11), the
  harmony on 0.14 of its notes, the arp on 0.14 (three songs; the raised
  seventh of the minor key 0.74 of them). The written line had held the
  voicing's tones alone (0.07 of its notes off the chord, and those from
  voicing marks the chord lacked); after this round the accompaniment
  line sits at a median 0.35 over sixty seeds (by tier 0.44, 0.33 and
  0.07 against FFVI's 0.45, 0.23 and 0.04; the figure's own onsets 0.25,
  the rest the theme the part carries), the harmony at 0.13 (0.14), the
  arp at 0.03 (its sevenths a semitone from the root give way to its
  clashes share). The clashes word stands over a tone the figure asks
  for: a part over its share for the beat gives the tone to the voicing.
  *`tone_tiers`: shape (part); drawn in _plan_once; conditions tone_figures · `tone_figures`: shape (part, tier, onsets, line); drawn in tone_figure_for, upper · `tone_degrees`: shape (part, shape, previous); drawn in tone_degree_for, upper.*

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
  *`moves`: shape (part, mode, habit, place, tone, previous); drawn in melody_models, write.*

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
  *`melody_recall`: shape (part, habit); drawn in melody_models, write, write_melody.*

- **theme_body** — how much of the theme phrase comes back with its head.
  Drawn a return: the theme's head, then that many of its bars, then new.
  *`theme_body`: shape (part); drawn in write.*

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
  *`counter_figures`: shape (part, weight, feel, tempo, onsets, line); drawn in write.*

## The drums

- **drums** — the kit's bar as one figure, every piece. Drawn a bar as a
  mixture under the kit's pieces (kit_pieces) and then its habit and feel:
  the kit repeats and varies as a kit does (the groups drawn apart had
  changed every bar), and a draw that backs off backs off to the same
  kit's bars (round 58: with the habit and feel before the kit, a kit the
  tier had not been seen with backed off to every kit's bars, none on its
  pieces, and the played bar was silent). Where no drawn bar fits the kit,
  the bar is any the table knows on its pieces (`writer.last_resort`): a
  bar the plan has the kit in is never silent. Until round 58 the drum
  group habits the plan draws (the hat's, the cymbals', the rest's) had
  capped each piece's hits a bar at its tier's top (`writer.group_caps`,
  against "sparse" cymbals riding in sixteenths); the caps chopped the
  kit's own bars (a dense kit at 7 hits a bar against FFVI's 13.7) and are
  retired: the kit's pieces say which sounds it has, the kit's bars say
  how they play. Since round 145 the table is kept a second time as
  `drums@2`, each song the reading has at half its speed counted in
  double time (`packtables.DOUBLE_TIME`, `songs_for`), and a song whose
  token is counted so (`Plan.beat`) draws its kit's bars from it: the
  table as read holds such a song's bars at half speed, a march's
  snare as rolls.
  *`drums`: shape (part, meter, kit, tempo, habit, feel, previous); drawn in compose, drums, samples_for, write.*

- **drums-KSt**, **drums-h**, **drums-c**, **drums-o** — the kick, snare and
  toms' bar; the hat's; the cymbals'; the other sounds'. The group figures,
  drawn by the slice writer (`tools/slice1.py`); the whole-song writer
  draws the kit as one where its token carries no strike classes, and
  since round 81 from the limbs under the slots' classes: the kick, snare
  and toms' bar under three fields, the densest slot's class first (the
  limb's backbone), a single-letter limb's under its class; the class says
  the density, the group's habit drives the recall urn, and the class's
  bars are their own cap (a one-figure class, a rare crash and its rests,
  stays the chain's floor). Each is kept a second time since round 145
  for the songs counted in double time, as the kit's table is
  (`drums-KSt@2`, `drums-h@2`, `drums-c@2`, `drums-o@2`); a table that
  comes out as the one as read is left out of the fit (FFVI's
  `drums-o@2`).
  *`drums-KSt`: shape (part, meter, limb1, limb2, limb3, tempo, feel, previous); drawn in _plan_once, drums, write, write_drums · `drums-h`: shape (part, meter, classes, tempo, feel, previous); drawn in _plan_once, drums, write, write_drums · `drums-c`: shape (part, meter, classes, tempo, feel, previous); drawn in _plan_once, drums, write, write_drums · `drums-o`: shape (part, meter, classes, tempo, feel, previous); drawn in _plan_once, drums, write, write_drums.*

## The bass

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
  note's chord role and the line's own move add nothing to it. The
  interval is counted between the two notes' scale tones (a note off the
  key's scale: the tone below it) where the line's note is on the scale,
  and since round 66 in semitones from the note itself (`s-4`) where it
  is off it (the value `line`: scale or altered), which the writer puts
  back exactly (`writer.interval_pitch`): the counted steps alone had gone
  back on the scale, so a unison with the tune's leading tone came out a
  semitone under it. FFVI's tune is off its key's scale at 0.23 of the
  counter's onsets with it; the written counter's intervals against such
  a note were "other" (a second, a tritone, a seventh) in 0.54 where
  FFVI's are in 0.15, and 0.12 against a scale note, FFVI's 0.12. A voice
  note off the scale against a scale note is kept as its scale tone: a
  mark for it had put alterations against notes they never follow (the
  written "other" against scale notes rose to 0.22). The product with
  `voice_moves` now weighs the move the entry's note would make from the
  voice's own last note, as the word counts it (it had taken the move from
  the voice's last note with the line).
  *`voice_intervals`: shape (part, kind, line, previous); drawn in bass, upper, write.*

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
  *`voice_moves`: shape (part, kind, place); drawn in bass, upper, write.*

- **parallel_intervals** — where a parallel voice's note sits against the chord at each onset it
  shares with the voice it follows (round 97): the chord tone it lands on
  (root, third, fifth, seventh, sus) or, off the chord, its semitones from
  the nominal placing, the followed note at the stretch's semitones (`+4`,
  `-8`; from the followed note itself before round 109), by the stretch's
  nominal interval in scale steps (`roles.generic` of the relation word's
  semitones: 2 a third up, -5 a sixth down, 11 a twelfth up), the tone
  class of the followed note against the chord, the voice's part and the
  landing before it in the stretch. Counted over the voices that follow a
  part's line voice (a line that reads as parallel to its own harmony
  voice is no unit; two lines parallel to each other count once, the one
  further from the lead following: the tune leads, then the counter, the
  chord parts, the bass), 4,764 onsets in 60 stretches of 37 songs, and
  since round 109 over the struck-with stretches too (round 107's `w`
  words, the line or a sibling voice followed): 8,281 onsets in 50 songs,
  Battle Theme's synth 193 of them at its twelfth (the fifth 49, at the
  nominal off the chord 36, the third 21, the root 19, an octave over the
  nominal 15). The writer follows a relation word's parallel or struck
  stretch, and a layer word's doubling, by it (`plan.parallel`, in place
  of the line again in the scale): a drawn chord tone is placed as that
  tone of the written chord nearest the followed note at the nominal
  interval, so a third over a major chord's third is its fifth at +3 and
  over a minor chord's at +4, and the voice rides the chord's quality; an
  off-chord outcome is placed from the nominal placing; a chord part's
  voice holds the part's clashes share as its other voices do. Why the
  nominal placing: an outcome counted from the followed note meant a
  different place at every nominal, and a draw at a nominal the word had
  never seen backed off to all of them, so Battle Theme's struck synth at
  a twelfth drew the thirds' and sixths' `-4` and `+3` and the octave
  doubles' `-12` from the guitar's note and sat a third or an octave under
  the guitar (36 of 119 draws in Journey of the Quarry, 31 of its 115
  stabs an octave or more under the nominal; midi 17-28, its sibling a
  fifth under at 7-21, where the game's synth never goes below 45): the
  distorted rumble heard on Song Check 91. FFVI's parallel voice sits on a
  chord tone on 0.65 of its shared onsets, 0.82 where the line's note is
  on the chord (0.95 over the third, 0.76 over the root, 0.79 over the
  fifth) and 0.40 where it is off it, at its nominal semitones on 0.58;
  the line again in the scale, as the writer had it, lands on the chord on
  0.48 of the game's onsets and matched the game's note on 0.31. Written
  (sixty seeds), the parallel voices had sat on the chord on 0.33 of their
  onsets (0.42 over a line on the chord, 0.22 off it); after this round
  0.62 (0.77 and 0.41; over the root 0.78,
  the third 0.92, the fifth 0.76), the rest the
  written lines' own: they are off the chord on 0.41 of these onsets
  where FFVI's are on 0.42, but a written tune's off-chord notes are its
  recalls and passing tones where FFVI's parallel voices mostly ride
  arpeggiated chord parts.
  Since round 110 a nominal that one song alone plays draws the word's
  finer levels, the part and the landing before, with that song behind
  them (`plan.parallel`: a one-song minimum where the nominal's level has
  fewer than PLAN_SONGS songs); the draw had passed over any level under
  two songs, so Battle Theme's chain at its twelfth, after an octave-up
  landing the fifth four times in five, after a two-octave landing another
  two-octave stab two times in three, never engaged, and the game's
  phrase-shaped excursions came out as single stabs two octaves up, drawn
  apart, a tenth of a beat each (Song Check 92). FFVI has eight such one-
  song nominals (11, -16, -14, 22, -22, -12, -10, 17 and 21 in scale
  steps).
  *`parallel_intervals`: shape (interval, tone, part, previous); drawn in parallel.*

## The upper parts (accompaniment, harmony, arp)

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
  Since round 106 a backing part whose balance token carries its period
  (`p2/83`) takes the token's lag where the pooled draw gives the part
  of the form a period, and its holds at the token's share.
  *`periods`: shape (part, length, tempo); drawn in _free_figures, _plan_once, song_of, upper; conditions period_holds.*

## The tune

- **climax** — which of a song's tune phrases holds the tune's highest note,
  by its place among them (opening, early, middle, late, closing). FFVI's
  tune peaks at 0.45 of the song at the median; the written tunes had
  peaked at 0.24. The melody writer draws it once and gives that phrase the
  song's peak as its ceiling.
  *`climax`: shape (part); drawn in melody.*

- **arc** — how far a tune phrase's highest note sits under the song's peak
  (0, 1-2, 3-5, 6-9, 10+ semitones), by the phrase's place. Drawn a phrase:
  the phrase's ceiling in the arc.
  *`arc`: shape (part, place); drawn in melody.*

- **summit** — how far the tune's highest note sits above the tune
  register's top (the 90th percentile, the registers table's), in
  semitones (0, 1-2, 3-5, 6+). Drawn once a song: the climax may rise above
  the register as FFVI's does (its tunes span 22 semitones; the written
  ones had spanned 16).
  *`summit`: shape (part); drawn in melody.*

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
  *`half_recall`: shape (part, habit); drawn in melody.*

- **recall_moves** — how far a recalled tune cell sits from its last
  occurrence, by whether it is the bar before's cell (same) or one heard
  before that (earlier) and whether the chord under it is the one under
  its source (same, other), round 100: at pitch (`0`), moved with the
  chord root (`root`: the root's own motion, folded into the octave either
  side), or by semitones (`+2`, `-5`, `6`). FFVI's 62 tunes recall 428 bars
  in their own form parts: a cell comes back at pitch in 0.70 of the
  earlier recalls and 0.53 of the immediate ones, within a third in 0.88
  and 0.95; over another chord it stays at pitch in 0.38 (earlier) and
  0.27 (same), moves with the root in 0.27 and 0.45, by a step in 0.12 and
  0.22. The tune writer (`again`, the half-bar recall in
  `new_cell_halves`) had re-rooted every recall on the new chord, the
  cell's first note the same interval over the new root, so a passage
  recalled over a chord a fourth away came back a fourth away (at pitch in
  0.27 of the written recalls, a fourth or fifth off in 0.22), and its
  recalled bars sat a semitone from the band on 0.15 to 0.25 of their
  strong beats against FFVI's 0.04 to 0.10, where its fresh bars sat at
  FFVI's 0.08. Now a recall's first note sits where the word's draw puts
  it (`writer.tune.recall_anchor`, an own stream `{seed}:{role}:recall
  moves`), the whole cell then moved within a third where the tune wants
  its beats on the chord or the cell would put a share over its word, the
  chord-tone, off-scale and clash holds weighed together (the chord had
  come first, and a clean shift a third away was passed over for one more
  chord tone), and a hold counts a note where the share with it in would
  pass the song's (it had counted only once over, so a song's first
  recalls clashed freely and the hold ran a bar behind). Over sixty seeds
  the recalled bars' strong-beat clashes fell from 0.147 to 0.101
  (earlier; FFVI 0.099) and from 0.167 to 0.117 (the bar before's; FFVI
  0.043), the tune's from 0.108 to 0.099 (FFVI 0.084; by song 0.109 to
  0.100, FFVI 0.069), and its recalls at pitch rose from 0.27 to 0.38. The
  phrase ending's note takes the degree's option that adds least to a
  share the tune is over (0.17 to 0.16 of phrase ends a semitone from the
  band, FFVI 0.06: the ending degree is the key's, not the cadence
  chord's, a limit).
  *`recall_moves`: shape (part, recall, chord); drawn in melody.*

- **values** — a melody note held or detached, by its value and the song's
  articulation habit. Drawn a note; the tune's note lengths, until round
  141 gave a tune's and a counter-line's line their token song's own
  (the balance token's twenty-sixth field): the draw is still made, and
  still decides for a voice beside a line and a line without the field.
  *`values`: shape (part, value, habit); drawn in counter, melody, melody_models, write.*

- **contours**, **contour_sizes**, **peaks** — a four-bar phrase's contour
  (rising, arch, falling…); how far it goes in semitones by its shape;
  where it peaks. The contour and its size steer a new phrase's line
  (`contour_targets`); the peaks are counted, not yet drawn.
  *`contours`: shape (part, mode); drawn in melody, melody_models, write; conditions contour_sizes, peaks · `contour_sizes`: shape (part, mode, contour); drawn in melody · `peaks`: shape (part, mode, contour); drawn in no writer (counted for the measures).*

- **relations**, **phrase_shifts** — how a phrase stands to the one before
  (new, repeated, moved up or down, answered); how far it sits above or
  below the one before, by that relation. Drawn a phrase: a repeated or
  moved phrase is the last phrase again, moved; a new phrase sits where the
  shift says and the line is steered there over its first third (taken as
  a jump, the phrase-start moves had been a quarter steps against FFVI's
  half).
  *`relations`: shape (part, mode, habit); drawn in melody, melody_models, write; conditions phrase_shifts · `phrase_shifts`: shape (part, mode, relation); drawn in melody.*

- **endings** — the note a phrase ends on, against the key. Drawn a phrase;
  the last note is placed on the degree.
  *`endings`: shape (part, mode); drawn in melody, melody_models, write.*

- **cell_rhythms** — a new cell's rhythm: new to the tune, the bar before's,
  or an earlier one's. Drawn for a new cell; the rhythm itself then comes
  from the part's `rhythm` table.
  *`cell_rhythms`: shape (part); drawn in melody.*

- **recall_continues** — whether a passage the tune recalls goes on with
  the bar after its source (`yes`, `no`), by the part and the song's echo
  habit (round 50, 2026-10-28): FFVI mixed 0.64, repeating 0.91, varied
  0.30. The melody writer draws it where the bar before was an "earlier"
  recall and its source has a bar after it (`continues()`); the CONTINUE
  constant (0.8) is the fallback without the table. Why: the constant was a
  rule standing where a count belonged (docs/idiom/rules-to-words.md).
  *`recall_continues`: shape (part, habit); drawn in melody.*

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
  *`pair_recall`: shape (part, habit); drawn in melody · `pair_bar_recall`: shape (part, habit); drawn in melody · `recall_sources`: shape (part, habit); drawn in melody.*

## The render

- **echo** — the song's echo as the chip had it at key-on, since round 70
  (2026-10-30): its volume of full (EVOL), its delay in ms (EDL), its
  feedback (EFB), the parts that send to it and the parts that stay dry
  (`0.20:80:0.78:accompaniment+counter+melody:bass+drums`; a part sends
  when half its voices or more send on half their notes or more), one
  unit a song. The readings keep it as features of source `echo`
  (`reading.echo_of_notes`, written at import by `store.keep`; FFVI's 82
  were added from the SPCs after the fact). Drawn once a song on its own
  stream (`whole:SEED:echo`) by the writer bare (`whole.compose`'s
  "habit" echo, `render.echo_word`) where the vocabulary has the word, the
  sound set's habits standing where not (`whole.echo_of`, Classic's way);
  the delay is the chip's nearest 16 ms step, and `score_of` sends a part
  as the word says, a part the word's song lacked by the old rule (the
  upper parts). Why: FFVI's echo volume is 0.20 of full in 70 of 82 songs,
  its delay 80 ms in every one, its feedback 0.78 at the median, and the
  written songs had sent every upper part at `score.ECHO_WET` 0.4 with a
  48 to 144 ms "slap": 6 dB wetter than the game ever plays, which the
  owner heard as vibrato and blur (Song Check 54's Whole 166). Since
  round 72 the default player draws the same word by the same draw on
  its own stream (`bitcomposer.performance.echo_for`,
  `written:SEED:performance:echo`) in place of its rule by tempo and
  density over `score.ECHO_WET`, which had sent 0.24 to 0.6 of full; the
  sound set's habits stand where a vocabulary has no echo word, and the
  song's message says which.
  *`echo`: shape (part); drawn in echo_word.*

- **attacks** — whether a part's line plays a struck sample or a
  sustaining one, since round 73 (2026-10-31): `struck` where the sample's
  first 150 ms carry more than twice (6 dB) the RMS of its loop body, so
  the sound decays after the attack, `sustaining` otherwise; one unit a
  part a song, counted on the sample the line plays most (as
  `part_samples` names it) with the samples' loudness as the pack's WAVs
  give it (`rhythm.set_loudness`). FFVI's tunes are sustaining in 63 of 66
  songs (Awakening, Spinach Rag and Good Night are struck), its basses and
  accompaniments mostly so too. On an imported pack the token's own sample
  decides the voice before the pool rule; on a built-in set the pool rule
  (`render.best_sample`) lets a voice of the other class stand down
  wherever one of the drawn class fits the register and speed. Why: after
  the bit set's range tops were placed by ear, its keys (the e-piano,
  piano, pluck and nylon, 14 to 20 dB struck, ranging 36 to 96 at any
  speed) took 6 of 10 default tunes, and a tune that fades between its
  notes reads weak at any measured level (Song Checks 59 and 60).
  *`attacks`: shape (part); drawn in attack_for.*
- **vibrato** — a part's vibrato on its held notes, since round 72
  (2026-10-30): the share of its notes held 0.35 s or more that carry a
  periodic pitch modulation, in each length class (0.35 to 0.5 s, 0.5 to
  1, 1 to 2, 2 and over; in tenths, `-` for a class the song held no note
  in), then its depth in cents either side, its rate in Hz and its onset
  in seconds from key-on (`0.0/0.1/0.3/0.3:30:5.5:0.5`;
  `0.0/0.0/0.0/0.0:0:0:0` for a part with none), one unit a part a song.
  Counted from the game's pitch writes while a note sounds
  (`reading.note_vibrato`: swings back and forth through 1.5 cycles or
  more of 3 cents or more; a slide counts as nothing, a trill of 90 cents
  or more is counted apart) and kept as features of source `vibrato`
  (`reading.vibrato_of_notes`, written at import by `store.keep`; FFVI's
  82 were added from the SPCs after the fact). Not the writer's: drawn
  once a song a part by the player's performance on its own stream
  (`performance.vibrato_words`, `written:SEED:performance:vibrato`) for
  the tune and the counter, each held note taking it with the class's
  share at the word's depth and rate from its onset, rising over one
  cycle; where a vocabulary has no such word the player's old rule stands
  (every held note, 10 cents at 5.5 Hz after 0.12 s) and the message says
  so. Why: FFVI's tunes carry vibrato on a fifth of their held notes
  (none at all in half the songs, nine in ten in a few), at a median 30
  cents, 5.7 Hz in most songs and 15 to 19 Hz in a third, from half a
  second in, so a note under half a second almost never has it; the
  rule had put a third of the depth on every held note a quarter of a
  second in.
  *`vibrato`: shape (part); drawn in vibrato_words.*

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
  *`ranges`: shape (part, role); drawn in samples_for.*

- **kit_rates** — the rate a percussion kit sample is struck at, as a note
  (60 the recording, 48 an octave under), by the sample and the piece it is
  struck as. Counted since round 88 as the wall a tuned kit slot's rate
  stays inside: round 79 reads a tonal kit piece's rate as a degree of its
  song's key and moves it with the written key, and the move had taken
  FFVI's "pitched snare", struck in the game within -4 to +3 of its
  recording, to -10, where it lasted 340 ms and sounded like a guitar (Song
  Check 70's Northern Bells). It was one: the sample is the game's
  distorted rhythm guitar, which the drum namer had called a snare, read as
  an instrument since round 102 (`drums.instrument_by_play`); the wall
  stands for the three kit pieces the game does tune. Over the game's tuned slots and the twelve
  keys a written song can land in, the moved rate fell outside the game's
  rates in 77 of 132 cases. Not a drawn word: `whole.samples_for` reads the
  slot's sample's rates as its piece into the plan (`kit_rate_walls`,
  `render.kit_rate_wall`) and `render.walled` holds the moved rate inside
  them, so the slot keeps the key's move where the game struck the sample
  there and stops at the game's nearest rate where it did not; a pair the
  game never struck has no wall.
  *`kit_rates`: shape (part, piece); read in kit_rate_wall.*

- **kit_seconds** — whether a kit letter's hit takes the slot's second
  sample or the slot's own, by the letter and the hit's place in the beat
  (on the beat, an eighth, a sixteenth, a triplet, finer), round 99. The
  balance token's kit field names a letter's second sample where the song
  strikes the letter on another sample eight times or more
  (`readings.kit_second_samples`), after a `+` with its level, its note or
  rate, its hold and its share of the letter's hits; the letter's figure
  and the slot's strike class count both samples' hits, since the written
  kit gives both their hits (round 81 had counted the slot's alone, the
  kit playing one sample a letter). The writer (`plan.write`, `kit_second_pick`) draws each hit
  of such a letter from this word on an own stream and plays the second
  while the letter's hits are not over the token's share for it; the
  render gives the second its own slot (`hihat2`) and sample, level, rate
  or note and hold, on the main's channel with the main's pan and echo
  mark. FFVI strikes 17 letters in 15 of its 44 kits on a second sample
  (as read since round 102): the hat in 13 of the 17 kits that have one (a
  short closed hat beside a longer open one, the open one off the beat),
  the snare in 2 of 28, a cymbal and an "other" once each. Round 99 had
  counted the Battle Theme's and The Decisive Battle's "sixteenth-note
  rattle beside the backbeat snare" as second snares: the rattle was the
  game's distorted rhythm guitar, which the drum namer had called a snare
  (round 102, `drums.instrument_by_play`), so those two kits have one snare
  and the round's snare numbers (0.86 of the sixteenths on the second) were
  the guitar's chugging. The written kit had played the slot's one sample
  on every hit (round 80's pick of the loudest), so a third of kit songs
  lost the open-hat lift.
  *`kit_seconds`: shape (part, place); drawn in kit_second_pick, write.*

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
  *`part_samples`: shape (part, speed); drawn in samples_for.*

## Counted, drawn nowhere: the measures' words

- **weights** — a part's weight in the band (minor, half, main). The
  fallback for a part the balance did not name; a weight conditions the
  rhythm, bass and echo habits.
  *`weights`: shape (part); drawn in no writer (counted for the measures); conditions bass_habits, counter_figures, echo_habits, habits.*

- **doubles** — what a song's double voices double and how. Counted; the
  plan's second voices are drawn from `layers` instead.
  *`doubles`: shape (part); drawn in no writer (counted for the measures).*

- **texture**, **presence** — which parts sound in a bar after the bar
  before's; a part playing or resting in a bar. Counted; the whole-song
  writer uses `part_textures` (a part keeps its texture) instead.
  *`texture`: shape (part, meter, previous); drawn in no writer (counted for the measures) · `presence`: shape (part, meter, previous); drawn in no writer (counted for the measures).*

- **changes**, **cadences** — where in the bar the chord changes; how a
  part's progression ends. Counted, not yet drawn (the written chords
  change on the bar line).
  *`changes`: shape (part, meter, habit); drawn in no writer (counted for the measures) · `cadences`: shape (part, mode, length); drawn in no writer (counted for the measures).*

- **widths** — how wide the upper voicing sits. Counted; the stack's spread
  is set by the register for now.
  *`widths`: shape (part, shape, previous); drawn in no writer (counted for the measures).*

## Measures and passes, not tables

- **lead** — which voice carries the tune, decided by salience (round 64,
  `translate/lead.py`): the voice the reader labelled melody keeps the
  lead where it is heard, within 9 dB of the loudest tonal voice as each
  renders alone; else the most varied heard voice becomes the melody and
  the old one a counter-line (an accompaniment where a counter exists).
  Why: the reader picks the melody by variety with a quarter of the
  loudest raw volume as its only loudness test, and in one FFVI song of
  seven that voice sits 9 dB or more under the whole; put to the owner's
  ear voice by voice, every such song had its tune elsewhere, and every
  heard label was right. Every word counted on the melody (the tune's
  cells, pairs, hooks, levels, sample, habit) counts on the lead.

- **loudness** (the balance token's `loud=-24`) and **mix_level** — a
  song's rendered loudness: its RMS in dBFS over its first minute through
  the player (the readings' feature render/loudness_dbfs, measured from
  the converted songs; FFVI's 81: median -25.6, the middle sixty between
  -26.3 and -22.0, none above -20.5), to 1 dB, carried on the balance
  token so a song's levels, its top and its loudness are one song's (round
  59, 2026-10-29). The written song's master volume holds its own to it
  (`whole.master_of`): the song's notes as scored give a mix estimate
  (`rhythm.mix_level`: each note's perceived level squared, summed over
  the quarter-beat frames it sounds in, at most two beats of it, the mean
  over the frames anything sounds in, in dB), a written song renders at
  that estimate plus RENDER_BRIDGE (-21.7 dB, measured over 20 written
  songs, quartiles -23.0 and -19.8), and the SNES chip's master volume
  (the IT global volume, a song's from its first bar: FFVI's sit at 32 to
  61 of 128) is set so the two meet; a song under its target with the
  master already full brings its notes up instead. Why: the written songs'
  rendered loudness spread 2.7 times FFVI's (IQR 6.7 dB against 2.5 over
  14 songs) and four of fourteen rendered louder than any FFVI song (up to
  -15.6 dBFS), because the level draws multiply independent things FFVI's
  composer held together: the top level, how many parts share it, the
  sections' levels, the sample's loudness and how thick the texture is.
  The rendered loudness is what FFVI holds steady, so it is the unit; the
  estimate alone would not do (it meets FFVI's renders with a correlation
  of 0.47, so a written song held to its token song's estimate took on the
  estimate's spread, 6 dB). The TOP_SCALE bridge of round 52 (1.7) is
  retired to 1.0, its work being the master's. With it the writer's
  loudness factor reads the module sample's own loudness
  (`whole.sample_rms`), not the pack table's: the instrument builder
  scales every sustaining voice's loop to one loudness
  (`samples.LOUDNESS_TARGET`), so the table's numbers (the game's samples
  as the game plays them, right for counting the readings) are not what
  the module plays, and round 56 had boosted "quiet" samples the module
  had brought up already, to full; with the module's own numbers no note
  is capped in 20 songs. Since round 65 a note's loudness is what it hears
  of its sample, its strike for STRIKE_SECONDS then its body
  (`rhythm.heard_rms`), on both sides: the readings scale a note's level
  by it for the note's own length and the writer divides by the module
  sample's (a struck accompaniment sample's attack 3.4 dB over its body
  and a slow lead's 3.1 under had put a backing over the tune the counts
  said was on top).
