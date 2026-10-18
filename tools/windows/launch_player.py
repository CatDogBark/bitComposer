"""PyInstaller entry for the player. The package imports itself relatively,
which fails when PyInstaller runs a module as a loose script, so the
executable starts here and imports the package by name."""
import sys
from bitcomposer.player.window import main

if __name__ == "__main__":
    sys.exit(main())
