import csv
import json
import os
import subprocess
import sys

import pytest

from timetable_ga.io import SCHEDULE_COLUMNS, DataValidationError, load_schedule

from .conftest import ROOT


def run_cli(*args, io_encoding="utf-8"):
    return subprocess.run(
        [sys.executable, "-m", "timetable_ga.cli", "validate", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": io_encoding},
        check=False,
    )


def test_cli_validate_sample():
    completed = run_cli("--data", "data/sample")
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["events"] == 24
    assert output["status"] == "data_valid"
    assert output["global_feasibility"] == "unknown"


@pytest.mark.parametrize("io_encoding", ["utf-8", "cp1252"])
def test_cli_validate_witness(io_encoding):
    completed = run_cli(
        "--data",
        "data/sample",
        "--schedule",
        "data/fixtures/sample_witness_schedule.csv",
        io_encoding=io_encoding,
    )
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["evaluation"]["hard_count"] == 0
    assert output["status"] == "schedule_valid"


def test_cli_invalid_schedule(tmp_path):
    path = tmp_path / "missing-events.csv"
    path.write_text(",".join(SCHEDULE_COLUMNS) + "\n", encoding="utf-8")
    completed = run_cli("--data", "data/sample", "--schedule", path)
    assert completed.returncode == 1
    output = json.loads(completed.stdout)
    assert output["status"] == "schedule_invalid"
    assert output["evaluation"]["hard_breakdown"]["H0"] == 24
    assert output["evaluation"]["status_label"] == "Lịch chưa hợp lệ"


def test_cli_bad_input(tmp_path):
    completed = run_cli("--data", tmp_path)
    assert completed.returncode == 2
    output = json.loads(completed.stderr)
    assert output["error_type"] == "DataValidationError"
    assert "teachers.csv" in output["message"]


def test_cli_no_candidate(data_dir, edit_csv):
    edit_csv("student_groups", lambda rows: rows[0].update(size="999"))
    completed = run_cli("--data", data_dir)
    assert completed.returncode == 2
    assert json.loads(completed.stderr)["error_type"] == "UnschedulableEvent"
    assert len(json.loads(completed.stderr)["event_ids"]) == 6


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_periods", "1"),
        ("teacher_id", "T99"),
        ("group_id", "G99"),
        ("assignment_id", "A99"),
        ("course_id", "C99"),
    ],
)
def test_schedule_metadata_cannot_override_source(tmp_path, sample, field, value):
    with (ROOT / "data/fixtures/sample_witness_schedule.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0][field] = value
    path = tmp_path / "tampered.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, SCHEDULE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(DataValidationError, match="differs from source event"):
        load_schedule(path, sample)


@pytest.mark.parametrize("algorithm", ["ga", "random", "greedy"])
def test_cli_solve_writes_real_result(tmp_path, algorithm):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "timetable_ga.cli",
            "solve",
            "--data",
            "data/sample",
            "--algorithm",
            algorithm,
            "--seed",
            "7",
            "--max-evals",
            "9",
            "--out",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode in (0, 1), completed.stderr
    output = json.loads(completed.stdout)
    assert output["actual_evals"] == 9
    assert output["algorithm"] == algorithm
    assert (completed.returncode == 0) == (output["hard_count"] == 0)
    saved = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert saved == output
    assert (tmp_path / "schedule.csv").exists()
    assert (tmp_path / "history.csv").exists()


def test_cli_solve_rejects_invalid_config(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "timetable_ga.cli",
            "solve",
            "--data",
            "data/sample",
            "--mutation",
            "nan",
            "--out",
            str(tmp_path / "invalid"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 2
    assert json.loads(completed.stderr)["error_type"] == "SolverConfigError"
    assert not (tmp_path / "invalid").exists()
