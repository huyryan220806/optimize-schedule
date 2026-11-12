"""Shared chromosome representation, evaluation budget, and solver result."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from random import Random
from time import perf_counter

from timetable_ga import evaluator
from timetable_ga.candidates import UnschedulableEvent
from timetable_ga.domain import ProblemInstance, ScheduledEvent
from timetable_ga.evaluator import EvaluationConfig, EvaluationResult

Chromosome = tuple[int, ...]


class SolverConfigError(ValueError):
    """Invalid solver options, rejected before any evaluation."""


def require_integer(name: str, value: int, minimum: int | None = None) -> None:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise SolverConfigError(
            f"{name} must be an integer" + (f" >= {minimum}" if minimum is not None else "")
        )


@dataclass(frozen=True)
class SearchConfig:
    seed: int = 42
    max_evals: int = 2000

    def __post_init__(self) -> None:
        require_integer("seed", self.seed)
        require_integer("max_evals", self.max_evals, 1)


@dataclass(frozen=True)
class Individual:
    chromosome: Chromosome
    evaluation: EvaluationResult


@dataclass(frozen=True)
class HistoryEntry:
    generation: int
    evaluation: int
    best_hard: int
    best_soft: float
    best_soft_if_feasible: float | None


@dataclass(frozen=True)
class OptimizationResult:
    algorithm: str
    chromosome: Chromosome
    schedule: tuple[ScheduledEvent, ...]
    evaluation: EvaluationResult
    history: tuple[HistoryEntry, ...]
    actual_evals: int
    runtime_sec: float
    stop_reason: str
    dataset_fingerprint: str
    config: Mapping

    def metrics(self) -> dict:
        """Serializable diagnostics; a soft score for infeasible runs is not a quality claim."""
        return {
            "algorithm": self.algorithm,
            "seed": self.config["seed"],
            "dataset_fingerprint": self.dataset_fingerprint,
            "max_evals": self.config["max_evals"],
            "actual_evals": self.actual_evals,
            "runtime_sec": self.runtime_sec,
            "stop_reason": self.stop_reason,
            "config": dict(self.config),
            "chromosome": list(self.chromosome),
            "soft_feasible_only": self.evaluation.soft_penalty
            if self.evaluation.feasible
            else None,
            **self.evaluation.to_dict(),
        }


def domain_sizes(problem: ProblemInstance) -> tuple[int, ...]:
    if not problem.events:
        raise SolverConfigError("Cannot solve a problem with no events")
    sizes = tuple(len(problem.candidates.get(event.event_id, ())) for event in problem.events)
    empty = tuple(
        event.event_id for event, size in zip(problem.events, sizes, strict=True) if not size
    )
    if empty:
        raise UnschedulableEvent(empty)
    return sizes


def random_chromosome(sizes: Sequence[int], rng: Random) -> Chromosome:
    return tuple(rng.randrange(size) for size in sizes)


def decode(problem: ProblemInstance, chromosome: Chromosome) -> tuple[ScheduledEvent, ...]:
    """Reject bad gene lengths/types/indices before constructing a complete schedule."""
    if len(chromosome) != len(problem.events):
        raise ValueError("Chromosome length differs from event count")
    schedule = []
    for event, index in zip(problem.events, chromosome, strict=True):
        candidates = problem.candidates.get(event.event_id, ())
        if type(index) is not int or not 0 <= index < len(candidates):
            raise ValueError(f"Invalid candidate index for {event.event_id}: {index!r}")
        schedule.append(ScheduledEvent(event.event_id, candidates[index]))
    return tuple(schedule)


class EvaluationBudget:
    """Only solver evaluation entry point; caches no trial and counts every full call."""

    def __init__(
        self, problem: ProblemInstance, config: SearchConfig, soft: EvaluationConfig | None
    ):
        self.problem = problem
        self.config = config
        self.soft = soft or EvaluationConfig()
        self.sizes = domain_sizes(problem)
        self.count = 0
        self.best: Individual | None = None
        self.history: list[HistoryEntry] = []
        self.started = perf_counter()

    @property
    def remaining(self) -> int:
        return self.config.max_evals - self.count

    def score(self, chromosome: Chromosome, generation: int) -> Individual:
        if not self.remaining:
            raise RuntimeError("Evaluation budget exhausted")
        schedule = decode(self.problem, chromosome)
        result = evaluator.evaluate(self.problem, schedule, self.soft)
        self.count += 1
        individual = Individual(chromosome, result)
        if self.best is None or result.fitness < self.best.evaluation.fitness:
            self.best = individual
        best = self.best.evaluation
        self.history.append(
            HistoryEntry(
                generation,
                self.count,
                best.hard_count,
                best.soft_penalty,
                best.soft_penalty if best.feasible else None,
            )
        )
        return individual

    def finish(self, algorithm: str, stop_reason: str) -> OptimizationResult:
        if self.best is None:
            raise RuntimeError("Solver did not evaluate any complete schedule")
        config = {
            **asdict(self.config),
            "active_soft_constraints": sorted(self.soft.active_soft_constraints),
            "soft_weights": dict(self.soft.weights),
        }
        return OptimizationResult(
            algorithm,
            self.best.chromosome,
            decode(self.problem, self.best.chromosome),
            self.best.evaluation,
            tuple(self.history),
            self.count,
            perf_counter() - self.started,
            stop_reason,
            self.problem.dataset_fingerprint,
            config,
        )
