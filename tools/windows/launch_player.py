"""PyInstaller entry for the player. The package imports itself relatively,
which fails when PyInstaller runs a module as a loose script, so the
executable starts here and imports the package by name.

It is the Windows build's worker too. The SPC import runs `python -m
bitcomposer.spc` in a process of its own, and the frozen executable has no
-m: started with library.WORKER first, it runs that command instead of the
window (packs/library.py). The import's pool starts its helpers the
Windows way, by running this executable again, so freeze_support() comes
before anything else: it is what sends a helper to its task, where
otherwise every helper would open a player."""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from bitcomposer.packs.library import WORKER, run_worker
    if sys.argv[1:2] == [WORKER]:
        sys.exit(run_worker(sys.argv[2:]))
    from bitcomposer.player.window import main
    sys.exit(main())
