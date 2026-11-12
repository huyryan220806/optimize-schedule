"""Export solver outputs without re-evaluating or changing their metrics."""

import csv
import io
import json
from dataclasses import asdict
from pathlib import Path

from timetable_ga.domain import ProblemInstance, ScheduledEvent
from timetable_ga.io import SCHEDULE_COLUMNS
from timetable_ga.search import OptimizationResult


def schedule_csv(problem: ProblemInstance, schedule: tuple[ScheduledEvent, ...]) -> str:
    """Create the contracted schedule CSV, also usable by a future UI download."""
    events = {event.event_id: event for event in problem.events}
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, SCHEDULE_COLUMNS)
    writer.writeheader()
    for row in schedule:
        event = events[row.event_id]
        placement = row.placement
        if placement is None:
            raise ValueError(f"Cannot export an absent placement: {row.event_id}")
        writer.writerow(
            {
                "event_id": event.event_id,
                "assignment_id": event.assignment_id,
                "course_id": event.course_id,
                "group_id": event.group_id,
                "teacher_id": event.teacher_id,
                "day": placement.day,
                "start_period": placement.start_period,
                "duration_periods": event.duration_periods,
                "room_id": placement.room_id,
            }
        )
    return buffer.getvalue()


def export_result(
    problem: ProblemInstance, result: OptimizationResult, directory: str | Path
) -> None:
    """Write a schedule, full diagnostics/config, and all counted evaluations."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    (root / "schedule.csv").write_text(
        schedule_csv(problem, result.schedule), encoding="utf-8", newline=""
    )
    (root / "metrics.json").write_text(
        json.dumps(result.metrics(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (root / "history.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, ("generation", "evaluation", "best_hard", "best_soft", "best_soft_if_feasible")
        )
        writer.writeheader()
        writer.writerows(asdict(entry) for entry in result.history)
