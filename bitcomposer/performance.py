"""The product's performance of a written song: what the player asks the writer
for and how it presents what comes back. Kept out of `translate/` on purpose.

The writer (`translate.whole`) is tuned against the games and measured by the
tools (`tools/whole.py`, the copy check, the Song Checks); nothing here may
move it. A `Performance` is the one place the default player's choices live:

- what it asks for: a theme that comes back and the band with it, a least
  form length, how many times the loop plays, the tail and the fade;
- the echo: the player's own habit, drawn per song from the song's tempo and
  density, where the vocabulary has no word for it (an echo word counted
  from the readings is a vocabulary gap, `docs/idiom/phase-6-generator.md`);
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

VIBRATO_HOLD = 0.35                   # seconds a note must sound to take vibrato
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


def tempo_class(bpm: float) -> str:
    return "slow" if bpm < 95 else "fast" if bpm >= 140 else "medium"


def density_of(plan) -> float:
    """How busy the song's parts are, 0 to 1: the share of the balance token's habit words that say dense."""
    words = [str(h).split()[0] for h in (getattr(plan, "habits", None) or {}).values() if h]
    if not words:
        return 0.5
    return sum(1 for w in words if w == "dense") / len(words)


def echo_for(plan, seed: int) -> dict | None:
    """The player's echo for a written song, drawn on its own stream from the song's character, in the shape
    `whole.score_of` takes: {"delay", "seconds", "wet", "feedback"}, or None for a dry song. Slower and sparser songs
    are wetter and longer; fast and busy ones lighter and shorter, and more often dry. The same mechanism Classic's
    packs use (`whole.echo_of`), chosen by the song instead of the set, and nothing learned from any game."""
    from .echo import ECHO_DELAYS, ECHO_WETNESS
    from .score import ECHO_STEP, ECHO_WET
    rng = random.Random(f"written:{seed}:performance:echo")
    tempo, dense, band = tempo_class(plan.bpm), density_of(plan), len(plan.band)
    chance = {"slow": 0.85, "medium": 0.65, "fast": 0.45}[tempo]
    if dense >= 0.5:
        chance -= 0.15
    if band <= 3:
        chance += 0.10
    if rng.random() >= chance:
        plan.log.append(f"performance: no echo ({tempo}, {'dense' if dense >= 0.5 else 'open'}, {band} parts, chance {chance:.2f})")
        return None
    delays = {"slow": {"dotted": 4, "eighth": 3, "slap": 1}, "medium": {"eighth": 4, "slap": 3, "dotted": 2},
              "fast": {"slap": 5, "eighth": 2}}[tempo]
    if dense >= 0.5:
        wets = {"light": 3, "normal": 2}
    elif band <= 3:
        wets = {"wet": 2, "normal": 2, "light": 1}
    else:
        wets = {"normal": 3, "light": 1, "wet": 1}
    delay = rng.choices(list(delays), list(delays.values()))[0]
    wet = rng.choices(list(wets), list(wets.values()))[0]
    feedback = rng.uniform(0.35, 0.5) if dense >= 0.5 else rng.uniform(0.45, 0.65)
    row_s = 60.0 / (plan.bpm * 4)
    steps = max(1, min(15, round(ECHO_DELAYS.get(delay, 2) * row_s / ECHO_STEP)))
    plan.log.append(f"performance: echo {delay} ({steps * ECHO_STEP * 1000:.0f} ms), {wet}, feedback {feedback:.2f} "
                    f"({tempo}, {'dense' if dense >= 0.5 else 'open'}, {band} parts)")
    return {"delay": delay, "seconds": steps * ECHO_STEP, "wet": ECHO_WETNESS.get(wet, 1.0) * ECHO_WET, "feedback": feedback}


def vibrato(score, plan, first: dict) -> int:
    """Vibrato on the held notes of the tune and the counter, as bends a row (the module slides the pitch a row at a
    time; 1/64 of a semitone a step): after VIBRATO_DELAY, a sine of VIBRATO_RATE rising to VIBRATO_DEPTH cents over
    VIBRATO_RISE. A performance of the written score, never of the writing: no note moves, starts or ends differently.
    Returns how many notes took it."""
    voices = set()
    for role in VIBRATO_PARTS:
        if role in first:
            voices.update(range(first[role], first[role] + plan.voices.get(role, 1)))
    count = 0
    for n in score.notes:
        if n.voice not in voices or n.end is None or n.noise or n.bends or n.end - n.start < VIBRATO_HOLD:
            continue
        bends = []
        t = VIBRATO_DELAY
        while n.start + t < n.end - VIBRATO_STEP:
            rise = min(1.0, (t - VIBRATO_DELAY) / VIBRATO_RISE)
            cents = VIBRATO_DEPTH * rise * math.sin(2 * math.pi * VIBRATO_RATE * (t - VIBRATO_DELAY))
            bends.append((n.start + t, max(1, round(n.pitch * 2 ** (cents / 1200.0)))))
            t += VIBRATO_STEP
        if bends:
            n.bends = bends
            count += 1
    if count:
        plan.log.append(f"performance: vibrato on {count} held notes of the tune and the counter")
    return count


def perform(out: dict, performance: Performance) -> dict:
    """What the performance adds to a written song after the writing: the vibrato. Returns what it did, for the
    song's message and its info: {"vibrato": notes}."""
    done = {"vibrato": 0}
    if performance.vibrato:
        done["vibrato"] = vibrato(out["score"], out["plan"], out["first"])
    return done


def describe(performance: Performance, echo: dict | None, done: dict) -> str:
    """One line for the song's message: what the performance asked for and added."""
    if performance.name == "bare":
        return "performance: none (the writer bare, as the Song Checks have it)"
    parts = []
    if performance.themed:
        parts.append("the theme returns" + (" with the band" if performance.band_returns else ""))
    parts.append("echo " + echo["delay"] if echo else "no echo")
    if done.get("vibrato"):
        parts.append(f"vibrato on {done['vibrato']} held notes")
    parts.append(f"the loop {'twice' if performance.loops == 2 else str(performance.loops) + ' times'}")
    return "performance: " + ", ".join(parts)
