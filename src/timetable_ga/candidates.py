"""Local placement domains. These do not establish global feasibility."""

from dataclasses import replace

from timetable_ga.domain import DAYS, PERIODS, Placement, ProblemInstance


class UnschedulableEvent(ValueError):
    """At least one event has no placement satisfying local H4–H8."""

    def __init__(self, event_ids: tuple[str, ...]) -> None:
        self.event_ids = event_ids
        super().__init__(
            "No candidate placements satisfying H4-H8 for events: " + ", ".join(event_ids)
        )


def build_candidates(problem: ProblemInstance) -> ProblemInstance:
    """Return a new instance with deterministic domains, or a structured error."""
    slots = {(slot.day, slot.period): slot for slot in problem.time_slots}
    domains: dict[str, tuple[Placement, ...]] = {}
    for event in problem.events:
        placements = []
        for day in DAYS:
            for start in PERIODS:
                periods = tuple(range(start, start + event.duration_periods))
                if not 1 <= event.duration_periods <= 4:
                    continue
                if any((day, period) not in slots for period in periods):
                    continue
                if len({slots[day, period].block for period in periods}) != 1:
                    continue
                if any(
                    (event.teacher_id, day, period) in problem.teacher_unavailability
                    for period in periods
                ):
                    continue
                for room in sorted(problem.rooms, key=lambda item: item.room_id):
                    if room.capacity < event.size or room.room_type != event.required_room_type:
                        continue
                    if any(
                        (room.room_id, day, period) in problem.room_unavailability
                        for period in periods
                    ):
                        continue
                    placements.append(Placement(day, start, room.room_id))
        domains[event.event_id] = tuple(placements)
    empty = tuple(event_id for event_id, placements in domains.items() if not placements)
    if empty:
        raise UnschedulableEvent(empty)
    return replace(problem, candidates=domains)
