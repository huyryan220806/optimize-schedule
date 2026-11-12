"""Strict CSV loading, normalized dataset identity, and schedule validation I/O."""

import csv
import hashlib
import json
import re
from datetime import time
from itertools import pairwise
from pathlib import Path

from timetable_ga.candidates import build_candidates
from timetable_ga.domain import (
    DAYS,
    ROOM_TYPES,
    Assignment,
    Course,
    Placement,
    ProblemInstance,
    Room,
    ScheduledEvent,
    StudentGroup,
    Teacher,
    TimeSlot,
    expand_events,
)

SCHEMAS = {
    "teachers": ("teacher_id", "name"),
    "student_groups": ("group_id", "name", "size"),
    "rooms": ("room_id", "name", "capacity", "room_type"),
    "courses": ("course_id", "name"),
    "assignments": (
        "assignment_id",
        "course_id",
        "group_id",
        "teacher_id",
        "sessions_per_week",
        "duration_periods",
        "required_room_type",
    ),
    "time_slots": ("day", "period", "block", "start", "end"),
    "teacher_unavailability": ("teacher_id", "day", "period"),
    "room_unavailability": ("room_id", "day", "period"),
    "teacher_preferences": ("teacher_id", "day", "period", "preference"),
}
SCHEDULE_COLUMNS = (
    "event_id",
    "assignment_id",
    "course_id",
    "group_id",
    "teacher_id",
    "day",
    "start_period",
    "duration_periods",
    "room_id",
)
INTEGER_COLUMNS = {"size", "capacity", "sessions_per_week", "duration_periods", "period"}
Row = dict[str, str | int]


class DataValidationError(ValueError):
    """Input error with a file, record number, and field when applicable."""


