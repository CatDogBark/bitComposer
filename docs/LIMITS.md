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
  token song's since round 124). The counter follows the tune's figures and takes no
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
- **A loop is the token song's or none.** Since round 121 a backing
  voice plays its figure again where its token song's voice loops, by
  the form's letters; where the plan keeps its own form (a token form
  short of the bars asked, 14 of 400 seeds) no loop is taken, and a
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
  a voice. And a song whose form is not its token song's (four FFVI
  forms are under the sixteen bars a song is asked, six tokens carry no
  form) keeps the pooled textures and entrances.
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
- **A section's density is a median and an envelope, and the tune's and
  the counter's are not held.** Since round 125 a backing line's figures
  are drawn within half to one and a half times the token song's median
  onsets a bar in the part of the form, and each kit piece within what
  the song strikes of it there. The bars inside a part of the form are
  not told apart (but the last, where it is a fill or a thinning): a
  line the game plays eleven, five, six and three notes a bar is asked
  for three to nine in each. The writers' grid stops at sixteenths, so
  a snare the game rolls at twenty-eight a bar plays sixteen. The tune
  keeps its own density and takes only the song's tier against it; the
  counter-line follows the tune's figures and rests more than the
  game's (it sounds in 0.72 of the Song Check 100 songs' bars against
  0.91); a voice beside a line follows its line and takes only the last
  bar's fill; and a kit piece the song plays in under three bars in
  four of a part of the form plays by its figures' own chain inside its
  bounds.
