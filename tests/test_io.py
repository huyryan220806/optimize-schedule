import csv
from dataclasses import FrozenInstanceError

import pytest

from timetable_ga.candidates import UnschedulableEvent
from timetable_ga.io import SCHEMAS, DataValidationError, load_problem


def test_sample_schema_and_event_expansion(sample):
    assert len(sample.teachers) == 7
    assert len(sample.groups) == 4
    assert len(sample.rooms) == 6
    assert len(sample.courses) == 7
    assert len(sample.assignments) == 12
    assert len(sample.events) == 24
    assert len(sample.time_slots) == 60
    assert sample.events[0].event_id == "A01-S01"
    assert sample.events[1].event_id == "A01-S02"
    assert {event.duration_periods for event in sample.events} == {2}
    groups = {group.group_id: group for group in sample.groups}
    assert all(event.size == groups[event.group_id].size for event in sample.events)
    assert all(sample.candidates[event.event_id] for event in sample.events)
    assert len(sample.dataset_fingerprint) == 64


def test_problem_immutable(sample):
    with pytest.raises(FrozenInstanceError):
        sample.events[0].size = 1
    with pytest.raises(TypeError):
        sample.candidates["A01-S01"] = ()


@pytest.mark.parametrize("table", SCHEMAS)
def test_duplicate_key_rejected(data_dir, edit_csv, table):
    edit_csv(table, lambda rows: rows.append(dict(rows[0])))
    with pytest.raises(DataValidationError, match=rf"{table}.csv: row .*duplicate key"):
        load_problem(data_dir)


@pytest.mark.parametrize(
    ("table", "field", "value", "message"),
    [
        ("teachers", "teacher_id", "", "is empty"),
        ("teachers", "name", "  ", "is empty"),
        ("student_groups", "size", "0", "outside"),
        ("student_groups", "size", "3.5", "expected integer"),
        ("rooms", "capacity", "-1", "outside"),
        ("rooms", "room_type", "gym", "invalid room_type"),
        ("assignments", "duration_periods", "5", "outside"),
        ("assignments", "duration_periods", "0", "outside"),
        ("assignments", "sessions_per_week", "0", "outside"),
        ("assignments", "sessions_per_week", "one", "expected integer"),
        ("assignments", "required_room_type", "any", "invalid required_room_type"),
        ("assignments", "teacher_id", "T404", "unknown teacher_id"),
        ("assignments", "group_id", "G404", "unknown group_id"),
        ("assignments", "course_id", "C404", "unknown course_id"),
        ("teacher_unavailability", "teacher_id", "T404", "unknown teacher_id"),
        ("room_unavailability", "room_id", "R404", "unknown room_id"),
        ("teacher_preferences", "teacher_id", "T404", "unknown teacher_id"),
        ("teacher_preferences", "preference", "prefer", "must be 'avoid'"),
        ("time_slots", "day", "Sat", "unknown day"),
        ("time_slots", "period", "13", "outside"),
        ("time_slots", "period", "0", "outside"),
        ("time_slots", "block", "afternoon", "block must be morning"),
        ("time_slots", "start", "25:00", "invalid start time"),
        ("time_slots", "start", "7:00", "invalid start time"),
        ("time_slots", "end", "06:00", "start must be before end"),
        ("time_slots", "end", "09:00", "times overlap"),
        ("teacher_unavailability", "day", "Sat", "unknown day"),
        ("room_unavailability", "period", "1.5", "expected integer"),
    ],
)
def test_malformed_fields(data_dir, edit_csv, table, field, value, message):
    edit_csv(table, lambda rows: rows[0].update({field: value}))
    with pytest.raises(DataValidationError, match=message):
        load_problem(data_dir)


@pytest.mark.parametrize("content", ["teacher_id\nT1\n", "teacher_id,name,name\nT1,A,B\n", ""])
def test_bad_header(data_dir, content):
    (data_dir / "teachers.csv").write_text(content, encoding="utf-8")
    with pytest.raises(DataValidationError, match="header|schema"):
        load_problem(data_dir)


@pytest.mark.parametrize("content", ["teacher_id,name\nT1,A,B\n", "teacher_id,name\nT1\n"])
def test_wrong_column_count(data_dir, content):
    (data_dir / "teachers.csv").write_text(content, encoding="utf-8")
    with pytest.raises(DataValidationError, match="wrong column count"):
        load_problem(data_dir)


def test_missing_file(data_dir):
    (data_dir / "teachers.csv").unlink()
    with pytest.raises(DataValidationError, match="teachers.csv: cannot read"):
        load_problem(data_dir)


def test_missing_referenced_slot(data_dir, edit_csv):
    edit_csv("time_slots", lambda rows: rows.pop(0))
    with pytest.raises(DataValidationError, match="time slot does not exist"):
        load_problem(data_dir)


@pytest.mark.parametrize(
    "table", ["teachers", "student_groups", "rooms", "courses", "assignments", "time_slots"]
)
def test_empty_required_table(data_dir, edit_csv, table):
    edit_csv(table, lambda rows: rows.clear())
    with pytest.raises(DataValidationError, match="at least one record"):
        load_problem(data_dir)


def test_empty_optional_tables(data_dir, edit_csv):
    for name in ("teacher_unavailability", "room_unavailability", "teacher_preferences"):
        edit_csv(name, lambda rows: rows.clear())
    assert len(load_problem(data_dir).events) == 24


def test_fingerprint_normalized_order_bom_columns_and_integers(data_dir, sample):
    for name in SCHEMAS:
        path = data_dir / f"{name}.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = list(reversed(reader.fieldnames))
            rows = list(reader)
        if name == "student_groups":
            rows[0]["size"] = " 032 "
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, columns)
            writer.writeheader()
            writer.writerows(reversed(rows))
    reordered = load_problem(data_dir)
    assert reordered.dataset_fingerprint == sample.dataset_fingerprint
    assert reordered.events == sample.events
    assert reordered.candidates == sample.candidates


def test_fingerprint_changes_with_data(data_dir, edit_csv, sample):
    edit_csv("teachers", lambda rows: rows[0].update(name="Different name"))
    assert load_problem(data_dir).dataset_fingerprint != sample.dataset_fingerprint


def test_manifest_is_not_read(data_dir, sample):
    (data_dir / "manifest.json").write_text("invalid JSON; witness must never be loaded")
    assert load_problem(data_dir).dataset_fingerprint == sample.dataset_fingerprint


def test_capacity_no_candidate_structured_error(data_dir, edit_csv):
    edit_csv("student_groups", lambda rows: rows[0].update(size="999"))
    with pytest.raises(UnschedulableEvent) as error:
        load_problem(data_dir)
    assert error.value.event_ids == tuple(f"A0{i}-S0{j}" for i in range(1, 4) for j in (1, 2))
