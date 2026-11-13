from dataclasses import replace

import pytest

from timetable_ga.candidates import UnschedulableEvent, build_candidates
from timetable_ga.domain import Placement, ScheduledEvent
from timetable_ga.evaluator import evaluate


@pytest.mark.parametrize(
    ("duration", "starts"),
    [
        (1, set(range(1, 13))),
        (2, {1, 2, 3, 5, 6, 7, 9, 10, 11}),
        (3, {1, 2, 5, 6, 9, 10}),
        (4, {1, 5, 9}),
    ],
)
def test_duration_one_to_four_same_block(tiny, duration, starts):
    event = replace(tiny.events[0], duration_periods=duration)
    problem = build_candidates(replace(tiny, events=(event,)))
    candidates = problem.candidates["E0"]
    assert {candidate.start_period for candidate in candidates} == starts
    assert {candidate.room_id for candidate in candidates} == {"R1", "R2"}
    assert len(candidates) == 5 * len(starts) * 2


def test_candidates_check_second_period(tiny):
    event = tiny.events[0]
    problem = build_candidates(
        replace(
            tiny,
            events=(event,),
            teacher_unavailability=frozenset({("T0", "Mon", 2)}),
            room_unavailability=frozenset({("R1", "Tue", 2)}),
        )
    )
    domain = problem.candidates["E0"]
    assert Placement("Mon", 1, "R1") not in domain
    assert Placement("Mon", 1, "R2") not in domain
    assert Placement("Tue", 1, "R1") not in domain
    assert Placement("Tue", 1, "R2") in domain


def test_teacher_fully_unavailable(tiny):
    problem = replace(
        tiny,
        teacher_unavailability=frozenset(("T0", slot.day, slot.period) for slot in tiny.time_slots),
    )
    with pytest.raises(UnschedulableEvent) as error:
        build_candidates(problem)
    assert error.value.event_ids == ("E0",)


def test_all_sample_candidates_pass_independent_local_evaluation(sample):
    for event in sample.events:
        isolated = replace(sample, events=(event,), candidates={})
        for placement in sample.candidates[event.event_id]:
            assert evaluate(isolated, [ScheduledEvent(event.event_id, placement)]).hard_count == 0


def test_jointly_infeasible_is_not_no_candidate(tiny):
    events = tuple(replace(event, duration_periods=1, teacher_id="T0") for event in tiny.events[:2])
    problem = build_candidates(
        replace(tiny, events=events, rooms=tiny.rooms[:1], time_slots=tiny.time_slots[:1])
    )
    assert all(len(domain) == 1 for domain in problem.candidates.values())
    schedule = [
        ScheduledEvent(event.event_id, problem.candidates[event.event_id][0]) for event in events
    ]
    result = evaluate(problem, schedule)
    assert result.hard_count == 2  # one teacher pair and one room pair
    assert result.status == "best_found_infeasible"


def test_missing_middle_slot_excluded(tiny):
    problem = build_candidates(
        replace(
            tiny,
            time_slots=tuple(
                slot for slot in tiny.time_slots if (slot.day, slot.period) != ("Mon", 2)
            ),
        )
    )
    assert Placement("Mon", 1, "R1") not in problem.candidates["E0"]
    assert Placement("Mon", 3, "R1") in problem.candidates["E0"]
