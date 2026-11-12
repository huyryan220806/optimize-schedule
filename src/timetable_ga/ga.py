"""Seeded genetic algorithm implemented with Python's standard library."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from random import Random

from timetable_ga.domain import ProblemInstance
from timetable_ga.evaluator import EvaluationConfig
from timetable_ga.search import (
    Chromosome,
    EvaluationBudget,
    Individual,
    OptimizationResult,
    SearchConfig,
    SolverConfigError,
    random_chromosome,
    require_integer,
)


@dataclass(frozen=True)
class GAConfig(SearchConfig):
    population_size: int = 40
    generations: int = 50
    crossover_rate: float = 0.85
    mutation_rate: float = 0.10
    elite_count: int = 2
    tournament_size: int = 3
    repair_enabled: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        require_integer("population_size", self.population_size, 2)
        require_integer("generations", self.generations, 0)
        require_integer("elite_count", self.elite_count, 0)
        require_integer("tournament_size", self.tournament_size, 1)
        if self.elite_count >= self.population_size:
            raise SolverConfigError("elite_count must be less than population_size")
        if self.tournament_size > self.population_size:
            raise SolverConfigError("tournament_size must not exceed population_size")
        for name in ("crossover_rate", "mutation_rate"):
            rate = getattr(self, name)
            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not math.isfinite(rate)
                or not 0 <= rate <= 1
            ):
                raise SolverConfigError(f"{name} must be finite and in [0, 1]")
        if self.repair_enabled is not False:
            raise SolverConfigError("Repair is deferred; repair_enabled must be False")


def tournament(population: Sequence[Individual], size: int, rng: Random) -> Individual:
    """Sample without replacement, then compare lexicographic fitness."""
    return min(rng.sample(list(population), size), key=lambda item: item.evaluation.fitness)


def uniform_crossover(
    first: Chromosome,
    second: Chromosome,
    rate: float,
    rng: Random,
) -> tuple[Chromosome, Chromosome]:
    if len(first) != len(second):
        raise ValueError("Parents must have equal chromosome lengths")
    if rng.random() >= rate:
        return first, second
    left, right = [], []
    for one, two in zip(first, second, strict=True):
        if rng.random() < 0.5:
            one, two = two, one
        left.append(one)
        right.append(two)
    return tuple(left), tuple(right)


def mutate(chromosome: Chromosome, sizes: Sequence[int], rate: float, rng: Random) -> Chromosome:
    """Random reset to a different candidate whenever mutation fires and size > 1."""
    genes = list(chromosome)
    for index, (gene, size) in enumerate(zip(chromosome, sizes, strict=True)):
        if rng.random() < rate and size > 1:
            alternative = rng.randrange(size - 1)
            genes[index] = alternative + (alternative >= gene)
    return tuple(genes)


def elitist_survivors(
    parents: Sequence[Individual],
    children: Sequence[Individual],
    elite_count: int,
    size: int,
) -> list[Individual]:
    """Retain parent elites without additional calls, then best evaluated offspring."""
    elite = sorted(parents, key=lambda item: item.evaluation.fitness)[:elite_count]
    offspring = sorted(children, key=lambda item: item.evaluation.fitness)
    # A last budget-limited generation can contain fewer children than a population.
    pool = offspring + sorted(parents, key=lambda item: item.evaluation.fitness)[elite_count:]
    return elite + pool[: size - elite_count]


def optimize(
    problem: ProblemInstance,
    config: GAConfig | None = None,
    soft: EvaluationConfig | None = None,
) -> OptimizationResult:
    config = config or GAConfig()
    rng = Random(config.seed)
    budget = EvaluationBudget(problem, config, soft)
    population = [
        budget.score(random_chromosome(budget.sizes, rng), 0)
        for _ in range(min(config.population_size, budget.remaining))
    ]
    for generation in range(1, config.generations + 1):
        if not budget.remaining:
            break
        children = []
        while len(children) < config.population_size and budget.remaining:
            first = tournament(population, config.tournament_size, rng)
            second = tournament(population, config.tournament_size, rng)
            pair = uniform_crossover(
                first.chromosome, second.chromosome, config.crossover_rate, rng
            )
            for child in pair:
                if len(children) == config.population_size or not budget.remaining:
                    break
                child = mutate(child, budget.sizes, config.mutation_rate, rng)
                children.append(budget.score(child, generation))
        population = elitist_survivors(
            population, children, config.elite_count, config.population_size
        )
    return budget.finish("ga", "max_evals" if not budget.remaining else "generations")
