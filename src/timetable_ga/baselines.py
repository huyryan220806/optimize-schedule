"""Random search and multi-start full-schedule greedy coordinate sweeps."""

from random import Random

from timetable_ga.domain import ProblemInstance
from timetable_ga.evaluator import EvaluationConfig
from timetable_ga.search import (
    EvaluationBudget,
    OptimizationResult,
    SearchConfig,
    random_chromosome,
)


def random_search(
    problem: ProblemInstance,
    config: SearchConfig | None = None,
    soft: EvaluationConfig | None = None,
) -> OptimizationResult:
    config = config or SearchConfig()
    rng = Random(config.seed)
    budget = EvaluationBudget(problem, config, soft)
    while budget.remaining:
        budget.score(random_chromosome(budget.sizes, rng), budget.count)
    return budget.finish("random", "max_evals")


def greedy_search(
    problem: ProblemInstance,
    config: SearchConfig | None = None,
    soft: EvaluationConfig | None = None,
) -> OptimizationResult:
    """Choose the best gene for each hard event against a full random completion.

    One sweep per restart; every trial invokes the same full evaluator as GA.
    No witness, incremental scoring, or uncounted construction evaluation.
    """
    config = config or SearchConfig()
    rng = Random(config.seed)
    budget = EvaluationBudget(problem, config, soft)
    dependencies = tuple(
        sum(
            other.event_id != event.event_id
            and (other.teacher_id == event.teacher_id or other.group_id == event.group_id)
            for other in problem.events
        )
        for event in problem.events
    )
    restart = 0
    while budget.remaining:
        current = budget.score(random_chromosome(budget.sizes, rng), restart)
        order = list(range(len(problem.events)))
        rng.shuffle(order)
        order.sort(key=lambda index: (budget.sizes[index], -dependencies[index]))
        for index in order:
            best = current
            candidates = list(range(budget.sizes[index]))
            rng.shuffle(candidates)
            for candidate in candidates:
                if not budget.remaining:
                    return budget.finish("greedy", "max_evals")
                if candidate == current.chromosome[index]:
                    continue  # its full fitness was already evaluated and counted
                genes = list(current.chromosome)
                genes[index] = candidate
                trial = budget.score(tuple(genes), restart)
                if trial.evaluation.fitness < best.evaluation.fitness:
                    best = trial
            current = best
        restart += 1
    return budget.finish("greedy", "max_evals")
