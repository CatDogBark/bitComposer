"""bitcomposer — Procedural 16-bit chiptune music generator."""

__version__ = "1.2.0rc3"

# The registry first, then the packs that register their voices into it.
from . import samples, packs  # noqa: E402,F401
