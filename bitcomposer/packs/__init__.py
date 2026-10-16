"""
Style packs: an instrument set paired with the arrangement habits of the
game scores it imitates. A pack sits inside a palette (the sound chip) and
narrows what the composer draws. Each pack is one module holding its voices
and its PACK table; importing this package registers every pack's voices with
the sample registry. The composer reads habits through pack_weights().
"""
from .. import samples as _samples
from . import ffvi, mana, evermore, megamanx

_MODULES = [ffvi, mana, evermore, megamanx]
for _m in _MODULES:
    _samples.register_presets(_m.PRESETS, _m.RELEASE)

PACKS = {"ffvi": ffvi.PACK, "mana": mana.PACK, "evermore": evermore.PACK, "megamanx": megamanx.PACK}

PACK_NAMES = list(PACKS)


def pack_weights(pack: str | None, habit: str):
    """The pack's weights for a habit, or None to draw the plain way."""
    if not pack:
        return None
    return PACKS[pack]["habits"].get(habit)


def pack_value(pack: str | None, habit: str, default):
    if not pack:
        return default
    return PACKS[pack]["habits"].get(habit, default)
