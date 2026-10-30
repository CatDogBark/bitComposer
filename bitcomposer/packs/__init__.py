"""
Style packs: an instrument set paired with the arrangement habits of the
game scores it imitates. A pack sits inside a palette (the sound chip) and
narrows what the composer draws. Each pack is one module holding its voices
and its PACK table; importing this package registers every pack's voices with
the sample registry. The composer reads habits through pack_weights().
"""
from .. import samples as _samples
from . import bit, ffvi, mana, evermore, megamanx

_MODULES = [bit, ffvi, mana, evermore, megamanx]
for _m in _MODULES:
    _samples.register_presets(_m.PRESETS, _m.RELEASE)

PACKS = {"bit": bit.PACK, "ffvi": ffvi.PACK, "mana": mana.PACK, "evermore": evermore.PACK, "megamanx": megamanx.PACK}

PACK_NAMES = list(PACKS)

RANGES = {}                           # every built-in pitched voice -> (low, high) MIDI, from each pack's RANGES
for _m in _MODULES:
    RANGES.update(getattr(_m, "RANGES", {}))

# A voice's speed, notes a second it can carry, from its measured attack: a struck voice takes anything; a swell
# that needs 200 ms to arrive cannot be played at eight a second (the attack never reaches its body). The classes are
# the sample_speeds table's (2, 3, 4, 6, 8, 12, 24).
_SPEED_BY_ONSET = ((10, 12.0), (30, 8.0), (60, 6.0), (120, 4.0), (200, 3.0))
_FLOOR_CLASSES = (0.04, 0.06, 0.08, 0.12, 0.16, 0.24, 0.4)   # the sample_lengths table's classes, seconds
_profiles: dict = {}


def profile(name: str) -> dict | None:
    """What the writer may ask of a built-in voice (phase 6), in the terms an imported game's tables answer in for the
    game's own samples: {"range": (low, high) MIDI, "speed": notes a second, "floor": the shortest note, seconds}. The
    range is the pack's RANGES entry; the speed and the floor come from the voice's measured attack (its onset, struck
    or not). None for a voice no pack ranges (a drum, a pack file's own sample, the chip palette's waveforms)."""
    if name in _profiles:
        return _profiles[name]
    rng = RANGES.get(name)
    if rng is None:
        _profiles[name] = None
        return None
    inst = _samples.generate_instrument(name)
    onset = 0.0 if inst["struck"] else float(inst["onset_ms"])
    speed = 24.0 if inst["struck"] else next((v for top, v in _SPEED_BY_ONSET if onset <= top), 2.0)
    need = 1.5 * onset / 1000.0
    floor = next((c for c in _FLOOR_CLASSES if c >= need), _FLOOR_CLASSES[-1])
    _profiles[name] = {"range": (int(rng[0]), int(rng[1])), "speed": speed, "floor": floor}
    return _profiles[name]


def pack_weights(pack: str | None, habit: str):
    """The pack's weights for a habit, or None to draw the plain way."""
    if not pack:
        return None
    return PACKS[pack]["habits"].get(habit)


def pack_value(pack: str | None, habit: str, default):
    if not pack:
        return default
    return PACKS[pack]["habits"].get(habit, default)
