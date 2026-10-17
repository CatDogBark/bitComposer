"""bitcomposer — Procedural 16-bit chiptune music generator."""

__version__ = "0.9.1"

# The registry first, then the packs that register their voices into it.
from . import samples, packs  # noqa: E402,F401
