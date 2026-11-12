from dataclasses import replace
from random import Random

import pytest

from timetable_ga import evaluator
from timetable_ga.baselines import greedy_search, random_search
from timetable_ga.candidates import UnschedulableEvent, build_candidates
from timetable_ga.domain import Placement
from timetable_ga.evaluator import EvaluationConfig, evaluate
from timetable_ga.ga import (
    GAConfig,
    elitist_survivors,
    mutate,
    optimize,
    tournament,
    uniform_crossover,
)
from timetable_ga.search import (
    EvaluationBudget,
    Individual,
    SearchConfig,
    SolverConfigError,
    decode,
    domain_sizes,
    random_chromosome,
)

SOLVERS = (random_search, greedy_search, optimize)


def config_for(solver, budget=37, seed=17):
    if solver is optimize:
        return GAConfig(seed=seed, max_evals=budget, population_size=6, generations=20)
    return SearchConfig(seed=seed, max_evals=budget)


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("budget", [1, 5, 6, 7, 37])
def test_shared_full_evaluator_exact_budget_and_returned_fitness(tiny, monkeypatch, solver, budget):
    problem = build_candidates(tiny)
    original = evaluator.evaluate
    seen = []

    def counted(instance, schedule, soft):
        assert instance is problem
        assert len(schedule) == len(problem.events)
        assert {row.event_id for row in schedule} == {event.event_id for event in problem.events}
        score = original(instance, schedule, soft)
        seen.append(score.fitness)
        return score

    monkeypatch.setattr(evaluator, "evaluate", counted)
    result = solver(problem, config_for(solver, budget))
    assert result.actual_evals == len(seen) == budget
    assert result.stop_reason == "max_evals"
    assert result.evaluation.fitness == min(seen)
    assert result.evaluation == original(problem, result.schedule)
    assert result.schedule == decode(problem, result.chromosome)
    assert len(result.history) == budget
    assert [entry.evaluation for entry in result.history] == list(range(1, budget + 1))
    observed_best = [(entry.best_hard, entry.best_soft) for entry in result.history]
    assert observed_best == [min(seen[:index]) for index in range(1, budget + 1)]
    assert all(
        entry.best_soft_if_feasible is None for entry in result.history if entry.best_hard > 0
    )


@pytest.mark.parametrize("solver", SOLVERS)
def test_reproducible_seed_chromosome_fitness_history(sample, solver):
    config = config_for(solver, budget=81)
    first = solver(sample, config)
    second = solver(sample, config)
    assert first.chromosome == second.chromosome
    assert first.evaluation == second.evaluation
    assert first.history == second.history
    assert first.config == second.config


@pytest.mark.parametrize("solver", SOLVERS)
def test_jointly_infeasible_returns_honest_status(tiny, solver):
    events = tuple(replace(event, duration_periods=1, teacher_id="T0") for event in tiny.events[:2])
    problem = build_candidates(
        replace(tiny, events=events, rooms=tiny.rooms[:1], time_slots=tiny.time_slots[:1])
    )
    result = solver(problem, config_for(solver, 13))
    assert result.evaluation.hard_count == 2
    assert result.evaluation.status == "best_found_infeasible"
    assert result.evaluation.status_label == "Lịch chưa hợp lệ"
    assert result.metrics()["soft_feasible_only"] is None
    assert result.actual_evals == 13


@pytest.mark.parametrize("solver", SOLVERS)
def test_empty_domain_preflight_no_evaluations(tiny, monkeypatch, solver):
    def forbidden(*args):
        raise AssertionError("Evaluator must not be called for no-candidate input")

    monkeypatch.setattr(evaluator, "evaluate", forbidden)
    with pytest.raises(UnschedulableEvent):
        solver(tiny, config_for(solver))


@pytest.mark.parametrize("solver", SOLVERS)
def test_soft_configuration_shared(tiny, solver):
    problem = build_candidates(tiny)
    config = EvaluationConfig(frozenset())
    result = solver(problem, config_for(solver), config)
    assert result.evaluation.soft_penalty == 0
    assert result.config["active_soft_constraints"] == []


