"""PyInstaller entry for the player (see launch_gui.py for why a launcher)."""
import sys
from bitcomposer.player.window import main

if __name__ == "__main__":
    sys.exit(main())
