import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from timetable_ga import evaluator
from timetable_ga.baselines import random_search
from timetable_ga.benchmark import run_benchmark, source_fingerprint
from timetable_ga.candidates import build_candidates
from timetable_ga.ga import GAConfig
from timetable_ga.io import load_schedule
from timetable_ga.outputs import export_result
from timetable_ga.search import SearchConfig, SolverConfigError

from .conftest import ROOT


def test_export_roundtrip_and_no_extra_evaluation(sample, tmp_path, monkeypatch):
    result = random_search(sample, SearchConfig(seed=8, max_evals=10))

    def forbidden(*args):
        raise AssertionError("Export must not call evaluate")

    monkeypatch.setattr(evaluator, "evaluate", forbidden)
    export_result(sample, result, tmp_path)
    assert load_schedule(tmp_path / "schedule.csv", sample) == result.schedule
    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["fitness"] == list(result.evaluation.fitness)
    assert metrics["actual_evals"] == 10
    assert metrics["dataset_fingerprint"] == sample.dataset_fingerprint
    assert len(pd.read_csv(tmp_path / "history.csv")) == 10


def test_benchmark_nine_runs_summary_and_figure(tmp_path, monkeypatch):
    original_open = Path.open

    def guard(path, *args, **kwargs):
        assert "witness" not in path.name.lower(), "Solver/benchmark must never open witness"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guard)
    out = tmp_path / "benchmark"
    raw = run_benchmark(
        ROOT / "data/sample",
        out,
        seeds=(1, 2, 3),
        max_evals=12,
        ga_config=GAConfig(population_size=4, generations=2, elite_count=1),
    )
    assert len(raw) == 9
    assert set(zip(raw.algorithm, raw.seed, strict=True)) == {
        (algorithm, seed) for algorithm in ("random", "greedy", "ga") for seed in (1, 2, 3)
    }
    assert set(raw.actual_evals) == {12}
    assert raw.dataset_fingerprint.nunique() == 1
    assert raw.loc[raw.hard_count > 0, "soft_feasible_only"].isna().all()
    assert (out / "convergence.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    summary = pd.read_csv(out / "summary.csv").set_index("algorithm")
    for algorithm, group in raw.groupby("algorithm"):
        feasible = group[group.hard_count == 0]
        row = summary.loc[algorithm]
        assert row.median_hard == group.hard_count.median()
        assert row.feasible_x_of_3 == f"{len(feasible)}/3"
        if len(feasible):
            assert row.median_soft_feasible_only == feasible.soft_penalty.median()
        else:
            assert pd.isna(row.median_soft_feasible_only)
    metadata = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["witness_used"] is False
    assert metadata["source_fingerprint"] == source_fingerprint()
    assert metadata["runs"] == 9


def test_infeasible_summary_keeps_soft_blank(tiny, tmp_path, monkeypatch):
    import timetable_ga.benchmark as benchmark

    events = tuple(replace(event, teacher_id="T0", duration_periods=1) for event in tiny.events[:2])
    problem = build_candidates(
        replace(tiny, events=events, rooms=tiny.rooms[:1], time_slots=tiny.time_slots[:1])
    )
    monkeypatch.setattr(benchmark, "load_problem", lambda path: problem)
    raw = run_benchmark("tiny", tmp_path, max_evals=2)
    assert (raw.hard_count == 2).all()
    assert raw.soft_feasible_only.isna().all()
    summary = pd.read_csv(tmp_path / "summary.csv")
    assert summary.median_soft_feasible_only.isna().all()
    assert (summary.feasible_x_of_3 == "0/3").all()


@pytest.mark.parametrize("seeds", [(1, 1, 2), (1, 2), (1, 2, 3, 4)])
def test_benchmark_requires_three_distinct_seeds(tmp_path, seeds):
    with pytest.raises(SolverConfigError, match="three distinct"):
        run_benchmark(ROOT / "data/sample", tmp_path, seeds=seeds)
