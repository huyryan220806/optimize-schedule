"""Headless input validation and optional schedule evaluation."""

import argparse
import json
import sys
from collections.abc import Sequence

from timetable_ga.baselines import greedy_search, random_search
from timetable_ga.candidates import UnschedulableEvent
from timetable_ga.evaluator import evaluate
from timetable_ga.ga import GAConfig, optimize
from timetable_ga.io import DataValidationError, load_problem, load_schedule
from timetable_ga.outputs import export_result
from timetable_ga.search import SearchConfig, SolverConfigError


def main(argv: Sequence[str] | None = None) -> int:
    # Windows pipes may default to cp1252; the JSON contract is always UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="timetable-ga")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate nine CSVs and local domains")
    validate.add_argument("--data", required=True)
    validate.add_argument("--schedule", help="Optional schedule CSV; evaluated independently")
    solve = commands.add_parser("solve", help="Run GA, Greedy, or Random Search")
    solve.add_argument("--data", required=True)
    solve.add_argument("--algorithm", choices=("ga", "greedy", "random"), default="ga")
    solve.add_argument("--seed", type=int, default=42)
    solve.add_argument("--max-evals", type=int, default=2000)
    solve.add_argument("--population", type=int, default=40)
    solve.add_argument("--generations", type=int, default=50)
    solve.add_argument("--mutation", type=float, default=0.10)
    solve.add_argument("--crossover", type=float, default=0.85)
    solve.add_argument("--elitism", type=int, default=2)
    solve.add_argument("--tournament", type=int, default=3)
    solve.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        problem = load_problem(args.data)
        if args.command == "solve":
            if args.algorithm == "ga":
                config = GAConfig(
                    seed=args.seed,
                    max_evals=args.max_evals,
                    population_size=args.population,
                    generations=args.generations,
                    mutation_rate=args.mutation,
                    crossover_rate=args.crossover,
                    elite_count=args.elitism,
                    tournament_size=args.tournament,
                )
                result = optimize(problem, config)
            else:
                config = SearchConfig(seed=args.seed, max_evals=args.max_evals)
                solver = greedy_search if args.algorithm == "greedy" else random_search
                result = solver(problem, config)
            export_result(problem, result, args.out)
            print(json.dumps(result.metrics(), ensure_ascii=False, indent=2))
            return 0 if result.evaluation.feasible else 1
        sizes = {key: len(value) for key, value in problem.candidates.items()}
        output = {
            "status": "data_valid",
            "events": len(problem.events),
            "dataset_fingerprint": problem.dataset_fingerprint,
            "candidate_counts": sizes,
            "global_feasibility": "unknown",
        }
        if args.schedule:
            result = evaluate(problem, load_schedule(args.schedule, problem))
            output["evaluation"] = result.to_dict()
            output["global_feasibility"] = "witness_validated" if result.feasible else "unknown"
            output["status"] = "schedule_valid" if result.feasible else "schedule_invalid"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1 if output["status"] == "schedule_invalid" else 0
    except (DataValidationError, UnschedulableEvent, SolverConfigError, OSError) as exc:
        error = {"status": "error", "error_type": type(exc).__name__, "message": str(exc)}
        if isinstance(exc, UnschedulableEvent):
            error["event_ids"] = list(exc.event_ids)
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
