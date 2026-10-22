"""A song's bass replaced by one written from the bass table: tools/table_parts.py with --parts bass (kept as the
name the phase 3 record uses).

    python tools/table_bass.py FILE.spc --db READINGS.db -o OUT.it [--seed 1] [--seconds 60] [--title T] [--figures OUT.json] [--stems DIR]
"""
import sys

import table_parts


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    return table_parts.main(argv + ["--parts", "bass"])


if __name__ == "__main__":
    sys.exit(main())
