"""Regression coverage for all three four-period blocks and evening soft costs."""

from dataclasses import replace

import pytest

from timetable_ga.candidates import build_candidates
from timetable_ga.domain import Placement, ScheduledEvent
from timetable_ga.evaluator import evaluate
from timetable_ga.io import DataValidationError, load_problem, load_schedule
from timetable_ga.outputs import schedule_csv
from timetable_ga.ui import timetable_frame, timetable_html


@pytest.mark.parametrize(("start", "duration"), [(4, 2), (8, 2), (12, 2), (7, 3), (10, 4)])
def test_crossing_any_block_boundary_rejected_even_if_slot_labels_lie(tiny, start, duration):
    event = replace(tiny.events[0], duration_periods=duration)
    problem = replace(
        tiny,
        events=(event,),
        time_slots=tuple(replace(slot, block="morning") for slot in tiny.time_slots),
    )
    result = evaluate(problem, [ScheduledEvent("E0", Placement("Mon", start, "R1"))])
    assert result.hard_breakdown["H8"] == 1


@pytest.mark.parametrize(
    ("start", "duration", "late"), [(7, 2, 0), (9, 2, 0), (10, 2, 1), (11, 2, 2), (9, 4, 2)]
)
def test_evening_valid_and_late_penalty_only_eleven_twelve(tiny, start, duration, late):
    event = replace(tiny.events[0], duration_periods=duration)
    result = evaluate(
        replace(tiny, events=(event,)), [ScheduledEvent("E0", Placement("Mon", start, "R1"))]
    )
    assert result.hard_count == 0
    assert result.soft_raw["S3"] == result.soft_weighted["S3"] == late


def test_evening_unavailable_checks_last_occupied_period(tiny):
    problem = replace(
        tiny,
        events=tiny.events[:1],
        teacher_unavailability=frozenset({("T0", "Mon", 12)}),
        room_unavailability=frozenset({("R1", "Tue", 12)}),
    )
    candidates = build_candidates(problem).candidates["E0"]
    assert Placement("Mon", 11, "R1") not in candidates
    assert Placement("Tue", 11, "R1") not in candidates
    assert Placement("Wed", 11, "R1") in candidates
    teacher = evaluate(problem, [ScheduledEvent("E0", Placement("Mon", 11, "R1"))])
    room = evaluate(problem, [ScheduledEvent("E0", Placement("Tue", 11, "R1"))])
    assert teacher.hard_breakdown["H6"] == room.hard_breakdown["H7"] == 1


def test_evening_loader_and_csv_round_trip(data_dir, edit_csv, tmp_path):
    edit_csv(
        "teacher_preferences",
        lambda rows: rows.append(
            {"teacher_id": "T01", "day": "Mon", "period": "12", "preference": "avoid"}
        ),
    )
    problem = load_problem(data_dir)
    assert ("T01", "Mon", 12) in problem.teacher_preferences
    event = problem.events[0]
    placement = next(p for p in problem.candidates[event.event_id] if p.start_period == 11)
    rows = (ScheduledEvent(event.event_id, placement),)
    path = tmp_path / "evening.csv"
    path.write_text(schedule_csv(problem, rows), encoding="utf-8-sig")
    assert load_schedule(path, problem) == rows
    frame = timetable_frame(problem, rows, event.group_id)
    assert frame.shape == (12, 5)
    assert event.event_id in frame.loc[11, placement.day]
    assert event.event_id in frame.loc[12, placement.day]
    html = timetable_html(problem, rows, event.group_id)
    assert "Tiết 12" in html and "Ca tối bắt đầu từ tiết 9" in html


def test_loader_rejects_wrong_evening_block(data_dir, edit_csv):
    def wrong_block(rows):
        next(row for row in rows if row["period"] == "9")["block"] = "afternoon"

    edit_csv("time_slots", wrong_block)
    with pytest.raises(DataValidationError, match="block must be evening"):
        load_problem(data_dir)
