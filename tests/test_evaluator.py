from dataclasses import replace

import pytest

from timetable_ga.domain import Placement, ScheduledEvent
from timetable_ga.evaluator import HARD_CODES, EvaluationConfig, evaluate
from timetable_ga.io import load_schedule

from .conftest import ROOT


def row(event_id, day="Mon", start=1, room="R1"):
    return ScheduledEvent(event_id, Placement(day, start, room))


def test_sample_witness(sample):
    schedule = load_schedule(ROOT / "data/fixtures/sample_witness_schedule.csv", sample)
    result = evaluate(sample, schedule)
    # A07-S02: teacher T02 on Wed period 7 contributes S1=1; periods 7/8 are no longer late.
    assert result.fitness == (0, 3)
    assert result.hard_breakdown == dict.fromkeys(HARD_CODES, 0)
    assert result.soft_raw == {"S1": 1, "S3": 0, "S4": 0}
    assert result.violations == ()
    assert result.status == "feasible"


def test_tiny_feasible_and_pure(tiny):
    schedule = [row("E0", start=1), row("E1", start=3), row("E2", start=5)]
    before = tuple(schedule)
    first = evaluate(tiny, schedule)
    assert first.fitness == (0, 0)
    assert evaluate(tiny, iter(schedule)) == first
    assert tuple(schedule) == before
    assert tiny.candidates == {}
    with pytest.raises(TypeError):
        first.hard_breakdown["H0"] = 7


@pytest.mark.parametrize(("field", "code"), [("teacher_id", "H1"), ("group_id", "H2")])
def test_one_period_overlap(tiny, field, code):
    events = (tiny.events[0], replace(tiny.events[1], **{field: getattr(tiny.events[0], field)}))
    problem = replace(tiny, events=events)
    result = evaluate(problem, [row("E0"), row("E1", start=2, room="R2")])
    assert result.hard_count == 1
    assert result.hard_breakdown[code] == 1
    assert result.violations[0].period == 2
    assert result.violations[0].event_ids == ("E0", "E1")


def test_room_overlap_one_period(tiny):
    result = evaluate(replace(tiny, events=tiny.events[:2]), [row("E0"), row("E1", start=2)])
    assert result.hard_breakdown["H3"] == result.hard_count == 1


@pytest.mark.parametrize("duration", [1, 2, 3, 4])
def test_three_events_pairs_per_period_all_resources(tiny, duration):
    events = tuple(
        replace(event, teacher_id="T0", group_id="G0", duration_periods=duration)
        for event in tiny.events
    )
    result = evaluate(replace(tiny, events=events), [row(event.event_id) for event in events])
    assert [result.hard_breakdown[code] for code in ("H1", "H2", "H3")] == [3 * duration] * 3
    assert result.hard_count == 9 * duration
    assert len(result.violations) == result.hard_count


@pytest.mark.parametrize(
    ("schedule", "count", "reason"),
    [
        ([], 1, "missing-event"),
        ([row("E0"), row("E0"), row("E0")], 1, "duplicate-event"),
        ([row("E0"), row("UNKNOWN")], 1, "unknown-event"),
        ([row("E0", room="UNKNOWN")], 1, "invalid-placement"),
        ([ScheduledEvent("E0", None)], 1, "invalid-placement"),
        ([row("E0", start="one")], 1, "invalid-placement"),
    ],
)
def test_h0_integrity(tiny, schedule, count, reason):
    result = evaluate(replace(tiny, events=tiny.events[:1]), schedule)
    assert result.hard_breakdown["H0"] == count
    assert any(violation.reason == reason for violation in result.violations)
    assert result.status_label == "Lịch chưa hợp lệ"
    assert not result.feasible


def test_split_session_duplicate_placements(tiny):
    result = evaluate(replace(tiny, events=tiny.events[:1]), [row("E0"), row("E0", room="R2")])
    assert result.hard_breakdown["H0"] == 1
    assert result.hard_breakdown["H1"] == 0  # one event cannot conflict with itself


