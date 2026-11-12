"""Fixed three-seed experiment, reproducible raw data, and figures from saved history."""

import argparse
import hashlib
import json
import platform
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from timetable_ga.baselines import greedy_search, random_search
from timetable_ga.ga import GAConfig, optimize
from timetable_ga.io import load_problem
from timetable_ga.outputs import export_result
from timetable_ga.search import SearchConfig, SolverConfigError


def source_fingerprint() -> str:
    """Identify code that produced these files, independent of output directory or Git state."""
    root = Path(__file__).resolve().parents[2]
    files = sorted((root / "src/timetable_ga").glob("*.py"))
    files += sorted((root / "scripts").glob("*.py"))
    files += [root / "pyproject.toml"]
    digest = hashlib.sha256()
    for path in files:
        if path.exists():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode())
    return digest.hexdigest()


def plot_convergence(directory: str | Path, seeds: tuple[int, ...]) -> None:
    """Read recorded GA histories; infeasible soft values are never plotted."""
    root = Path(directory)
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, layout="constrained")
    feasible_seen = False
    for seed in seeds:
        frame = pd.read_csv(root / f"ga_seed_{seed}" / "history.csv")
        axes[0].step(frame.evaluation, frame.best_hard, where="post", label=f"Seed {seed}")
        if frame.best_soft_if_feasible.notna().any():
            feasible_seen = True
            axes[1].step(
                frame.evaluation, frame.best_soft_if_feasible, where="post", label=f"Seed {seed}"
            )
    axes[0].set(
        title=f"GA convergence: {metadata['dataset_id']} ({metadata['events']} events)",
        ylabel="Best hard violations",
    )
    axes[1].set(ylabel="Best soft penalty (H = 0 only)", xlabel="Full evaluator calls")
    axes[0].legend()
    if feasible_seen:
        axes[1].legend()
    else:
        axes[1].text(
            0.5,
            0.5,
            "No feasible schedule found within budget",
            ha="center",
            transform=axes[1].transAxes,
        )
    for axis in axes:
        axis.set_ylim(bottom=0)
        axis.grid(alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
    figure.savefig(root / "convergence.png", dpi=160)
    plt.close(figure)


def run_benchmark(
    data: str | Path,
    out: str | Path,
    seeds: tuple[int, ...] = (11, 22, 33),
    max_evals: int = 2000,
    ga_config: GAConfig | None = None,
) -> pd.DataFrame:
    """Run exactly three methods by three distinct seeds with a common full-call cap."""
    if len(seeds) != 3 or len(set(seeds)) != 3:
        raise SolverConfigError("Benchmark requires exactly three distinct seeds")
    for seed in seeds:
        SearchConfig(seed, max_evals)
    config = ga_config or GAConfig()
    problem = load_problem(data)
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone(timedelta(hours=7))).isoformat()
    records = []
    for algorithm in ("random", "greedy", "ga"):
        for seed in seeds:
            if algorithm == "ga":
                result = optimize(problem, replace(config, seed=seed, max_evals=max_evals))
            else:
                solver = random_search if algorithm == "random" else greedy_search
                result = solver(problem, SearchConfig(seed, max_evals))
            export_result(problem, result, root / f"{algorithm}_seed_{seed}")
            score = result.evaluation
            records.append(
                {
                    "algorithm": algorithm,
                    "seed": seed,
                    "dataset_id": Path(data).name,
                    "dataset_fingerprint": problem.dataset_fingerprint,
                    "max_evals": max_evals,
                    "actual_evals": result.actual_evals,
                    "hard_count": score.hard_count,
                    "soft_penalty": score.soft_penalty,
                    "soft_feasible_only": score.soft_penalty if score.feasible else None,
                    "feasible": score.feasible,
                    "status": score.status,
                    "status_label": score.status_label,
                    "runtime_sec": result.runtime_sec,
                    "stop_reason": result.stop_reason,
                    "config_json": json.dumps(result.config, sort_keys=True),
                }
            )
    pd.DataFrame(records).to_csv(root / "raw_runs.csv", index=False)
    # Summaries, including feasible-only soft medians, derive from the persisted raw data.
    raw = pd.read_csv(root / "raw_runs.csv")
    summary = []
    for algorithm, group in raw.groupby("algorithm", sort=True):
        feasible = group[group.hard_count == 0]
        summary.append(
            {
                "algorithm": algorithm,
                "feasible_x_of_3": f"{len(feasible)}/3",
                "feasible_rate": len(feasible) / 3,
                "median_hard": group.hard_count.median(),
                "median_soft_feasible_only": feasible.soft_penalty.median()
                if len(feasible)
                else None,
                "median_runtime": group.runtime_sec.median(),
                "median_actual_evals": group.actual_evals.median(),
            }
        )
    pd.DataFrame(summary).to_csv(root / "summary.csv", index=False)
    metadata = {
        "started_at": started,
        "timezone": "Asia/Saigon",
        "dataset": str(Path(data).resolve()),
        "dataset_id": Path(data).name,
        "events": len(problem.events),
        "dataset_fingerprint": problem.dataset_fingerprint,
        "source_fingerprint": source_fingerprint(),
        "seeds": list(seeds),
        "max_evals": max_evals,
        "runs": len(raw),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {name: version(name) for name in ("timetable-ga", "pandas", "matplotlib")},
        "witness_used": False,
        "repair_enabled": False,
        "protocol": (
            "Full complete-schedule evaluations; cached elites/current greedy fitness are reused, "
            "not re-counted. No incremental scorer. Common cap; actual calls reported."
        ),
        "greedy": (
            "Multi-start hardest-event-first coordinate sweep over full random completions; "
            "one sweep per restart."
        ),
        "ga": (
            "Random initial population; up to population_size offspring evaluated per generation; "
            "parent elites plus best children survive."
        ),
        "limitations": (
            "Synthetic sample, n=3; illustrative comparison, "
            "no statistical or global-optimality claim."
        ),
    }
    (root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plot_convergence(root, seeds)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/sample")
    parser.add_argument("--seeds", type=int, nargs=3, default=[11, 22, 33])
    parser.add_argument("--max-evals", type=int, default=2000)
    parser.add_argument("--out", default="results/benchmark")
    args = parser.parse_args()
    try:
        raw = run_benchmark(args.data, args.out, tuple(args.seeds), args.max_evals)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Benchmark error: {exc}\n")
    print(
        raw[
            ["algorithm", "seed", "actual_evals", "hard_count", "soft_feasible_only", "runtime_sec"]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
