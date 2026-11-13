# Known limits of the written songs

What the written songs do that can sound odd or wanting, and why it stands.
Each entry says whether it is the game's own way (kept by the vocabulary
rule, [IDIOM.md](IDIOM.md): the writer is never patched past what its
vocabulary says), a word not yet counted, or a product choice; and what
would change it. Rounds are in [idiom/phase-4-writing.md](idiom/phase-4-writing.md).

- **A kit arrives with its song's character, not with its music** (noted
  2026-11-06, Song Check 70). The balance token brings one FFVI song's
  band as one unit, its instruments, levels, pans, channels and kit, and
  the notes come from the pooled tables. FFVI's kits are idiosyncratic:
  16 of its 47 are a single lone piece, and several hinge on one odd
  sample (The Mines of Narshe's dull footstep burst on every beat, Cyan's
  sizzle, Wild West's blip; the Battle Theme's "pitched rattle" was the
  game's guitar, read as an instrument since round 102). Under its
  own music each belongs; under a tune, counter and pad from the pool the
  same kit can read as clapping or as a bell. The Endless Valley's kit is
  The Mines of Narshe's, the same sample, rate, level, pan and figure,
  heard beside the game's own rendering by the owner: the sounds are the
  game's. Where the realization went further than the game ever did, it
  was a fault and was fixed (round 88: a tuned slot moved an octave past
  the game's rates). Expect roughly a third of written songs to carry a
  one-piece kit, as a third of FFVI's songs do. What could change it: a
  count of how a kit's character relates to the rest of its band in FFVI
  (whether a lone-thud kit ever sits under a melody-led song); if it
  never does, a word is in that.
- **Every song is in 4/4.** The form and texture tables were counted at
  one meter; FFVI's four 3/4 songs lend no bars (round 81). A meter word
  is the first audit's rule #8, standing.
- **A tune without stretches may play notes its sample never played in
  its song.** Where the token carries the line's instrument by stretch
  (round 91) the tune is written over its own stretches' ranges and folded
  into each; a tune on one instrument keeps round 43's wall, the whole
  range the game ever took its sample over, because binding it to the main
  sample's own range had cut 9 of 30 tunes short (round 86).
- **A line enters a new stretch's register by octaves.** Since round 92
  the writers take a register a bar, so a line that changes instrument is
  written in each stretch's register; where the line crosses a stretch line
  the next note is the last one moved by octaves into the new register, and
  the contour goes on from there. A phrase the form repeats is copied as
  written, and the fold after writing moves it into its bars' registers
  where they differ.
- **A channel's second instrument is not written.** The second voices the
  reader splits off (42 in 25 FFVI songs; round 89) are kept beside the
  counts, not in them: they are another part on the same channel (Kefka's
  pedal channel carries a high counter piece), and a voice of its own would
  ask the writer for a ninth chip voice in the eight-channel songs that
  time-share one. The line's own instrument by stretch (round 91) is
  written; a channel shared by two parts in turn is not.
- **A voice beside a line is folded into its sample's range; a narrow
  range still leaks.** Since round 95 a voice written by its relation
  word is folded by octaves into where the token song plays its sample in
  each stretch, bar by bar as a line is (before, it sat at the word's
  semitones from the line wherever the written line was: Umaro's
  accompaniment voice, two octaves over a tune the game has low there,
  reached midi 112 where the game plays that sample at 72 to 88, and 45 %
  of such notes sat outside their sample's range). What remains is the
  narrow range: a sample the game plays over four or eight semitones
  cannot hold a parallel line, and 10 % of relation-voice notes still sit
  just outside (the arp's parallels worst). The reader's relation runs
  were a sample run long, too: Umaro's voice doubles the tune for five
  bars and then plays its own chromatic run on the same sample, and the
  whole run read as the double; since round 96 a run's own edge bars (two
  or more, eight notes or more) are a stretch of their own, and a change
  in the middle of a run, or a shorter edge, still reads as the relation.
- **A chord part leaves the chord by degree, not by figure.** Since
  round 96 the line leaves the chord where its tone figure says (a bar's
  onsets as chord tones and tones off it, drawn under the song's tier)
  and plays the drawn degree nearest the voicing tone it replaces, chained
  within the bar; so FFVI's extensions and ostinato tones come out, and
  the written off-chord notes fall into FFVI's kinds (a leap to the tone
  0.36 against 0.39, a repeat 0.18 against 0.22, a step 0.36 against 0.38).
  A neighbor's return and a passing tone's direction are not a word: a
  step comes out where the chained degree happens to sit a step from the
  chord tones around it. The arp's off-chord tones are the minor key's
  raised seventh, a semitone from the root, and give way to its clashes
  share (0.03 of its line against FFVI's 0.14): the two words meet there.
  Since round 111 which of the chord's tones the line favours is the token
  song's profile (the hold on the voicing tone); its off-chord onsets are
  still the tone figure's and its degrees the tone_degrees word's.
- **The bass leaves the chord at the game's pooled rate, not each
  song's.** The bass's figures carry its passing tones at FFVI's share of
  marks (0.19 of tokens against 0.17) and its line sits off the chord on
  0.18 of its notes pooled against FFVI's 0.16, but by song at a median
  0.24 against 0.15: FFVI's basses are mostly near pure with a few walking
  ones (quartiles 0.05 to 0.29), the written ones all near the pooled
  rate. A tier for the bass as the chord parts have (`tone_tiers`) would
  carry the spread; the bass_habits word's tones class carries some.
  Since round 111 the bass's chord tones follow the token song's profile
  (its root, third, fifth and seventh shares); its off-chord share is
  still its figures' passing marks at the pooled rate. Since round 114
  the bass keeps its pitch class across the token song's share of bar
  lines (a pedal under the changing chords, the bar before's main pitch
  class), as far as the bars left to it allow: the theme band, the
  hand-offs and the form's repeats rewrite bars of the bass after its
  writer and those bars stay as the theme wants them, so a song whose
  bass carries much of the theme (The Terminal of Glass, 13 of 23 playing
  bars) stays under the share; and the hold pedals the bar after a change
  rather than the bars of a riff's stretch, so the pedal moves every bar
  or two where Battle Theme's stays for a part. Since round 117 a chord
  part's line keeps the token song's step profile (its moves the same
  pitch, a step, a leap); the bass's token carries the field too and the
  bass writer does not read it yet (FFVI's basses and the written ones
  leap alike, 0.41 and 0.37 of their moves on Battle Theme's token).
- **A voice beside a line follows its word whole.** Since round 90 the
  balance token says what a voice beyond a line does beside which part,
  stretch by stretch (a double, parallel at an interval, or its own line),
  and the writer copies the followed part's line at the interval over the
  stretch's bars. A voice that struck with only some of that line's notes
  (the cover rule asks for half) is written striking them all; a voice's
  own stretches are its layer word's line (the pooled `layers` draw),
  since what the voice's own motion was there is not yet a word; and the
  samples a voice changes between stretches are not written (the
  instrument-by-stretch word, the next round).
  Since round 107 a voice that strikes with the line or a sibling voice on
  0.8 of its notes at no one interval is a struck-with word, written on
  the followed voice's onsets, and since round 108 its share of those
  onsets, its note lengths by the line's gap and its longest note are the
  token voice's. Which onsets a bar thins is still the pooled
  `second_figures` mask's shape, held toward the share; a gap class the
  token voice never played falls to the pooled second voice's share; and a
  struck voice whose token voice rings long rings as long (since round
  115 within the token voice's sounding share of its bars' time; a voice
  under the share is not lengthened: its stabs are its gap classes'
  already), and (Mt. Koltz's and
  Opening Theme part 3's hold notes of 15.9 beats).
  Since round 122 the relation is read part by part of the form, so a
  voice struck with its line in one part and on the tune in another is
  written each way; a part the voice plays under eight notes in takes
  its neighbour's reading, a change inside a part is not seen, and a
  song with many short parts gets a word of many stretches (Mt. Koltz's
  second accompaniment voice, ten). A stretch on another part's line is
  written wherever that line plays, the voice's own part resting or not:
  where the texture rests the accompaniment through a part and its
  synths double the tune there, they play as the tune's layers.
  The sections' densities were thought to move out of step on Battle
  Theme's token (the round 104 investigation) and do not, by the measure:
  at a section boundary the written pitched parts step alike on 0.33 of
  boundaries and agree pairwise on 0.53 (sixty seeds), FFVI's on 0.27 and
  0.53 at the median, and Battle Theme's own on 0.00 and 0.33 of its four;
  measured in round 113 and left as it is.
  The relation reader counts channels, and a game sometimes splits one
  line over two: of FFVI's 56 pairs of voices that strike together on 0.8
  of their notes, 7 trade the top note between their channels on a fifth
  or more of their steps (Returners' bass pair on 0.81, Mt. Koltz's
  accompaniment on 0.50, Aria's on 0.54), each channel reading as a voice
  where the ear hears one line; Battle Theme's synth pair is not one of
  them (channel 0 holds the top note on every one of their 219 stabs, and
  the lower voice's octave flips are the game's own voicing). Measured in
  round 110 and left.
- **Parts written apart clash more than FFVI's.** Each part holds its
  clashes share against the parts written before it since round 94 (the
  tune in its draws and recalls, the counter in its interval draws, the
  chord parts in their voicing tones), which halved the counter's pairs
  (against the tune 0.06 of its strong onsets, FFVI 0.05; against the bass
  0.07, FFVI 0.05). The rest sits where no word is held: the tune's line
  keeps a floor from its phrase endings (the ending degree is the key's,
  not the cadence chord's: 0.16 of phrase ends a semitone from the band,
  FFVI 0.06) and its theme returns (0.13 of their strong onsets, FFVI's
  returning bars 0.10), round 100 having brought its recalled bars to
  FFVI's rate (the line's strong onsets 0.10 against 0.08), a chord voicing of
  one tone has no clear tone to go to (the accompaniment 0.08 against
  0.04), a parallel voice followed its line into the band's semitones
  until round 97 (a tune's parallel third in Whole 4 on 0.40 of its beats,
  the tune itself on 0.12; a chord part's parallel voice now lands by the
  chord and holds the part's clashes share, 0.08 of its onsets a
  semitone from a part under it against 0.11 before), and an apart voice
  in a dense band finds no clear tone within VOICE_TRIES draws. A
  placement for returning cells that looks at the band would carry it
  further.
- **The counter is more diatonic than FFVI's.** A counter by the voice
  words takes scale steps from the tune's note, so it leaves the scale
  only where the tune does: 0.06 to 0.08 of its line's notes against
  FFVI's 0.14 to 0.26 (round 93's count). Only a counter written as a
  line of its own holds its off_scale draw. A semitone form of the
  interval word against a tune note on the scale would carry the rest.
- **A parallel voice rides the chord only where the line does.** Since
  round 97 a parallel voice lands where the `parallel_intervals` word
  says against the chord (a third over the chord's third is its fifth, a
  third over its fifth the root above), which put the written voices on
  the chord on 0.77 of the onsets where the line's note is on it (FFVI
  0.82); over a line note off the chord the game's voice is on the chord
  0.40 of the time and the written one 0.41: the word knows the
  line's tone class, not which off-chord tone the line took, and the
  written lines leave the chord as much as FFVI's but elsewhere (a tune's
  recalls and passing tones; FFVI's parallels mostly ride arpeggiated
  chord parts). A class for the line's off-chord tones (a step from which
  chord tone) would carry the rest.

- **A line's echo is its part's across its stretches.** The echo word names
  the parts that send and the kit pieces by their marks; a line that
  changes sample between stretches sends every stretch alike. FFVI sends
  one sample and keeps another dry on 11 of the 89 voices that change
  sample (Kefka's tune and counter: the organ dry, the strings wet; Gau's
  accompaniment). An echo mark per stretch on the token's eleventh field
  would carry it; measured in round 98 and left.
- **A voice beside a line plays all the line's bars.** FFVI's layer
  voices play in 0.90 of their line's bars at the median, 19 of 129 in
  under half; a written voice plays wherever its line does, since the
  relation word has stretches of notes and no stretch of rest. A rest kind
  in the word would carry it; measured in round 98 and left.
- **The chord parts' spread is the token's.** The `widths` word is counted,
  not drawn: a written part's line is one voice, and its spread per chord
  span comes from the voices beside it at the token's own offsets. Measured
  in round 98 over sixty seeds, the accompaniment spans 10 semitones at
  the median against FFVI's 11, the arp 9 against 8, the harmony 8 against
  5 (ten FFVI songs); the token carries the first two, the harmony's is
  the gap.
- **The beat reader breaks a driving song into many sections.** A song
  keeps its tempo but the reader takes its grid again where three onsets
  in a row miss it, and FFVI's battle songs, whose drivers shift the
  grid by a few hundredths of a beat now and then, come back in twenty
  sections (Battle Theme), sixteen (The Decisive Battle) or a hundred and
  fourteen (Dancing Mad part 5), each with a meter and a downbeat of its
  own from a few bars' accents; the joins leave bars of 1, 2, 3, 5 or 6
  beats (Battle Theme: 10 of 41 since round 105, 13 before), and those
  bars' figures go into the tables as they are. Since round 105 a
  section's kit sets its downbeat and its meter, so the sections agree;
  one grid for the song, re-locked without a new section, is the fix.

- **A chord part's line moves more than its motion class says.** Since
  round 103 a chord part's line walks the voicing stack as its token
  song's motion class does (block holds a tone a strike, arpeggiated
  moves one), but its pitches are also the voicing drawn for each chord,
  the off-chord degrees and the themes the part carries, and what the
  line keeps from one chord to the next is not yet a word. FFVI's block
  accompaniment lines repeat the note on 0.89 of their moves at the
  median (mixed 0.50, arpeggiated 0.05); the written lines repeat on
  0.44, 0.36 and 0.26 over seeds 1-60, so a riff that pecks one tone in
  the game still wanders in the writing.

- **A level step's company is its density tier alone.** Since round 101 a
  section's level step draws the part's density tier with it
  (`section_densities`), but FFVI's steps also come with register moves
  (The Mines of Narshe's accompaniment up an octave) and with textures
  where the part leads alone (Aria de Mezzo Carattere's, Another World of
  Beasts' intros); the register is the token song's own by stretch (round
  92) and is not drawn again, and which parts sound is its own word (the
  token song's since round 124). The counter follows the tune's figures (within its
  own onsets a bar by the part of the form since round 143) and takes no
  density tier of its own, where FFVI's counter steps are mostly bare
  anyway (7 of 10).
- **A kit letter's second sample plays as its first does, and a third is
  not carried.** Since round 99 the token names a letter's second sample
  and the writer gives it its hits by the `kit_seconds` word, but the
  second plays on the main's channel, at the main's pan and with the
  main's echo mark: some of FFVI's seconds sit on another channel, and a
  channel of its own would ask the kit for a voice the token did not
  count (the Battle Theme's "two snares on two channels" of round 99 were a
  snare and the game's guitar, round 102). A third sample on a letter
  (Techno de Chocobo's third hat, Devil's Lab's third snare, Dancing Mad
  (part 5)'s toms on three channels) is folded into the first two.
- **A tonal sample pumped on two pitches is a kit piece.** Round 77's play
  clause reads a voice on one sample at one or two pitches, eight notes or
  more, held under two beats, as a drum voice; FFVI's percussion plays so
  at G#3, the driver's own pitch, and Wild West's pump (169 strikes at E2
  and C3, 0.23 beats each) has the same shape. Round 89 unmasked it (the
  counter-line that shared its channel split off), so it is a kit piece
  `o`, struck through the kit at the degree it played most, where the game
  pumps two notes. A pitch word for the clause (percussion at the driver's
  own pitch) would separate them; a count first.
- **No surround, no leaning echo.** FFVI never inverts a voice's or the
  echo's sides and sets the echo's two volumes equal in every song, so
  the FFVI vocabulary has no such word ([ROADMAP.md](ROADMAP.md)); a pack
  from a game that uses them would bring it.
- **Hard pans on headphones.** A written song's voices sit where its
  token's FFVI song put them, by amplitude alone as the SNES pans for a
  television; a lead held at 0.25 all song sits far to one side on
  headphones, as the game's own songs do. The player's WIDTH (under
  GAIN) narrows every pan toward centre at playback; the vocabulary is
  untouched.
- **A drum played as a pitched part is tuned as the reader heard it.**
  Since round 119 a kit voice given to a pitched part is tuned by its
  tonal reading (the readings' fundamental of the recording), so the
  written part plays the recording at the rates the game does. For
  FFVI's rhythm guitar the reading is the pitch heard: Battle Theme's
  riff on the SNES chip is on the reading on every note. For a drum it
  is one reading of a sound with no single pitch. Mt. Koltz's tom, an
  accompaniment to the role reader, sounds two semitones over its
  reading through its strike, in the game's own audio as in a song
  written on it; The Empire Gestahl's snare, struck at one rate there,
  is written a line. Whether such a voice is a part or a kit piece is
  the role reader's question; the tuning only keeps the game's rates.
- **A voice beside a line that the fold does not see sits where its
  word puts it, up to the SNES chip's ceiling.** Round 95 folds a voice
  written after the lines by its relation word into where the token song
  plays its sample. A voice written by its layer word alone (a doubling
  at its interval, an apart voice in its span) and a voice struck with
  another (round 107) are placed from the line and never folded: over
  400 seeds 0.30 of the first kind's notes and 0.21 of the second's sit
  outside the range the token song plays their sample over (0.08 of the
  folded kind's), in 267 songs. Since round 120 one bound holds for
  every voice: the chip's pitch register stops at four times a
  recording's rate, so a sample sounds no higher than two octaves over
  the note it plays at 32 kHz, and a voice that holds a note over that
  ceiling is folded whole, as round 95 folds, into where the token song
  plays its sample and under the ceiling (7 of 400 seeds had held such a
  voice, every note of it over the ceiling sounding the ceiling's one
  pitch). A voice with no such note is left as written, wherever it
  sits: folding them all is the same fold, and it would move 267 songs,
  a change to hear before it is made. One cause stands under it: an
  apart voice whose span is a pedal's width holds the middle of its
  offset register, not of its span (5 of 400 seeds: Lower Aqueduct's
  third accompaniment voice at 99 where its span is 58 to 60, at 51 now
  for the ceiling's sake; Twin Glass's second at 24 where its span is
  68).
- **The loop's bar is the token song's part's first bar, and its chord
  is not drawn for the turn.** Since round 132 a song on its token
  song's own form loops to the part the game's loop returns to. The
  chord chain is drawn before the loop's bar is moved (so that no other
  draw moves), with the pooled loop_parts draw's bar as the loop's: the
  chord the `loops` word draws for a loop's return sits at that bar,
  and the bar the loop now returns to has the chain's own chord. A
  song whose form is not its token song's keeps the pooled draw.
- **A loop is the token song's or none.** Since round 121 a backing
  voice plays its figure again where its token song's voice loops, by
  the form's letters; a token form short of the bars asked is played
  round again since round 154 and its loops are taken with it, and a
  pack whose token carries no form has none. The figure is the first bar the
  voice plays on it, as the writers wrote it: a bar drawn note by note,
  not a riff built as one. A bar the token song has off its figure (a
  fill where the tune holds a note, a turn at the part's end) is the
  bar as written, with the `section_fills` word's density on a part's
  last bar and no figure of its own; a figure eight bars long is not
  read.
- **Outside its loops the backing still plays a new bar every bar.**
  Battle Theme's C and D are no loops: there its guitar, bass and kick
  strike together under the tune's main notes and its synths double the
  tune, and the written parts keep their own rhythm at their own
  density. Since round 122 a voice beside a line is read part by part
  (the written synths double the tune through D), and since round 123
  the line doubles the bass where the token song's does (Battle Theme's
  guitar through A, C and D), at its octave, and since round 125 a
  backing line's onsets a bar in each part of the form are the token
  song's (Battle Theme's bass and guitar thin to four and five a bar in
  C and D). What is left: the line follows only the bass (a line that
  doubles the tune through a part is its own there); and the double is
  of the bars the bass plays, so where the texture rests the bass the
  line keeps its own notes.
- **A part's bars in a part of the form are one span, and a returning
  part is its first statement.** Since round 124 the parts that sound in
  each part of the form are the token song's, each from the bar it
  enters to the bar it leaves. A bar a part rests between those is not
  carried: the kit's figures rest single bars at their tables' rate, a
  pitched part's writer plays through. A part of the form that returns
  sounds as its first statement did, where the game's second A can add
  a voice. A form under the sixteen bars a song is asked (four of
  FFVI's) is played round again from its loop's part since round 154,
  the part that comes round its first statement note for note; under
  the player's asking for a theme that returns, Shadow's own form
  gives the tune no phrase to come back in and the plan is drawn again
  on another token (1 seed of 400 where 3 were). And a song whose form
  is not its token song's (six tokens carry no form) keeps the pooled
  textures and entrances. Since round 153 its
  lines keep to their song's pace all the same: one number for the
  whole song, so a line is written at its song's median onsets a bar
  in every part of the form (a song that thins in one part does not).
  Since round 155 its kit's pieces keep to their song's hits a bar the
  same way, and a kit that plays through its song plays in every bar:
  the bar or two the game rests it are not carried.
- **A song's tempo is one of the game's, near its token song's.**
  Since round 137 a written song runs within a tenth of its token
  song's tempo, at one of the tempos the game's songs of that class
  run at (the tempos word, to five beats a minute): it is the token
  song's tempo itself only where the draw lands there or no other is
  near. The bars' figures are still drawn by the tempo's class, three
  classes for the whole game.
- **Which of a tune's notes are cut is drawn, not placed.** Since round
  141 a tune's note is held or detached at its token song's own rate
  for the gap to the next note (five gap classes), and sounds the
  song's own share of the gap. Which notes of a class are the cut ones
  is a draw at that rate: the game cuts the notes its phrasing cuts
  (the first of a group, the notes before a rest), and where in the
  bar or the phrase a cut note falls is not counted. A gap class the
  song's tune plays fewer than four notes of takes the whole line's
  rate and the nearest class's shares: the game's Kids Run Through
  the City cuts its two notes before a long gap to 0.6 of it, and the
  written tune, holding as the rest of that tune does, sounds 0.22
  of its notes past a bar line where the game's sounds 0.02. And
  a written tune's rhythm is not its token song's, so the whole
  line's share differs though each class keeps the song's: the game's
  Gogo holds 0.40 of its tune's notes, half of its sixteenths and none
  of its eighths; the written tune on it plays eighths and no
  sixteenths, and holds 0.24. Song by song the written tune's share
  of held notes is within a tenth of its token song's tune's in 51 of
  62 songs. The floor of round 136 stands under it: no note shorter
  than the song's shortest usual one where its gap leaves room.
- **Only the tune's line takes its song's note lengths.** A voice
  beside the tune's or the counter-line's line, and a second
  counter-line, are still sounded by the pooled `values` and
  `tune_sounds` words under the pooled `articulation` habit, as is a
  line whose token song's tune has under sixteen notes (two of the
  118 melody and counter tokens). A part that doubles or carries the
  tune's bar takes the notes as the tune sounds them, raised to its
  own sample's floor in the render. The sample's floor (round 36) is
  still asked of every voice but the tune's and the counter-line's
  lines: drawn under the written part's speed class, it can sit well
  over what the token song plays the sample at (it sat at 160 to 400
  ms over tunes whose token's shortest usual note is 60 to 140), and
  whether it does for the chord parts and the bass is not measured.
- **A tune's note before a rest of a bar or more stops at its bar's
  end.** Since round 140 a tune's note is measured to the next note
  where that starts in its bar or the next, so a note held before a
  bar that opens with a rest sounds over the bar line. Where the tune
  then rests a whole bar or more the note is still measured to its
  own bar's end, and the game's may ring past it (its Terra's tune
  holds the last note before a long rest six and a half beats, two
  and a half of them past the bar line). Whether a note is held is
  the token song's rate for its gap class since round 141: the notes
  before a bar's opening rest are carried over the line in 0.89 of
  the cases at the median (FFVI's 0.75), and song by song the written
  tune sounds over 0.03 more of its notes past a bar line than its
  token song's tune in 24 of 62 songs and over 0.03 fewer in 8 (its
  bars open with a rest more often than the game's). A part that doubles or
  carries the tune's bar takes the notes as they sound and a voice's
  note ends at its next (the render): where the part's own next bar
  opens with a rest, its copy rings on with the tune.
- **The band takes the tune up less than the words say.** Since round
  139 a part plays the tune's bar (doubled, the theme phrase carried,
  a half-bar cell taken up) only where its own bar then keeps within
  its token song's onsets for the part of the form. Over the 68 Song
  Check 100 songs the bass is given 134 bars of the tune to double and
  doubles 89, the accompaniment 61 and 32; of the half-bar cells handed
  on, the bass takes up 44 of 63 and the accompaniment 25 of 36. The
  `tune_doubling`, `theme_doubling` and `cell_handoffs` words' shares
  are FFVI's over all its songs; what they come to in a song whose
  bass plays eight notes a bar under a tune of two is not counted. The
  counter-line's are tested against its own onsets too since round 143
  (70 bars fewer over the Song Check 100 songs).
- **The tune's grain is not its token song's.** Since round 138 a tune
  bar drawn within its part of the form's own onsets is not held to the
  pooled `tune_grain` word (a share over the whole tune, which a bar of
  one note cannot meet alone): its notes fall on or off the beat as the
  bar table has bars of that density in the song's feel and tempo class.
  Bar for bar the written tunes then sit near the game's (bars of two
  notes all on the beat 0.57 against 0.53, of three or four 0.34
  against 0.35; five to eight notes 0.52 off the beat against 0.51),
  but song by song the tune's share of notes off the beat is within a
  tenth of its token song's tune's in 28 of 59 songs and 0.05 under it
  at the median: the token carries no grain of its song's tune. Since
  round 147 it carries the tune's share of notes on the places finer
  than the half beat (a quarter of the beat, a third, finer), and a
  tune written in its token song's feel keeps under each; its share on
  the half beat is still the bar table's.
- **A song is written in its token song's feel; its parts' bars are
  still each drawn on their own.** Until round 148 a written song's feel
  was the pooled `feels` word's draw: 21 of the 68 Song Check 100 songs
  and 120 of 400 seeds were written in the other feel than their FFVI
  song's (ten test songs in triple feel on a duple song's token, eleven
  duple on a triple song's), their tunes not held to their song's places
  (round 147) and their kits drawing none of their song's bars. Since
  round 148 the plan takes the feel the token says (`feel=`), and every
  tune is held to its song's places. The figure tables are drawn by the
  feel a part at a time: a triple song's bass and its kit each draw a
  triple song's bars, and which bar of one sits over which bar of the
  other no word says. Over the 68 songs the bass plays two against the
  kit's three, or three against its two, in 144 of 965 bars where it did
  in 106 of 962 (the game's 217 of 949, a fifth of the bars or more in
  12 songs), and over the 11 songs the round changes that have a bass
  and a kit the bass strikes 0.53 of its notes with a kit hit at the
  median where it struck 0.65 (their FFVI songs' 0.77). Round 149 holds
  the bass and the tune to the kit. A vocabulary counted before round
  147 says no feel on any token and keeps the pooled draw
  (`tokens_say_feel`).
- **A bar moved onto its song's places keeps its notes.** Since round
  147 the notes of a bar that would put the tune over its song's share
  of a place are moved onto the nearest rhythm that keeps the places,
  its pitches as they were: a note that passed between two beats is
  then heard on one. Of the rhythms as near, the one that brings the
  fewest notes onto a beat off the chord is taken; over the 68 Song
  Check 100 songs the tunes' strong-beat notes on the chord go from
  0.479 to 0.473 (the songs' rates 0.58 at the mean), and the chord
  reader hears a change of chord over a held bass note in 292 of 1,310
  changes (0.22) where it heard 277 of 1,298 (0.21; FFVI 0.13), more
  in eleven songs and fewer in six. A bar moved changes what the bar
  and half-bar urns hold, so the bars after it are not always the bars
  they were: in a tune the places change, 0.56 of its bars are the
  same note for note and 0.66 the same rhythm.
- **The half beat is not held.** The token's places are those finer
  than the half beat; a written tune's notes on the half beat are the
  bar table's. The written Terra's tune plays its half-beat note inside
  the kit's triplet in 6 of its bars and starts 8 of its 73 held notes
  on the half beat (the game's Terra: no bar, and one note of 34), and
  its bass played straight eighths against the kit's triplet in 28 of
  its 44 bars, where the game's bass plays the kit's own rhythm in 48
  of the 71 bars both play in and never two against three. Since
  round 149 the token says how often the bass's and the tune's notes
  are struck with the kit, and the written Terra's bass plays on a
  snare hit in every note.
- **The bass and the tune are held to the kit as it is written; the kit
  is held to nothing.** Round 149 moves a line's notes onto the kit's
  hits. Where the written kit's bars are not its song's, the lines stand
  off it: the song on Opening Theme (part 3)'s token plays the kit on a
  roll's bar, the second half of the bar alone, in about half its bars,
  where its song's kit plays the bass's figure hit for hit; its bass
  plays its song's own figure in every bar, no rhythm the bass table
  knows sits on the roll, and 0.47 of its notes fall with a kit hit (the
  game's 1.00). Over 400 seeds 200 bars of 50 basses and 120 bars of 39
  tunes have no rhythm the table knows that brings them nearer.
- **The passes after the writers are not asked the kit.** The theme
  band, the hand-offs and the voices that double the tune's cell rewrite
  bars of the bass and the tune after their writers, and the theme band
  brings a bar back over another bar of the kit. By the bass writer's
  own count 197 of the 232 held basses over 400 seeds are at their
  song's share of notes with a kit hit; as finally written, 167 (69
  before the round). The kit's own share, its hits struck with a bass
  note, is reached in 165 (126): a bass that plays fewer notes than its
  kit strikes is not given more, and no note is left out for it.
- **A note moved onto a kit hit keeps its pitch, and some are left
  out.** As for the places (round 147), a tune's note that passed
  between two beats may be heard on one: over the 59 test tunes on their
  song's arrangement the strong-beat notes on the chord sit 0.12 under
  their song's at the median (0.09 before the round, 0.08 before round
  148). Where no rhythm of as many onsets as the bar has notes puts them
  on the hits, one of fewer does: 526 bass notes in 87 of 400 songs and
  459 tune notes in 94, never past the part of the form's own onsets;
  the bass plays a tenth fewer notes or more in 15 songs (Terra's 296
  become 258, the game's 5.8 a bar).
- **A song without a kit has no such word, and the tune is not held to
  the bass.** 23 of FFVI's 68 songs have no kit, and their written songs
  are as they were. Over the 63 test songs with a tune and a bass the
  tune strikes 0.49 of its notes with a bass note at the median (0.48
  before the round; the game's 0.61) and is 0.20 or more under its own
  song's in 18 (21).
- **A doubling voice's own notes are written for the bass alone, at the
  written line's pace.** Since round 151 a bass's double plays its
  song's short notes and the note between the line's. The tune's
  doubling voice on The Wedding Waltz-Duel (part 4)'s token, the game's
  other doubling with notes of its own (42 of its 167 onsets), is still
  the line again. The between note falls at its place in the written
  line's gap: the song on Overture (part 3)'s token strikes its bass
  line once a bar where the game's strikes it twice, so its pulse is two
  notes a bar where the game's is four.
- **A part's level steps only by its own song's sections.** Since round
  150 a part's level in a part of the form is its token song's part's
  there, where the form's letters are the song's. In a form that is not
  the song's (a token that carries no form: 17 of 400 seeds since
  round 154 plays a short form round again) every part holds one level
  through, and so does a
  part the token has no count for. The token's level is the section's
  median over the song's: a swell inside a section, and a part that
  enters loud and settles, are not in it.
- **A bar the reader could not place stays in the bar tables.** The
  reading counts a song at one tempo. Where a song's band plays a
  passage at another (the opening of The Wedding Waltz-Duel (part 4),
  bars 1 to 10: tune, counter-line and bass strike together 0.52 and
  0.63 of a beat apart), the notes fall between the grid's places and
  are kept where the grid puts them: `1/4 3/4 5/4 7/4`, a bar no song
  plays. Since round 147 such a bar does not stand in a tune whose
  song's tune plays on no quarter of the beat; in another it can,
  within the song's share. A rule that leaves out the bars a song's
  whole band strikes off the grid (a fifth of a grid step or more at
  the mean) takes 58 bars of 18 songs, most of them finer than their
  song's grid and not at another tempo; it was not built.
- **The counter-line beside a tune is held to its places by its
  masks.** Its bar is a mask over the tune's bar; since round 147 a
  bar off its song's places takes the nearest mask the table knows
  that keeps them, and where the table knows none the word is drawn
  again (75 of the 86 such bars over the 68 Song Check 100 songs),
  which gives the bar other onsets and draws the line's notes after
  it again: in a counter-line the places change, 0.35 of its bars are
  the same note for note. The bars the theme band and the hand-offs
  give the line, and the voice beside it, are not asked: counted on
  the part as finally written, 18 of 210 held counter-lines are over
  a share of their song's line's (138 before), by 111 notes of 22,545.
- **A theme stated over a thin part of the form is stated again in a
  busy one.** Since round 138 the theme comes back only where its bars
  keep within the bars' own onsets; a phrase the letters name the theme
  where its head does not is written new and stands as the theme for
  the phrases after it. A song whose first part is an intro of a note a
  bar then has two statements that share no bar, and where the letters
  return the theme once, into a part of the form of another density,
  that return is a new statement: in one of the 23 themed Song Check
  100 songs on their token song's arrangement (a song on Returners) the
  theme comes back by the form's repeat alone. The chords still come
  back with the letters' return (round 134).
- **A theme may be stated where the tune mostly rests.** The theme is
  the first phrase of the first part of the form the tune plays in, and
  since round 124 the tune rests where its token song's rests: in 35 of
  400 plans the theme's four bars are ones the tune rests in for half of
  them or more (Terra's tune enters in the intro's last bar). Since
  round 134 the band no longer brings such an intro's bars back over a
  fuller part of the form, but the chords still come back with the
  return (the intro's one chord for four bars), and what the tune
  brings back is a theme of a bar or two.
- **Only the token and its own song's kit count a half-speed song in
  double time.** Since round 131 Locke's and Blackjack's tokens are
  counted at twice the tempo the reading has them at, so a song
  written on them is a fast song with a kit a writer can strike, and
  since round 145 such a song takes its kit's bars from the kit's bar
  tables counted the same way (kept a second time: `drums@2` and its
  limbs'), so the written Locke's snare plays the game's march. Every
  other table still holds the two songs as read, a slow song: the
  tune's cells, the bass's figures and the tempos word; and every
  other song draws its kit from the tables as read, so the other fast
  songs' kits do not know the march, and the slow songs' still hold
  the two songs' bars at half speed. The kit's tables themselves
  counted in double time moved the kit in 23 of the 68 Song Check 100
  songs and, through the bass that strikes with it, the tune in 9
  (Battle Theme's among them); every table counted so moved 130 of 400
  seeds onto another token song (the tempos word is the plan's first
  draw). The four tables kept twice are 54 KB of the vocabulary's 530.
  A steady kit past sixteen strikes a bar
  in a song at 85 beats a minute or more (Dancing Mad's fifth part,
  Grand Finale's second) is still capped at sixteen: doubled, the song
  would pass the fastest tempo the game is read at. A written tune on
  the two tokens is busier than the game's (2.9 notes a second on
  Blackjack's against 1.4): the tune keeps its own density tier, and a
  medium tune of a fast song is four to six notes a bar.
- **A bar played again enters from wherever the bar before left the
  tune.** Since round 130 a tune's thirds and far moves are kept to its
  token song's shares, and a new bar is entered as FFVI's new bars are
  (by step in 0.49 of the cases, FFVI 0.51; by a fourth or more in 0.22,
  0.22). A bar the tune plays again comes back at its pitch, or where
  the recall_moves word puts it, whatever the bar before ended on: it is
  entered by a fourth or more in 0.31 of the cases at pitch and 0.40
  moved, where FFVI's are in 0.19, because the game's bars mostly come
  back after the bars they followed the first time. The shares say how
  many moves of each class a tune has, not their order beyond the moves
  table's one move of memory: a written tune turns back on its last
  move in 0.61 of its moves where FFVI's does in 0.53, and repeats a
  note after a repeated note in 0.35 where FFVI's does in 0.56. Kept to
  fewer thirds, the tune lands a bar's first note on the chord a little
  less (0.52 of the bars, 0.55 before; FFVI 0.61). A counter-line
  written beside a tune (`writer.counter`) is drawn by its interval to
  the tune; since round 143 its moves of a fourth or more are held to
  its token song's line's share, its thirds and its repeated notes are
  not.
- **A part is asked the first beat, never asked off it.** Since rounds
  133 and 135 the bass and the chord parts strike a bar's first beat at
  least as often as their token song's part does. The share is only
  raised to: a part the game plays off the beat (after-beat chords
  over a bass on the one: Devil's Lab's accompaniment strikes the first
  beat in none of its bars, Techno de Chocobo's in 0.28) is written as
  its drawn bars fall, mostly on it: of the Song Check 100 songs,
  seventeen accompaniments and fourteen basses sit over their token
  song's share by 0.15 or more. The share is the part's over the whole
  song, any voice of it, asked of the written line; the kit is drawn
  with no first beat asked (its kick strikes it in every bar at the
  median, FFVI's 0.93), and a part that plays in under eight bars of
  its token song carries no share.
- **The band does not always spell the plan's chord.** Read back by the
  chord reader, a written song's bar is heard on the plan's root in
  0.66 of its bars and as the plan's chord, root and quality, in 0.35;
  a song planned on six chords is heard on eleven. FFVI's chords are
  the reader's own, so there is no plan to hold them against, but its
  bass strikes a bar's first beat on the root of the chord heard there
  in 0.73 of the bars, and since round 129 the written bass is held to
  its token song's share of that (it was on the plan's root in 0.50).
  That brought the bars heard on the plan's root from 0.66 to 0.70 and
  no further: a plan's power chord or suspended chord leaves its third
  to whatever the tune and the chord parts play over it, the voice
  beside a bass line is drawn by its interval to the line and not by
  the chord, and the chord parts' off-chord tones are their token
  song's tier. The harmony's loops (round 128) and a chord's one
  quality (round 127) are the plan's; what the ear gets of them is the
  writers'. Round 142 put the question part by part. A written
  song's chord changes its shape on a held root in 0.21 of its
  changes, the game's in 0.13, and no one part does it: read with
  any one part left out the share is 0.20 to 0.23 (without the bass
  0.16, on the plan's root in 0.49 of the bars for 0.70), and it
  comes down to the game's only where every part, the tune and the
  counter-line among them, plays again what it played on the chord
  the bar before (0.11 then; the backing alone 0.17). A bar with an
  earlier bar on its root within eight, the root the bass's, sounds
  one of those bars' pitch classes again in 0.71 of the written
  bass's such bars (FFVI's 0.73), 0.37 of the accompaniment's (0.62),
  0.49 of the harmony's (0.67), 0.30 of the tune's (0.48) and 0.25 of
  the counter-line's (0.46). The chord parts are held to their token
  song's share since round 142, as far as a bar of their own rhythm
  is there to play again (0.42 and 0.53); the tune and the
  counter-line are not. Round 144 counted the bars' returns
  themselves: a line plays an earlier bar again note for note, eight
  bars back at most, in 0.26 of the written tune's bars (FFVI's 0.29),
  0.46 of the bass's (0.41), 0.34 of the accompaniment's (0.37) and
  0.14 of the counter-line's (0.28), so the lines come back about as
  often as the game's and the counter-line half as often; what differs
  is that the game's bars come back whole. Where the tune plays an
  earlier bar again the bass plays that bar again too in 0.79 of such
  bars in the game and 0.52 in the written songs, and where the bass
  does the tune does in 0.43 and 0.16: a written tune plays an earlier
  bar again more often where the bass does not (0.24 of such bars; the
  game's 0.13). The chord parts and the counter-line are held to
  their lead since round 144 and the tune to the bass's bars since
  round 146 (below); the bass still comes back by its
  own draws.
- **The tune comes back with the bass only where its urn decides the
  bar, and only as far as its song's count goes.** Round 146 (built as
  an experiment, taken at Song Check 105) has the tune play an earlier
  bar again
  where the bass does, held to its token song's share of such bars,
  the bars in which the bass brings one back from further off and the
  bars in which it stands on the bar before counted apart. A bar a
  theme, a phrase's relation or a pair decides is not touched, the
  bar must keep within its own onsets and sit under the same chord,
  and a song whose bass plays such a bar in under four bars the tune
  plays in has no count for the kind (32 of FFVI's 66 tune tokens
  have none for the bars from further back, 53 none for the bar
  before), so its tune comes back as the urn draws it. Over the Song
  Check 100 songs the tune plays the bass's bar from further back
  again in 0.33 of such bars (0.26 before; FFVI's 0.48), in the 34
  songs with a count in 0.44 against their songs' 0.47, ten of them
  still more than a tenth under. The bass is the bass as its writer
  left it: the theme band, the hand-offs and the bass's last pass
  rewrite bars of it once the tune is written. A bar given moves
  every draw after it, so a tune given one bar is another tune from
  there on (the written Kids Run Through the City, given two, plays
  an earlier bar again in 8 of its 45 bars where it had in 13). The
  written bass stands on one bar more than the game's (the bar before
  again in 0.23 of its bars; 0.14), which is the bass's and not
  touched: the tune is not made to stand with it unless its song's
  tune does.
- **A part comes back with its lead a bar at a time, where the chord is
  the same.** Round 144's hold gives a bar the part's earlier bar
  where its lead plays that bar again, the plan's chord is the same
  under both and the bar keeps within the part's own onsets; a bar on
  its loop's figure, a bar the line rides the bass in, a bar of a part
  of the form played again and a bar that would sit a semitone from
  more notes over it stand. Of the 36 accompaniments with a share in
  the Song Check 100 songs 9 are still more than a tenth under it, of
  the 26 counter-lines 4 and of the 9 harmonies 2. A song whose lead
  plays an earlier bar again in under four bars the part plays in has
  no share (21 of FFVI's 57 accompaniment tokens, 22 of its 52 counter
  tokens), and a part written on its token comes back as it is drawn.
  A part with one note a bar that moved a bar at a time under a bass
  that plays one bar holds its note now, as its song's does (the
  written Terra's harmony through the four bars before the tune
  enters).
- **A chord part plays an earlier bar again only note for note.**
  Round 142's hold gives a bar the notes of an earlier bar where that
  bar has its rhythm, voice by voice, on the plan's same chord in the
  same part of the form and eight bars back at most. FFVI's chord
  parts keep their pitch classes on a chord across another rhythm as
  well (of the accompaniments' bars that sound an earlier bar's pitch
  classes again 0.55 have its rhythm; the written ones' 0.78), and
  that is not written. A bar on its loop's figure, a bar the line
  rides the bass in, a bar of a part of the form played again and a
  bar that would then sit a semitone from the tune stand. So the
  hold reaches its song's share in few parts: of the 58 chord
  parts with a share in the Song Check 100 songs, 14 are within
  a tenth of it as finally written (11 before the round) and 41
  are more than a tenth under it, 17 of them with no bar given.
  The voices written after the hold (those that follow a line by
  the token's stretches) and the passes after them (the theme in
  the band, the hand-offs) change bars it counted.
- **A chord part's richness is the pooled draw.** How many chord
  tones a chord part holds a span (the voicing table is asked under
  it) is the `voicing_habits` word's draw, a habit a song: in the
  Song Check 100 songs' plans it is the token song's part's own habit
  in 14 of 54 accompaniments and 6 of 16 harmonies, and thirteen
  accompaniments are thin where the song's is rich (the written Kids
  Run Through the City's accompaniment, an arpeggio of root, third
  and fifth in the game, walks a voicing of one tone through a part
  of the form: one note eight times a bar). Taken from the token
  (tried in round 142) it re-wrote the tune in 208 of 400 seeds, the
  tune being written over the chord parts and steered by them, and
  moved no measure of the round's; it stands until a round can show
  what it buys. Whatever changes a chord part before the tune is
  written re-writes the tune.
- **A chord's degree is the pooled chain's; only its quality is the
  token song's.** Since round 127 a chord takes the quality its degree
  has in its token song and keeps one quality through the song. Which
  degrees the harmony visits, and in what order, is still the pooled
  chords word's chain: the written Edgar and Sabin sits on its tonic in
  most bars where the game's is on it in two of seventeen, and a
  written song has six distinct chords at the median where FFVI's has
  nine. A degree the token song stays on under four bars carries no
  quality (a chord there keeps what the profile's hold gave it most,
  within its third), and a quality is the degree's own only at 0.6 of
  its beats: Battle Theme's tonic is a power chord for 0.44 of its
  beats and nothing else for a fifth of them, so its tonic chords keep
  what the profile's hold gave them, within their third.
- **A bass has two voices at most, and the other parts' voices still
  draw their layer word.** Since round 126 a bass's second voice does
  what its token song's does (a line of its own, or the line again). A
  third bass voice is not written (Dancing Mad's two readings have
  one), a bass whose two voices alternate keeps the pooled draw
  (Fanfare's), and the second voice's busyness comes from the mask word
  drawn under the line's figure, not from the song's own onsets by
  section. A chord part's or the tune's voices beside the line take
  what they do part by part from the token (rounds 90 and 122) and, in
  the stretches the token leaves them their own, a layer word that is
  still the pooled draw: Edgar and Sabin's two accompaniment voices
  beside the line are lines of their own in the game, and the first
  was drawn a doubling a fourth under.
- **A section's density is a median and an envelope, and the
  counter-line's pace is its notes a bar.** Since round 125 a backing line's figures
  are drawn within half to one and a half times the token song's median
  onsets a bar in the part of the form, and each kit piece within what
  the song strikes of it there; since round 138 the tune's bars keep
  within the same envelope of its own. The bars inside a part of the
  form are not told apart (but the last, where it is a fill or a
  thinning): a line the game plays eleven, five, six and three notes a
  bar is asked for three to nine in each, and a tune's busiest parts of
  the form (over six notes a bar) are written at 0.88 of the game's at
  the median, the bar table's thinner bars being the commoner inside
  the envelope. The writers' grid stops at sixteenths, so a snare the
  game rolls at twenty-eight a bar plays sixteen. The
  counter-line beside a tune keeps within its own envelope since round
  143, its part of the form's bars held to the song's own onsets a bar
  (within half of them), and is still a mask over the tune's bar from
  the pooled `counter_figures` word. A bar the word draws as a rest
  stays one: it sounds in 0.76 of the Song Check 100 songs' bars at the
  median against the game's 0.91. And the token counts how many notes
  a bar, not how close together: in six of the 49 songs with a
  counter-line it still runs sixteenths on a tenth more of its moves
  than the game's line does (The Unforgiven's leaps a fourth or more
  inside a sixteenth 21 times where the game's does twice);
  a voice beside a line follows its line and takes only the last
  bar's fill; and a kit piece the song plays in under three bars in
  four of a part of the form plays by its figures' own chain inside its
  bounds.

- **A written song is not as loud as its game song, and the player
  plays every song at one level** (a product choice, 2026-11-13). The
  balance token once carried its song's rendered loudness and the
  writer held a song's master volume to it (round 59). The shipped
  vocabulary has carried no such word since round 103, and it is not
  put back: measured from rendered songs, the hold's estimate of a
  song's level is several dB out for some songs (on Final Fantasy VI's
  sounds 13 of 150 songs sit more than 5 dB from their token song's
  loudness with it, 3 without). So a file plays at the level its
  parts' own levels give it: over 150 seeds on the player's own sounds
  from -30.3 to -19.7 dBFS, 1.6 dB from its token song's at the median.
  The player levels what it plays, at playback, to the middle of
  Final Fantasy VI's songs (`bitcomposer/player/level.py`, SET →
  LEVEL), so in the player Fanatics and The Mines of Narshe, 7 dB
  apart in the game, play alike; a file opened in another player
  plays as written. What would change it: a song's level measured
  from its own render at writing time, which the generator, having no
  renderer of its own, cannot do; or an estimate that meets the
  render.

- **The Serpent Trench is not written by the player** (round 152; the
  game's own way, met by a product choice). Its tune, read from the
  voice heard as the tune, has no phrase that can come back, the
  player asks every song for a theme that returns, and a plan whose
  tune has nowhere to come back is drawn again, on another token: 6 of
  400 seeds were written on it before round 152, none of 1,400 since.
  Written without the asking (the command line's `--no-carry-theme`)
  it is a song of 33 bars. What would change it: the player asking a
  song for a returning theme only where its token song's tune returns.

- **A theme's return brings its chords over the part's own** (noted at
  round 156; the player's asking). Asked for a theme that returns with
  the band, the plan copies the theme's four bars of chords over the
  bars the theme returns in. Where those bars lie in a part of the
  form with its own harmony (a figure the token song loops, 239 of the
  409 such returns over 400 seeds) the part's harmony gives way for
  them, and where the tune, the bass and the accompaniment cannot
  follow the theme there (their pace in the part is not the theme's:
  86 of the 409) the chords are all that comes back. The song on
  Fanatics's token holds one chord through its second part so: 22 of
  the 173 figures of two bars or more are on one root for it. What
  would change it: a return that leaves a part's own harmony standing,
  or one that brings no chords where the tune cannot come.