@pytest.mark.parametrize(("room", "code"), [("SMALL", "H4"), ("LAB", "H5")])
def test_room_local_constraints_independent_of_candidates(tiny, room, code):
    problem = replace(tiny, events=tiny.events[:1], candidates={"E0": (Placement("Mon", 1, room),)})
    result = evaluate(problem, [row("E0", room=room)])
    assert result.hard_count == result.hard_breakdown[code] == 1


def test_capacity_and_type_count_once_per_event(tiny):
    event = replace(tiny.events[0], required_room_type="lab")
    result = evaluate(replace(tiny, events=(event,)), [row("E0", room="SMALL")] * 3)
    assert result.hard_breakdown["H0"] == 1
    assert result.hard_breakdown["H4"] == result.hard_breakdown["H5"] == 1


@pytest.mark.parametrize("periods", [(2,), (1, 2)])
def test_unavailable_each_occupied_period(tiny, periods):
    problem = replace(
        tiny,
        events=tiny.events[:1],
        teacher_unavailability=frozenset(("T0", "Mon", period) for period in periods),
        room_unavailability=frozenset(("R1", "Mon", period) for period in periods),
    )
    result = evaluate(problem, [row("E0")])
    assert result.hard_breakdown["H6"] == result.hard_breakdown["H7"] == len(periods)
    assert result.hard_count == 2 * len(periods)


@pytest.mark.parametrize(
    ("day", "start"), [("Mon", 4), ("Fri", 8), ("Sat", 1), ("Mon", 0), ("Mon", 12), ("Mon", 13)]
)
def test_h8_cross_block_or_week(tiny, day, start):
    result = evaluate(replace(tiny, events=tiny.events[:1]), [row("E0", day, start)])
    assert result.hard_breakdown["H8"] == 1


def test_h8_missing_second_slot(tiny):
    problem = replace(
        tiny,
        events=tiny.events[:1],
        time_slots=tuple(slot for slot in tiny.time_slots if (slot.day, slot.period) != ("Mon", 2)),
    )
    result = evaluate(problem, [row("E0")])
    assert result.hard_breakdown["H8"] == 1


def test_soft_exact_weights_and_avoid_is_not_unavailable(tiny):
    events = (tiny.events[0], replace(tiny.events[1], assignment_id="A0"))
    problem = replace(tiny, events=events, teacher_preferences=frozenset({("T0", "Mon", 12)}))
    schedule = [row("E0", start=11), row("E1", start=1)]
    result = evaluate(problem, schedule)
    assert result.hard_count == 0
    assert result.soft_raw == {"S1": 1, "S3": 2, "S4": 1}
    assert result.soft_weighted == {"S1": 3, "S3": 2, "S4": 5}
    assert result.soft_penalty == 10
    different_days = evaluate(problem, [schedule[0], row("E1", day="Tue")])
    assert different_days.soft_raw["S4"] == 0
    subset = evaluate(problem, schedule, EvaluationConfig(frozenset({"S1"}), {"S1": 7}))
    assert subset.soft_raw == {"S1": 1}
    assert subset.soft_penalty == 7
    assert evaluate(problem, schedule, EvaluationConfig(frozenset())).soft_penalty == 0


@pytest.mark.parametrize("code", ["S2", "S5", "S6", "S9"])
def test_unimplemented_soft_rejected(code):
    with pytest.raises(ValueError, match="Only S1, S3, S4"):
        EvaluationConfig(frozenset({code}))


@pytest.mark.parametrize("weight", [-1, float("nan"), float("inf")])
def test_invalid_weight_rejected(weight):
    with pytest.raises(ValueError, match="finite and non-negative"):
        EvaluationConfig(weights={"S1": weight})


def test_lexicographic_comparator(tiny):
    problem = replace(
        tiny, events=tiny.events[:1], teacher_preferences=frozenset({("T0", "Mon", 1)})
    )
    feasible = evaluate(problem, [row("E0")], EvaluationConfig(weights={"S1": 9999}))
    invalid = evaluate(problem, [row("E0", day="Tue", room="SMALL")])
    assert feasible.fitness == (0, 9999)
    assert invalid.fitness == (1, 0)
    assert feasible.fitness < invalid.fitness
