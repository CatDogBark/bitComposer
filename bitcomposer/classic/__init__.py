"""Classic: the 1.x generator, behind a wall and frozen.

Everything Classic needs is in this folder: its composer and the parts' writers, and its own copies of the sounds
(samples/, packs/), the module writer (it_format) and the pattern, drum, echo and mix helpers, as they stood on the
day it was walled off. Nothing here imports from outside this folder but the package's version, which a Classic
song's message records; and nothing here changes again. A fault found in code the writer shares a history with is
put right on the writer's side, not here: `tests/test_classic_lock.py` holds 109 Classic songs to the files they
were, and `tests/test_classic_wall.py` holds the wall.

Classic plays its own sounds and reads no pack file.

The front door is this module: outside code takes the names below from `bitcomposer.classic` and reaches no
deeper. The command line's `--classic` (and through it the player) composes with `compose_song` and writes with
`save_song`; the readers' tools and tests take a Classic song as a known answer, with `theory` for what its plan's
names mean."""
from .. import __version__                          # noqa: F401  the one thing taken from outside: a song's message records it

# The registry first, then the packs that register their voices into it (as the package's root does for the writer's).
from . import samples, packs                        # noqa: E402,F401
from . import theory                                # noqa: E402,F401
from .composer import (SOUNDS, STYLES, compose_and_save, compose_song, resolve_sound, save_song)   # noqa: E402,F401

__all__ = ["SOUNDS", "STYLES", "compose_and_save", "compose_song", "resolve_sound", "save_song", "theory"]
