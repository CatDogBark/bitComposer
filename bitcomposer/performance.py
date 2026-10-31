"""The product's performance of a written song: what the player asks the writer
for and how it presents what comes back. Kept out of `translate/` on purpose.

The writer (`translate.whole`) is tuned against the games and measured by the
tools (`tools/whole.py`, the copy check, the Song Checks); nothing here may
move it. A `Performance` is the one place the default player's choices live:

- what it asks for: a theme that comes back and the band with it, a least
  form length, how many times the loop plays, the tail and the fade;
- the echo: the vocabulary's `echo` word (round 70: the game's volume, delay,
  feedback and the parts that send), drawn on the performance's own stream
  by the writer's own draw (`whole.render.echo_word`, so the two paths cannot
  drift), the sound set's habits where a vocabulary has no such word (an
  import counted before round 70);
- vibrato on held notes of the tune and the counter, as a performance of the
  score after it is written: a bend a row, the figures and the tune untouched.

`Performance.none()` is the writer bare, exactly what `compose_written` did
before this module: the tools' way. `Performance.player()` is the default
player's. A test holds the bare path byte for byte to `whole.compose`, and
another that `translate/` never imports this module.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

ECHO_HABIT = "habit"                  # whole.compose's default: the echo as the sound set's habits give it (the tools' way)

# The player's old vibrato rule, the fallback where a vocabulary has no `vibrato` word (an import counted before round 72)
VIBRATO_HOLD = 0.35                   # seconds a note must sound to take vibrato (the word's count uses the same threshold)
VIBRATO_DELAY = 0.12                  # seconds into the note before it starts
VIBRATO_RISE = 0.25                   # seconds it takes to reach its depth
VIBRATO_DEPTH = 10.0                  # cents either side (the module slides in 1/64 of a semitone, 1.6 cents)
VIBRATO_RATE = 5.5                    # Hz
VIBRATO_STEP = 0.01                   # seconds between bends: the module's row (100 a second)
VIBRATO_PARTS = ("melody", "counter")


@dataclass(frozen=True)
class Performance:
    name: str
    themed: bool                      # the tune's phrases drawn again until its theme comes back
    band_returns: bool                # and the chords, the bass or the accompaniment come back with it
    min_bars: int | None              # a form shorter is drawn again
    max_bars: int | None              # and longer
    loops: int                        # how many times the loop plays in all
    tail_bars: int                    # the loop's first bars once more after the form, fading
    fade: float                       # seconds
    echo: str                         # ECHO_HABIT (the sound set's habit), "song" (the player's policy) or "off"
    vibrato: bool

    @classmethod
    def player(cls) -> "Performance":
        """The default player's: a theme that returns with the band, at least sixteen bars, the loop twice, the
        echo by the song, vibrato on held notes."""
        return cls("player", themed=True, band_returns=True, min_bars=16, max_bars=48, loops=2, tail_bars=4, fade=3.0,
                   echo="song", vibrato=True)

    @classmethod
    def none(cls) -> "Performance":
        """The writer bare, as the tools and the Song Checks have it: nothing asked for, nothing added."""
        return cls("bare", themed=False, band_returns=False, min_bars=12, max_bars=48, loops=1, tail_bars=4, fade=3.0,
                   echo=ECHO_HABIT, vibrato=False)

    def asking(self, carry_theme: bool | None, band_returns: bool | None) -> "Performance":
        """This performance with the two switches as the caller set them (None: as the performance has them)."""
        if carry_theme is None and band_returns is None:
            return self
        return Performance(self.name, self.themed if carry_theme is None else bool(carry_theme),
                           self.band_returns if band_returns is None else bool(band_returns), self.min_bars, self.max_bars,
                           self.loops, self.tail_bars, self.fade, self.echo, self.vibrato)


def echo_stream(seed: int) -> random.Random:
    """The performance's own stream for the echo: apart from the writer's (`whole:SEED:echo`), so the player's draw
    moves nothing of the writing."""
    return random.Random(f"written:{seed}:performance:echo")


def echo_for(plan, seed: int, models: dict | None = None, habits: dict | None = None) -> dict | None:
    """The player's echo for a written song, in the shape `whole.score_of` takes ({"delay", "seconds", "wet",
    "feedback", and the word's "sends" and "dry"}), or None for a dry song: the vocabulary's `echo` word, drawn on the
    performance's own stream by the writer's own draw (`render.echo_word`: the game's echo volume of full, its delay
    in ms, its feedback and the parts that send, one unit a song; round 70), so the player plays the echo the game
    played. Until round 72 the player had drawn its own rule here (a delay by tempo and density, a wetness name over
    `score.ECHO_WET` 0.4): 0.24 to 0.6 of full against FFVI's 0.20 in every song. Where a vocabulary has no `echo`
    word (an import counted before round 70), the sound set's habits stand, as they do for the writer bare
    (`render.echo_of`, Classic's way), on the same stream; `describe` says which."""
    from .translate.whole import render as render_mod
    rng = echo_stream(seed)
    if (models or {}).get("echo"):
        echo = render_mod.echo_word(models, plan, rng)
        if echo is not None:
            echo["from"] = "word"
        return echo
    echo = render_mod.echo_of(habits or {}, plan.bpm, rng)
    if echo is not None:
        echo["from"] = "habit"
        plan.log.append(f"performance: echo {echo['delay']} ({echo['seconds'] * 1000:.0f} ms) at {echo['wet']:.2f} of full, "
                        f"feedback {echo['feedback']:.2f}: the sound set's habit, the vocabulary having no echo word")
    else:
        plan.log.append("performance: no echo (the sound set's habit, the vocabulary having no echo word)")
    return echo


def vibrato_stream(seed: int) -> random.Random:
    """The performance's own stream for the vibrato: the words a part, then each held note's draw."""
    return random.Random(f"written:{seed}:performance:vibrato")


def vibrato_words(models: dict | None, plan, rng: random.Random) -> dict | None:
    """The `vibrato` word drawn for each of VIBRATO_PARTS in the band (round 72: a part's share of held notes carrying
    vibrato in each length class, its depth in cents, its rate in Hz, its onset in seconds; one unit a song a part,
    counted from the game's pitch writes while a note sounds): {role: {"shares", "depth", "rate", "onset"}}, or None
    where the vocabulary has no such word (the old rule then stands)."""
    from .translate import rhythm
    from .translate.whole.plan import _draw
    if not (models or {}).get("vibrato"):
        return None
    out = {}
    for role in VIBRATO_PARTS:
        if role not in plan.band:
            continue
        outcome = _draw(models, "vibrato", (role,), rng, plan.log)
        word = rhythm.vibrato_word(outcome)
        if word is None:
            continue
        out[role] = word
        shares = "/".join("-" if s is None else f"{s:.1f}" for s in word["shares"])
        plan.log.append(f"performance: the {role}'s vibrato (vibrato): shares {shares} of its held notes by length class, "
                        f"{word['depth']:.0f} cents at {word['rate']:.1f} Hz from {word['onset']:.1f} s in")
    return out


def vibrato(score, plan, first: dict, words: dict | None = None, rng: random.Random | None = None) -> int:
    """Vibrato on the held notes of the tune and the counter, as bends a row (the module slides the pitch a row at a
    time; 1/64 of a semitone a step). With `words` (vibrato_words), a held note takes it with the word's share for its
    length class (drawn on `rng`), at the word's depth and rate from the word's onset, rising over one cycle (FFVI's
    first swing is 0.41 of its depth at the median, round 72's measure); without, the old rule: every held note, after VIBRATO_DELAY, a sine of
    VIBRATO_RATE rising to VIBRATO_DEPTH cents over VIBRATO_RISE. A performance of the written score, never of the
    writing: no note moves, starts or ends differently. Returns how many notes took it."""
    from .translate.reading import vibrato_class
    voices = {}
    for role in VIBRATO_PARTS:
        if role in first:
            for v in range(first[role], first[role] + plan.voices.get(role, 1)):
                voices[v] = role
    count = 0
    for n in score.notes:
        if n.voice not in voices or n.end is None or n.noise or n.bends or n.end - n.start < VIBRATO_HOLD:
            continue
        if words is not None:
            word = words.get(voices[n.voice])
            if word is None:
                continue
            share = word["shares"][vibrato_class(n.end - n.start)]
            if not share or rng.random() >= share:
                continue
            depth, rate, delay = word["depth"], word["rate"], word["onset"]
            if depth <= 0 or rate <= 0:
                continue
            rise_s = 1.0 / rate
        else:
            depth, rate, delay, rise_s = VIBRATO_DEPTH, VIBRATO_RATE, VIBRATO_DELAY, VIBRATO_RISE
        bends = []
        t = delay
        while n.start + t < n.end - VIBRATO_STEP:
            rise = min(1.0, (t - delay) / rise_s) if rise_s > 0 else 1.0
            cents = depth * rise * math.sin(2 * math.pi * rate * (t - delay))
            bends.append((n.start + t, max(1, round(n.pitch * 2 ** (cents / 1200.0)))))
            t += VIBRATO_STEP
        if bends:
            n.bends = bends
            count += 1
    if count:
        plan.log.append(f"performance: vibrato on {count} held notes of the tune and the counter"
                        + (" (the vocabulary's word)" if words is not None else " (the player's rule, the vocabulary having no vibrato word)"))
    return count


def perform(out: dict, performance: Performance, models: dict | None = None, seed: int | None = None) -> dict:
    """What the performance adds to a written song after the writing: the vibrato, by the vocabulary's word where it
    has one (drawn on the performance's own stream; `models` and `seed` given), the old rule where not. Returns what
    it did, for the song's message and its info: {"vibrato": notes, "vibrato_from": "word" | "rule" | None}."""
    done = {"vibrato": 0, "vibrato_from": None}
    if performance.vibrato:
        words = vibrato_words(models, out["plan"], vibrato_stream(seed)) if seed is not None else None
        done["vibrato_from"] = "word" if words is not None else "rule"
        done["vibrato"] = vibrato(out["score"], out["plan"], out["first"], words, vibrato_stream(seed) if seed is not None else None)
    return done


def describe(performance: Performance, echo: dict | None, done: dict) -> str:
    """One line for the song's message: what the performance asked for and added."""
    if performance.name == "bare":
        return "performance: none (the writer bare, as the Song Checks have it)"
    parts = []
    if performance.themed:
        parts.append("the theme returns" + (" with the band" if performance.band_returns else ""))
    if echo:
        parts.append(f"echo {echo['delay']} at {echo['wet']:.2f} of full"
                     + (" (the vocabulary's word)" if echo.get("from") == "word" else " (the sound set's habit)" if echo.get("from") == "habit" else ""))
    else:
        parts.append("no echo")
    if done.get("vibrato"):
        parts.append(f"vibrato on {done['vibrato']} held notes"
                     + (" (the vocabulary's word)" if done.get("vibrato_from") == "word" else " (the player's rule, no vibrato word)" if done.get("vibrato_from") == "rule" else ""))
    elif performance.vibrato and done.get("vibrato_from") == "word":
        parts.append("no vibrato (the vocabulary's word)")
    parts.append(f"the loop {'twice' if performance.loops == 2 else str(performance.loops) + ' times'}")
    return "performance: " + ", ".join(parts)
