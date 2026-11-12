"""Small synthetic problems, independent of the sample witness schedule."""

import csv
import shutil
from pathlib import Path

import pytest

from timetable_ga.domain import (
    DAYS,
    Assignment,
    Course,
    Event,
    ProblemInstance,
    Room,
    StudentGroup,
    Teacher,
    TimeSlot,
)
from timetable_ga.io import load_problem

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def sample():
    return load_problem(ROOT / "data/sample")


@pytest.fixture
def data_dir(tmp_path):
    return Path(shutil.copytree(ROOT / "data/sample", tmp_path / "data"))


@pytest.fixture
def edit_csv(data_dir):
    def edit(name, mutate):
        path = data_dir / f"{name}.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            rows = list(reader)
        mutate(rows)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, columns)
            writer.writeheader()
            writer.writerows(rows)

    return edit


@pytest.fixture
def tiny():
    """Three events with distinct teachers/groups and two viable lecture rooms."""
    return ProblemInstance(
        teachers=tuple(Teacher(f"T{i}", f"Teacher {i}") for i in range(3)),
        groups=tuple(StudentGroup(f"G{i}", f"Group {i}", 30) for i in range(3)),
        rooms=(
            Room("R1", "Room 1", 40, "lecture"),
            Room("R2", "Room 2", 80, "lecture"),
            Room("LAB", "Lab", 50, "lab"),
            Room("SMALL", "Small room", 10, "lecture"),
        ),
        courses=(Course("C", "Course"),),
        assignments=tuple(
            Assignment(f"A{i}", "C", f"G{i}", f"T{i}", 1, 2, "lecture") for i in range(3)
        ),
        events=tuple(
            Event(f"E{i}", f"A{i}", "C", f"G{i}", f"T{i}", 30, 2, "lecture") for i in range(3)
        ),
        time_slots=tuple(
            TimeSlot(day, period, "morning" if period <= 4 else "afternoon", "", "")
            for day in DAYS
            for period in range(1, 9)
        ),
        teacher_unavailability=frozenset(),
        room_unavailability=frozenset(),
        teacher_preferences=frozenset(),
        dataset_fingerprint="tiny-test-instance",
    )
