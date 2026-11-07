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
  sizzle, the Battle Theme's pitched rattle, Wild West's blip). Under its
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
- **A voice beside a line changes instrument, not register, by stretch.**
  Since round 92 its layer entry carries its own stretches and the render
  plays each note on its stretch's sample; its register stays what its
  relation to the line gives it (a doubling voice the line's at the
  interval, an apart voice its span), where the game's voice may also
  move register with its instrument.
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
- **Parts written apart clash more than FFVI's.** Each part holds its
  clashes share against the parts written before it since round 94 (the
  tune in its draws and recalls, the counter in its interval draws, the
  chord parts in their voicing tones), which halved the counter's pairs
  (against the tune 0.06 of its strong onsets, FFVI 0.05; against the bass
  0.07, FFVI 0.05). The rest sits where no word is held: the tune's line
  keeps a floor from its returning cells and endings (0.13 of its strong
  onsets against the bass and chord parts, FFVI 0.08), a chord voicing of
  one tone has no clear tone to go to (the accompaniment 0.08 against
  0.04), a parallel voice at a third follows its line into the band's
  semitones (a tune's parallel third in Whole 4 on 0.40 of its beats, the
  tune itself on 0.12), and an apart voice in a dense band finds no clear
  tone within VOICE_TRIES draws. A word for how FFVI's parallels bend at a
  clash, and a placement for returning cells that looks at the band, would
  carry it further.
- **The counter is more diatonic than FFVI's.** A counter by the voice
  words takes scale steps from the tune's note, so it leaves the scale
  only where the tune does: 0.06 to 0.08 of its line's notes against
  FFVI's 0.14 to 0.26 (round 93's count). Only a counter written as a
  line of its own holds its off_scale draw. A semitone form of the
  interval word against a tune note on the scale would carry the rest.
- **A voice beside the tune at a third stays on the scale.** A parallel
  voice is written at its generic interval from the line, in the scale,
  where FFVI's doublings leave it with the tune and beyond; since round 94
  a double at a unison or octaves copies the line exactly, altered notes
  and all, but a third, fourth or fifth is still taken in the scale. The
  relation word has no exact-interval form yet for those.

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
