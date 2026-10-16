"""PyInstaller entry for the window. gui.py imports its package relatively,
which fails when PyInstaller runs the file as a loose script, so the
executable starts here and imports the package by name."""
from bitcomposer.gui import main

if __name__ == "__main__":
    main()
