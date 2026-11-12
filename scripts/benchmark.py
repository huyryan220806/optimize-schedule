"""Repository entry point; install the package with pip install -e '.[dev]' first."""

from timetable_ga.benchmark import main

if __name__ == "__main__":
    raise SystemExit(main())
