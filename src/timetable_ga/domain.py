"""Immutable domain objects; event order is also chromosome position order."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
PERIODS_PER_BLOCK = 4
BLOCK_NAMES = ("morning", "afternoon", "evening")
PERIODS = tuple(range(1, PERIODS_PER_BLOCK * len(BLOCK_NAMES) + 1))
LATE_PERIODS = frozenset({11, 12})
ROOM_TYPES = frozenset({"lecture", "lab"})


@dataclass(frozen=True)
class Teacher:
    teacher_id: str
    name: str


@dataclass(frozen=True)
class StudentGroup:
    group_id: str
    name: str
    size: int


@dataclass(frozen=True)
class Room:
    room_id: str
    name: str
    capacity: int
    room_type: str


@dataclass(frozen=True)
class Course:
    course_id: str
    name: str


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    course_id: str
    group_id: str
    teacher_id: str
    sessions_per_week: int
    duration_periods: int
    required_room_type: str


@dataclass(frozen=True)
class Event:
    event_id: str
    assignment_id: str
    course_id: str
    group_id: str
    teacher_id: str
    size: int
    duration_periods: int
    required_room_type: str


@dataclass(frozen=True)
class TimeSlot:
    day: str
    period: int
    block: str
    start: str
    end: str


@dataclass(frozen=True)
class Placement:
    day: str
    start_period: int
    room_id: str

    def occupied_periods(self, duration: int) -> tuple[int, ...]:
        return tuple(range(self.start_period, self.start_period + duration))


@dataclass(frozen=True)
class ScheduledEvent:
    event_id: str
    placement: Placement | None


@dataclass(frozen=True)
class ProblemInstance:
    teachers: tuple[Teacher, ...]
    groups: tuple[StudentGroup, ...]
    rooms: tuple[Room, ...]
    courses: tuple[Course, ...]
    assignments: tuple[Assignment, ...]
    events: tuple[Event, ...]
    time_slots: tuple[TimeSlot, ...]
    teacher_unavailability: frozenset[tuple[str, str, int]]
    room_unavailability: frozenset[tuple[str, str, int]]
    teacher_preferences: frozenset[tuple[str, str, int]]
    dataset_fingerprint: str
    candidates: Mapping[str, tuple[Placement, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "teachers",
            "groups",
            "rooms",
            "courses",
            "assignments",
            "events",
            "time_slots",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        for name in ("teacher_unavailability", "room_unavailability", "teacher_preferences"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        object.__setattr__(
            self,
            "candidates",
            MappingProxyType({key: tuple(value) for key, value in self.candidates.items()}),
        )


def expand_events(
    assignments: tuple[Assignment, ...], groups: tuple[StudentGroup, ...]
) -> tuple[Event, ...]:
    """Expand sessions deterministically, deriving size from the student group."""
    sizes = {group.group_id: group.size for group in groups}
    return tuple(
        Event(
            f"{assignment.assignment_id}-S{session:02d}",
            assignment.assignment_id,
            assignment.course_id,
            assignment.group_id,
            assignment.teacher_id,
            sizes[assignment.group_id],
            assignment.duration_periods,
            assignment.required_room_type,
        )
        for assignment in sorted(assignments, key=lambda item: item.assignment_id)
        for session in range(1, assignment.sessions_per_week + 1)
    )