def _read_csv(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames
            if headers is None or len(headers) != len(set(headers)):
                raise DataValidationError(f"{path.name}: missing header or duplicate columns")
            if set(headers) != set(columns):
                raise DataValidationError(
                    f"{path.name}: schema mismatch; missing={sorted(set(columns) - set(headers))}, "
                    f"unexpected={sorted(set(headers) - set(columns))}"
                )
            rows = []
            for number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise DataValidationError(f"{path.name}: row {number}: wrong column count")
                clean = {key: value.strip() for key, value in row.items()}
                for key, value in clean.items():
                    if not value:
                        raise DataValidationError(f"{path.name}: row {number}: {key} is empty")
                rows.append(clean)
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataValidationError(f"{path.name}: cannot read CSV: {exc}") from exc


def _integer(value: str, context: str, minimum: int, maximum: int | None = None) -> int:
    if not re.fullmatch(r"[+-]?[0-9]+", value):
        raise DataValidationError(f"{context}: expected integer, got {value!r}")
    number = int(value)
    if number < minimum or (maximum is not None and number > maximum):
        raise DataValidationError(
            f"{context}: value {number} outside {minimum}..{maximum or 'inf'}"
        )
    return number


def _normalize(name: str, rows: list[dict[str, str]]) -> list[Row]:
    normalized = []
    seen: set[tuple[str | int, ...]] = set()
    columns = SCHEMAS[name]
    key_columns = (
        columns[:1]
        if name in {"teachers", "student_groups", "rooms", "courses", "assignments"}
        else tuple(
            column for column in columns if column in {"teacher_id", "room_id", "day", "period"}
        )
    )
    for number, row in enumerate(rows, 2):
        context = f"{name}.csv: row {number}"
        item: Row = dict(row)
        for key in INTEGER_COLUMNS.intersection(row):
            maximum = 4 if key == "duration_periods" else 8 if key == "period" else None
            item[key] = _integer(row[key], f"{context}: {key}", 1, maximum)
        if "day" in row and row["day"] not in DAYS:
            raise DataValidationError(f"{context}: unknown day {row['day']!r}")
        for key in ("room_type", "required_room_type"):
            if key in row and row[key] not in ROOM_TYPES:
                raise DataValidationError(f"{context}: invalid {key} {row[key]!r}")
        if "preference" in row and row["preference"] != "avoid":
            raise DataValidationError(f"{context}: preference must be 'avoid'")
        if name == "time_slots":
            expected = "morning" if item["period"] <= 4 else "afternoon"
            if row["block"] != expected:
                raise DataValidationError(f"{context}: block must be {expected}")
            for key in ("start", "end"):
                try:
                    if not re.fullmatch(r"[0-9]{2}:[0-9]{2}", row[key]):
                        raise ValueError("expected HH:MM")
                    time.fromisoformat(row[key])
                except ValueError as exc:
                    raise DataValidationError(
                        f"{context}: invalid {key} time {row[key]!r}"
                    ) from exc
            if row["start"] >= row["end"]:
                raise DataValidationError(f"{context}: start must be before end")
        identity = tuple(item[key] for key in key_columns)
        if identity in seen:
            raise DataValidationError(f"{context}: duplicate key {identity}")
        seen.add(identity)
        normalized.append(item)
    if name in {"teachers", "student_groups", "rooms", "courses", "assignments", "time_slots"}:
        if not normalized:
            raise DataValidationError(f"{name}.csv: table must contain at least one record")
    return normalized


def _foreign_keys(tables: dict[str, list[Row]]) -> None:
    ids = {
        "teacher_id": {row["teacher_id"] for row in tables["teachers"]},
        "group_id": {row["group_id"] for row in tables["student_groups"]},
        "course_id": {row["course_id"] for row in tables["courses"]},
        "room_id": {row["room_id"] for row in tables["rooms"]},
    }
    slots = {(row["day"], row["period"]) for row in tables["time_slots"]}
    for name in (
        "assignments",
        "teacher_unavailability",
        "room_unavailability",
        "teacher_preferences",
    ):
        for number, row in enumerate(tables[name], 2):
            for column, valid_ids in ids.items():
                if column in row and row[column] not in valid_ids:
                    raise DataValidationError(
                        f"{name}.csv: row {number}: unknown {column} {row[column]!r}"
                    )
            if "day" in row and (row["day"], row["period"]) not in slots:
                raise DataValidationError(f"{name}.csv: row {number}: time slot does not exist")
    for day in DAYS:
        daily = sorted(
            (row for row in tables["time_slots"] if row["day"] == day),
            key=lambda row: row["period"],
        )
        for earlier, later in pairwise(daily):
            if earlier["end"] > later["start"]:
                raise DataValidationError(
                    f"time_slots.csv: {day}: times overlap or are out of order"
                )


def load_problem(data_dir: str | Path) -> ProblemInstance:
    """Load exactly the nine contracted CSVs; never open a manifest or witness."""
    root = Path(data_dir)
    tables = {
        name: _normalize(name, _read_csv(root / f"{name}.csv", columns))
        for name, columns in SCHEMAS.items()
    }
    _foreign_keys(tables)
    for name, rows in tables.items():
        rows.sort(key=lambda row: tuple(row[column] for column in SCHEMAS[name]))
    payload = json.dumps(tables, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    groups = tuple(StudentGroup(**row) for row in tables["student_groups"])
    assignments = tuple(Assignment(**row) for row in tables["assignments"])
    problem = ProblemInstance(
        teachers=tuple(Teacher(**row) for row in tables["teachers"]),
        groups=groups,
        rooms=tuple(Room(**row) for row in tables["rooms"]),
        courses=tuple(Course(**row) for row in tables["courses"]),
        assignments=assignments,
        events=expand_events(assignments, groups),
        time_slots=tuple(TimeSlot(**row) for row in tables["time_slots"]),
        teacher_unavailability=frozenset(
            (row["teacher_id"], row["day"], row["period"])
            for row in tables["teacher_unavailability"]
        ),
        room_unavailability=frozenset(
            (row["room_id"], row["day"], row["period"]) for row in tables["room_unavailability"]
        ),
        teacher_preferences=frozenset(
            (row["teacher_id"], row["day"], row["period"]) for row in tables["teacher_preferences"]
        ),
        dataset_fingerprint=fingerprint,
    )
    return build_candidates(problem)


def load_schedule(path: str | Path, problem: ProblemInstance) -> tuple[ScheduledEvent, ...]:
    """Keep duplicate/unknown event IDs for H0; reject altered event metadata."""
    path = Path(path)
    rows = _read_csv(path, SCHEDULE_COLUMNS)
    events = {event.event_id: event for event in problem.events}
    schedule = []
    for number, row in enumerate(rows, 2):
        context = f"{path.name}: row {number}"
        start = _integer(row["start_period"], f"{context}: start_period", -(2**31), 2**31 - 1)
        duration = _integer(row["duration_periods"], f"{context}: duration_periods", 1, 4)
        event = events.get(row["event_id"])
        if event:
            for column in ("assignment_id", "course_id", "group_id", "teacher_id"):
                if row[column] != getattr(event, column):
                    raise DataValidationError(f"{context}: {column} differs from source event")
            if duration != event.duration_periods:
                raise DataValidationError(
                    f"{context}: duration differs from source event (split-session)"
                )
        schedule.append(
            ScheduledEvent(row["event_id"], Placement(row["day"], start, row["room_id"]))
        )
    return tuple(schedule)