def test_ga_generation_limit_and_initial_only(tiny):
    problem = build_candidates(tiny)
    result = optimize(problem, GAConfig(population_size=6, generations=2, max_evals=100))
    assert result.actual_evals == 18  # 6 initial + 2 * 6 children, elites reused
    assert result.stop_reason == "generations"
    assert result.history[-1].generation == 2
    initial = optimize(problem, GAConfig(population_size=6, generations=0))
    assert initial.actual_evals == 6
    assert all(entry.generation == 0 for entry in initial.history)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"population_size": 1}, "population_size"),
        ({"population_size": 3.5}, "population_size"),
        ({"elite_count": 40}, "elite_count"),
        ({"elite_count": -1}, "elite_count"),
        ({"tournament_size": 41}, "tournament_size"),
        ({"tournament_size": 0}, "tournament_size"),
        ({"generations": -1}, "generations"),
        ({"mutation_rate": -0.1}, "mutation_rate"),
        ({"mutation_rate": 1.1}, "mutation_rate"),
        ({"mutation_rate": float("nan")}, "mutation_rate"),
        ({"crossover_rate": float("inf")}, "crossover_rate"),
        ({"mutation_rate": "bad"}, "mutation_rate"),
        ({"repair_enabled": True}, "Repair is deferred"),
        ({"max_evals": 0}, "max_evals"),
        ({"max_evals": True}, "max_evals"),
        ({"seed": 1.5}, "seed"),
        ({"seed": True}, "seed"),
    ],
)
def test_bad_config_rejected(changes, message):
    with pytest.raises(SolverConfigError, match=message):
        GAConfig(**changes)


def test_crossover_whole_event_genes_and_different_domains(sample):
    sizes = domain_sizes(sample)
    first = tuple(0 for _ in sizes)
    second = tuple(size - 1 for size in sizes)
    left, right = uniform_crossover(first, second, 1, Random(11))
    assert left != first and left != second
    for i, size in enumerate(sizes):
        assert {left[i], right[i]} == {first[i], second[i]}
        assert 0 <= left[i] < size and 0 <= right[i] < size
    assert uniform_crossover(first, second, 0, Random(11)) == (first, second)
    assert decode(sample, left)
    with pytest.raises(ValueError, match="equal chromosome lengths"):
        uniform_crossover((0,), (0, 0), 1, Random(0))


def test_mutation_different_candidate_and_singleton():
    genes = (0, 1, 7, 0)
    sizes = (2, 3, 8, 1)
    changed = mutate(genes, sizes, 1, Random(42))
    assert all(new != old for new, old in zip(changed[:3], genes[:3], strict=True))
    assert changed[3] == 0
    assert all(0 <= gene < size for gene, size in zip(changed, sizes, strict=True))
    assert mutate(genes, sizes, 0, Random(42)) == genes
    assert genes == (0, 1, 7, 0)


def test_tournament_and_elite_lexicographic(tiny):
    problem = build_candidates(tiny)
    baseline = evaluate(problem, decode(problem, (0, 1, 2)))
    feasible = Individual((0, 1, 2), replace(baseline, hard_count=0, soft_penalty=9999))
    invalid = Individual((1, 2, 3), replace(baseline, hard_count=1, soft_penalty=0))
    worse = Individual((2, 3, 4), replace(baseline, hard_count=2, soft_penalty=0))
    assert tournament([invalid, feasible, worse], 3, Random(0)) is feasible
    parents = [invalid, feasible, worse]
    children = [worse, worse, worse]
    survivors = elitist_survivors(parents, children, 2, 3)
    assert survivors == [feasible, invalid, worse]
    assert parents == [invalid, feasible, worse]


@pytest.mark.parametrize("chromosome", [(), (-1, 0, 0), (0, 999, 0), (True, 0, 0), (0.5, 0, 0)])
def test_decode_rejects_invalid_genes(tiny, chromosome):
    with pytest.raises(ValueError, match="Chromosome length|Invalid candidate"):
        decode(build_candidates(tiny), chromosome)


def test_budget_refuses_extra_call(tiny):
    budget = EvaluationBudget(build_candidates(tiny), SearchConfig(max_evals=1), None)
    budget.score((0, 0, 0), 0)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        budget.score((0, 0, 0), 0)
    assert budget.count == 1


def test_random_sampling_and_seed_do_not_use_global_rng(tiny):
    import random

    before = random.getstate()
    problem = build_candidates(tiny)
    sizes = domain_sizes(problem)
    assert random_chromosome(sizes, Random(3)) == random_chromosome(sizes, Random(3))
    for solver in SOLVERS:
        solver(problem, config_for(solver, 12))
    assert random.getstate() == before


def test_greedy_selects_best_candidate_in_full_sweep(tiny):
    event = replace(tiny.events[0], duration_periods=1)
    problem = replace(
        tiny,
        events=(event,),
        candidates={event.event_id: (Placement("Mon", 7, "R1"), Placement("Mon", 1, "R1"))},
    )
    result = greedy_search(problem, SearchConfig(seed=1, max_evals=2))
    assert result.chromosome == (1,)
    assert result.evaluation.fitness == (0, 0)
