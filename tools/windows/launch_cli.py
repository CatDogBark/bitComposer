"""PyInstaller entry for the command line (see launch_gui.py)."""
import sys
from bitcomposer.cli import main

if __name__ == "__main__":
    sys.exit(main())
