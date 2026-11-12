"""Independent H0–H8 validator and S1/S3/S4 scoring; no solver assumptions."""

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from itertools import combinations
from types import MappingProxyType

from timetable_ga.domain import DAYS, Placement, ProblemInstance, ScheduledEvent

HARD_CODES = tuple(f"H{index}" for index in range(9))
SOFT_CODES = ("S1", "S3", "S4")


@dataclass(frozen=True)
class EvaluationConfig:
    active_soft_constraints: frozenset[str] = frozenset(SOFT_CODES)
    weights: Mapping[str, float] = field(default_factory=lambda: {"S1": 3, "S3": 1, "S4": 5})

    def __post_init__(self) -> None:
        active = frozenset(self.active_soft_constraints)
        if active - set(SOFT_CODES) or set(self.weights) - set(SOFT_CODES):
            raise ValueError("Only S1, S3, S4 are implemented in the MVP")
        weights = {"S1": 3.0, "S3": 1.0, "S4": 5.0, **self.weights}
        if any(not math.isfinite(value) or value < 0 for value in weights.values()):
            raise ValueError("Soft weights must be finite and non-negative")
        object.__setattr__(self, "active_soft_constraints", active)
        object.__setattr__(self, "weights", MappingProxyType(weights))


@dataclass(frozen=True)
class Violation:
    code: str
    event_ids: tuple[str, ...]
    reason: str
    day: str | None = None
    period: int | None = None
    resource_id: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    hard_count: int
    soft_penalty: float
    hard_breakdown: Mapping[str, int]
    soft_raw: Mapping[str, int]
    soft_weighted: Mapping[str, float]
    violations: tuple[Violation, ...]

    @property
    def fitness(self) -> tuple[int, float]:
        """Native tuple comparison is the only ranking rule."""
        return self.hard_count, self.soft_penalty

    @property
    def feasible(self) -> bool:
        return self.hard_count == 0

    @property
    def status(self) -> str:
        return "feasible" if self.feasible else "best_found_infeasible"

    @property
    def status_label(self) -> str:
        return "Lịch hợp lệ" if self.feasible else "Lịch chưa hợp lệ"

    def to_dict(self) -> dict:
        return {
            "hard_count": self.hard_count,
            "soft_penalty": self.soft_penalty,
            "fitness": list(self.fitness),
            "status": self.status,
            "status_label": self.status_label,
            "hard_breakdown": dict(self.hard_breakdown),
            "soft_raw": dict(self.soft_raw),
            "soft_weighted": dict(self.soft_weighted),
            "violations": [asdict(violation) for violation in self.violations],
        }


def evaluate(
    problem: ProblemInstance,
    schedule: Iterable[ScheduledEvent],
    config: EvaluationConfig | None = None,
) -> EvaluationResult:
    """Count distinct event pairs per occupied period, including on invalid schedules."""
    config = config or EvaluationConfig()
    rows = tuple(schedule)
    events = {event.event_id: event for event in problem.events}
    rooms = {room.room_id: room for room in problem.rooms}
    slots = {(slot.day, slot.period): slot for slot in problem.time_slots}
    violations: list[Violation] = []
    seen_violations: set[Violation] = set()

    def add(code, event_ids, reason, day=None, period=None, resource_id=None):
        violation = Violation(code, tuple(event_ids), reason, day, period, resource_id)
        if violation not in seen_violations:
            violations.append(violation)
            seen_violations.add(violation)

    counts = Counter(row.event_id for row in rows)
    for event_id in events:
        if not counts[event_id]:
            add("H0", (event_id,), "missing-event")
    for event_id, count in sorted(counts.items()):
        if event_id not in events:
            add("H0", (event_id,), "unknown-event")
        if count > 1:
            add("H0", (event_id,), "duplicate-event")

    occupancy = {code: defaultdict(set) for code in ("H1", "H2", "H3")}
    avoid_periods: set[tuple[str, str, int]] = set()
    late_periods: set[tuple[str, str, int]] = set()
    assignment_events: dict[str, set[str]] = defaultdict(set)
    assignment_days: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        event = events.get(row.event_id)
        if event is None:
            continue
        placement = row.placement
        if not isinstance(placement, Placement):
            add("H0", (event.event_id,), "invalid-placement")
            continue
        day, start, room_id = placement.day, placement.start_period, placement.room_id
        if not isinstance(day, str) or type(start) is not int or not isinstance(room_id, str):
            add("H0", (event.event_id,), "invalid-placement")
            continue
        room = rooms.get(room_id)
        if room is None or day not in DAYS or (day, start) not in slots:
            add("H0", (event.event_id,), "invalid-placement")
        periods = tuple(range(start, start + event.duration_periods))
        if (
            not 1 <= event.duration_periods <= 4
            or day not in DAYS
            or any((day, period) not in slots for period in periods)
            or len({slots[day, period].block for period in periods if (day, period) in slots}) != 1
            or not (1 <= start <= start + event.duration_periods - 1 <= 8)
            or (start <= 4 < start + event.duration_periods - 1)
        ):
            add("H8", (event.event_id,), "outside-single-block")
        if room is not None:
            if room.capacity < event.size:
                add("H4", (event.event_id,), "room-capacity")
            if room.room_type != event.required_room_type:
                add("H5", (event.event_id,), "room-type")
        if day in DAYS:
            assignment_events[event.assignment_id].add(event.event_id)
            assignment_days[event.assignment_id].add(day)
        for period in periods:
            if (day, period) not in slots:
                continue
            occupancy["H1"][event.teacher_id, day, period].add(event.event_id)
            occupancy["H2"][event.group_id, day, period].add(event.event_id)
            if room is not None:
                occupancy["H3"][room_id, day, period].add(event.event_id)
            if (event.teacher_id, day, period) in problem.teacher_unavailability:
                add("H6", (event.event_id,), "teacher-unavailable", day, period, event.teacher_id)
            if (room_id, day, period) in problem.room_unavailability:
                add("H7", (event.event_id,), "room-unavailable", day, period, room_id)
            if (event.teacher_id, day, period) in problem.teacher_preferences:
                avoid_periods.add((event.event_id, day, period))
            if period in (7, 8):
                late_periods.add((event.event_id, day, period))

    for code, resources in occupancy.items():
        for (resource_id, day, period), event_ids in sorted(resources.items()):
            for pair in combinations(sorted(event_ids), 2):
                add(code, pair, "overlap", day, period, resource_id)

    raw_all = {
        "S1": len(avoid_periods),
        "S3": len(late_periods),
        "S4": sum(
            max(0, len(event_ids) - len(assignment_days[assignment_id]))
            for assignment_id, event_ids in assignment_events.items()
        ),
    }
    raw = {code: raw_all[code] for code in SOFT_CODES if code in config.active_soft_constraints}
    weighted = {code: value * config.weights[code] for code, value in raw.items()}
    breakdown = {code: 0 for code in HARD_CODES}
    for violation in violations:
        breakdown[violation.code] += 1
    return EvaluationResult(
        sum(breakdown.values()),
        sum(weighted.values()),
        MappingProxyType(breakdown),
        MappingProxyType(raw),
        MappingProxyType(weighted),
        tuple(violations),
    )
