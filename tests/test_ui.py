"""Day 3 acceptance: visible schedules must describe the stored solver result."""

import csv
import io
from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from timetable_ga import evaluator, ui
from timetable_ga.candidates import UnschedulableEvent, build_candidates
from timetable_ga.domain import Placement, ScheduledEvent
from timetable_ga.ga import GAConfig, optimize
from timetable_ga.io import DataValidationError

from .conftest import ROOT


def test_week_grid_covers_each_period_and_keeps_collisions(tiny):
    rows = (
        ScheduledEvent("E0", Placement("Mon", 1, "R1")),
        ScheduledEvent("E1", Placement("Mon", 2, "R1")),
        ScheduledEvent("E2", Placement("Tue", 5, "R2")),
    )
    problem = replace(tiny, events=tuple(replace(event, group_id="G0") for event in tiny.events))
    frame = ui.timetable_frame(problem, rows, "G0")
    assert frame.shape == (12, 5)
    assert "E0" in frame.loc[1, "Mon"]
    assert "E0" in frame.loc[2, "Mon"] and "E1" in frame.loc[2, "Mon"]
    assert "E1" in frame.loc[3, "Mon"]
    assert "E2" in frame.loc[5, "Tue"] and "E2" in frame.loc[6, "Tue"]
    assert frame.loc[4, "Mon"] == ""
    assert ui.timetable_frame(problem, rows, "G1").eq("").all().all()


def test_week_html_escapes_dataset_text(tiny):
    problem = replace(tiny, courses=(replace(tiny.courses[0], name="<script>alert(1)</script>"),))
    rows = (ScheduledEvent("E0", Placement("Mon", 1, "R1")),)
    html = ui.timetable_html(problem, rows, "G0")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Nghỉ trưa" in html


def test_app_run_filter_and_csv_without_reevaluation(monkeypatch):
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not app.exception
    assert not app.metric
    app.button(key="optimize").click().run()
    assert not app.exception
    assert app.success[0].value == "Lịch hợp lệ"
    assert [metric.value for metric in app.metric[:2]] == ["0", "0"]
    run = app.session_state["run"]
    original_genes = run.result.chromosome
    original_history = run.result.history
    payload = app.session_state["download_csv"]
    assert len(list(csv.DictReader(io.StringIO(payload)))) == 24
    assert app.get("download_button")[0].proto.label == "Tải toàn bộ lịch CSV"

    def forbidden(*args, **kwargs):
        raise AssertionError("Filtering must not call the solver/evaluator")

    monkeypatch.setattr(ui, "optimize", forbidden)
    monkeypatch.setattr(evaluator, "evaluate", forbidden)
    app.selectbox(key="group").select("G02").run()
    assert not app.exception
    assert app.session_state["run"].result.chromosome == original_genes
    assert app.session_state["run"].result.history == original_history
    assert app.session_state["download_csv"] == payload
    assert app.selectbox(key="group").value == "G02"


def test_app_infeasible_warning_and_conflicts(tiny):
    events = tuple(replace(event, teacher_id="T0", duration_periods=1) for event in tiny.events[:2])
    problem = build_candidates(
        replace(tiny, events=events, rooms=tiny.rooms[:1], time_slots=tiny.time_slots[:1])
    )
    result = optimize(problem, GAConfig(max_evals=4, population_size=4))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    app.session_state["run"] = ui.RunView(problem, result)
    app.run()
    assert not app.exception
    assert any(warning.value == "Lịch chưa hợp lệ" for warning in app.warning)
    assert not app.success
    assert app.metric[0].value == "2"
    assert any("chẩn đoán" in caption.value for caption in app.caption)
    assert any(len(frame.value) == 2 for frame in app.dataframe)


@pytest.mark.parametrize(
    "error",
    [
        DataValidationError("assignments.csv: unknown teacher_id T404"),
        UnschedulableEvent(("A01-S01",)),
    ],
)
def test_app_input_errors_clear_previous_result(monkeypatch, sample, error):
    previous = optimize(sample, GAConfig(max_evals=4, population_size=4))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    app.session_state["run"] = ui.RunView(sample, previous)
    app.run()

    def invalid(path):
        raise error

    monkeypatch.setattr(ui, "load_problem", invalid)
    app.button(key="optimize").click().run()
    assert not app.exception
    assert str(error) in app.error[0].value
    assert "run" not in app.session_state
    assert "download_csv" not in app.session_state
    assert not app.get("download_button")


def test_app_config_reaches_solver_and_same_seed_repeats():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    app.number_input(key="seed").set_value(7)
    app.number_input(key="population").set_value(4)
    app.number_input(key="generations").set_value(0)
    app.slider(key="mutation").set_value(0.25)
    app.button(key="optimize").click().run()
    assert not app.exception
    first = app.session_state["run"].result
    assert first.actual_evals == 4
    assert first.config["seed"] == 7
    assert first.config["population_size"] == 4
    assert first.config["mutation_rate"] == 0.25
    app.button(key="optimize").click().run()
    second = app.session_state["run"].result
    assert first.chromosome == second.chromosome
    assert first.evaluation == second.evaluation
