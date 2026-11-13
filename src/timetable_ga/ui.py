"""Streamlit presentation of stored solver results; never recomputes fitness."""

from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from timetable_ga.candidates import UnschedulableEvent
from timetable_ga.domain import DAYS, PERIODS, ProblemInstance, ScheduledEvent
from timetable_ga.ga import GAConfig, optimize
from timetable_ga.io import DataValidationError, load_problem
from timetable_ga.outputs import schedule_csv
from timetable_ga.search import OptimizationResult, SolverConfigError

ROOT = Path(__file__).resolve().parents[2]
DAY_LABELS = dict(zip(DAYS, ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu"), strict=True))


@dataclass(frozen=True)
class RunView:
    problem: ProblemInstance
    result: OptimizationResult


def timetable_frame(
    problem: ProblemInstance,
    schedule: tuple[ScheduledEvent, ...],
    group_id: str,
) -> pd.DataFrame:
    """Map every occupied period to a cell; retain all entries in overlapping cells."""
    events = {event.event_id: event for event in problem.events}
    courses = {course.course_id: course.name for course in problem.courses}
    cells = {(period, day): [] for period in PERIODS for day in DAYS}
    for row in schedule:
        event = events[row.event_id]
        placement = row.placement
        if event.group_id != group_id or placement is None:
            continue
        text = (
            f"{courses[event.course_id]}\n"
            f"{placement.room_id} · {event.teacher_id}\n{event.event_id}"
        )
        for period in placement.occupied_periods(event.duration_periods):
            if (period, placement.day) in cells:
                cells[period, placement.day].append(text)
    return pd.DataFrame(
        {day: ["\n\n".join(cells[period, day]) for period in PERIODS] for day in DAYS},
        index=pd.Index(PERIODS, name="Tiết"),
    )


def timetable_html(
    problem: ProblemInstance,
    schedule: tuple[ScheduledEvent, ...],
    group_id: str,
) -> str:
    """Accessible week table with escaped labels and breaks between three blocks."""
    frame = timetable_frame(problem, schedule, group_id)
    slots = {(slot.day, slot.period): slot for slot in problem.time_slots}
    rows = []
    for period in PERIODS:
        time_slot = next((slots[day, period] for day in DAYS if (day, period) in slots), None)
        time_label = f"{time_slot.start}–{time_slot.end}" if time_slot and time_slot.start else ""
        cells = [f'<th scope="row">Tiết {period}<small>{escape(time_label)}</small></th>']
        for day in DAYS:
            text = frame.loc[period, day]
            lessons = text.split("\n\n") if text else []
            content = (
                "".join(
                    '<div class="lesson">'
                    + "<br>".join(escape(line) for line in lesson.splitlines())
                    + "</div>"
                    for lesson in lessons
                )
                or '<span class="empty">—</span>'
            )
            cells.append(f'<td class="{"overlap" if len(lessons) > 1 else ""}">{content}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
        if period == 4:
            rows.append(
                '<tr class="lunch"><td colspan="6">Nghỉ trưa · Ca chiều bắt đầu từ tiết 5</td></tr>'
            )
        elif period == 8:
            rows.append(
                '<tr class="lunch"><td colspan="6">'
                'Nghỉ chuyển ca · Ca tối bắt đầu từ tiết 9</td></tr>'
            )
    headers = '<th scope="col">Thời gian</th>' + "".join(
        f'<th scope="col">{DAY_LABELS[day]}</th>' for day in DAYS
    )
    return (
        """
    <style>
    .week-scroll { overflow-x:auto; border:1px solid #dce6e9; border-radius:12px; }
    .week-table { width:100%; min-width:720px; border-collapse:collapse; table-layout:fixed;
                  font:13px/1.45 sans-serif; color:#182f3a; }
    .week-table th { background:#f3f7f8; text-align:left; padding:12px; font-weight:600; }
    .week-table th:first-child { width:115px; }
    .week-table th small { display:block; color:#657b85; font-size:11px; font-weight:400; }
    .week-table td { border-top:1px solid #e6edef; border-left:1px solid #e6edef;
                     padding:6px; height:70px; vertical-align:top; }
    .week-table .lesson { background:#e9f5f4; border-left:3px solid #087f8c;
                          border-radius:5px; padding:7px; margin-bottom:3px;
                          overflow-wrap:anywhere; }
    .week-table .overlap .lesson { background:#fff0e9; border-color:#b85825; }
    .week-table .empty { color:#b7c5ca; display:block; padding:10px; }
    .week-table .lunch td { height:auto; background:#f8fafb; text-align:center;
                            color:#657b85; font-size:12px; padding:7px; }
    </style>
    """
        + '<div class="week-scroll"><table class="week-table" aria-label="Thời khóa biểu tuần">'
        + f"<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_app() -> None:
    st.set_page_config(page_title="GA Timetable", page_icon="📅", layout="wide")
    st.caption("GA TIMETABLE  /  LỊCH HỌC MỘT TUẦN")
    st.title("Sắp xếp lịch học, kiểm tra từng ràng buộc.")
    st.write("Tìm thời khóa biểu bằng giải thuật di truyền trên dữ liệu mô phỏng.")
    with st.sidebar:
        st.header("Cấu hình tìm kiếm")
        with st.form("ga_settings"):
            st.selectbox("Bộ dữ liệu", ["sample"], key="dataset")
            seed = st.number_input("Seed", min_value=0, max_value=2**31 - 1, value=42, key="seed")
            population = st.number_input(
                "Kích thước quần thể",
                min_value=4,
                max_value=200,
                value=40,
                step=1,
                key="population",
            )
            generations = st.number_input(
                "Số thế hệ", min_value=0, max_value=200, value=50, step=1, key="generations"
            )
            mutation = st.slider(
                "Xác suất đột biến",
                min_value=0.0,
                max_value=1.0,
                value=0.10,
                step=0.01,
                key="mutation",
            )
            submitted = st.form_submit_button("Optimize", type="primary", key="optimize")
        st.caption(
            "Tối đa 2.000 lần đánh giá mỗi lần chạy. "
            "Cùng dữ liệu, seed và cấu hình cho cùng kết quả."
        )

    if submitted:
        for key in ("run", "download_csv", "group"):
            st.session_state.pop(key, None)
        try:
            with st.spinner("Đang tìm lịch và kiểm tra ràng buộc…"):
                problem = load_problem(ROOT / "data/sample")
                config = GAConfig(
                    seed=int(seed),
                    population_size=int(population),
                    generations=int(generations),
                    mutation_rate=float(mutation),
                )
                result = optimize(problem, config)
                st.session_state["run"] = RunView(problem, result)
        except (DataValidationError, UnschedulableEvent, SolverConfigError, OSError) as exc:
            st.error(f"Không thể tạo lịch: {exc}")

    if "run" not in st.session_state:
        st.info("Chọn cấu hình bên trái rồi nhấn Optimize để tạo lịch.")
        return

    run = st.session_state["run"]
    problem, result = run.problem, run.result
    score = result.evaluation
    if score.feasible:
        st.success(score.status_label)
    else:
        st.warning(score.status_label)
        st.caption(
            "Điểm mềm chỉ có ý nghĩa chẩn đoán khi lịch còn vi phạm cứng. "
            "Xem chi tiết lỗi bên dưới."
        )
    columns = st.columns(4)
    for column, label, value in zip(
        columns,
        ("Vi phạm cứng (H)", "Điểm mềm (S)", "Lần đánh giá", "Thời gian tìm kiếm"),
        (
            str(score.hard_count),
            f"{score.soft_penalty:g}",
            f"{result.actual_evals:,}",
            f"{result.runtime_sec:.2f} s",
        ),
        strict=True,
    ):
        column.metric(label, value)
    st.caption(
        f"Kết quả lần chạy: seed {result.config['seed']} · "
        f"quần thể {result.config['population_size']} · "
        f"{result.config['generations']} thế hệ · đột biến {result.config['mutation_rate']:.0%}. "
        "Thay cấu hình rồi nhấn Optimize để chạy lại."
    )
    st.divider()
    st.subheader("Thời khóa biểu tuần")
    groups = {group.group_id: group.name for group in problem.groups}
    group_id = st.selectbox(
        "Nhóm sinh viên",
        list(groups),
        key="group",
        format_func=lambda value: f"{groups[value]} · {value}",
    )
    st.html(timetable_html(problem, result.schedule, group_id))
    st.caption(
        "Mỗi ô hiển thị môn học, phòng · giảng viên và mã buổi. "
        "Buổi nhiều tiết xuất hiện ở mọi tiết chiếm."
    )
    payload = schedule_csv(problem, result.schedule)
    st.session_state["download_csv"] = payload
    st.download_button(
        "Tải toàn bộ lịch CSV",
        data=payload.encode("utf-8-sig"),
        file_name="schedule.csv",
        mime="text/csv",
        key="download",
        on_click="ignore",
    )
    st.caption("CSV chứa tất cả nhóm của lần chạy này; bộ lọc nhóm chỉ thay đổi bảng hiển thị.")

    with st.expander("Chi tiết ràng buộc và xung đột", expanded=not score.feasible):
        if score.violations:
            st.dataframe(pd.DataFrame(asdict(item) for item in score.violations), hide_index=True)
        else:
            st.write("Không có vi phạm cứng H0–H8.")
        st.dataframe(
            pd.DataFrame(
                {
                    "Ràng buộc": list(score.hard_breakdown),
                    "Số lỗi": list(score.hard_breakdown.values()),
                }
            ),
            hide_index=True,
        )
        st.dataframe(
            pd.DataFrame(
                {
                    "Ràng buộc mềm": list(score.soft_raw),
                    "Điểm gốc": list(score.soft_raw.values()),
                    "Điểm có trọng số": list(score.soft_weighted.values()),
                }
            ),
            hide_index=True,
        )

    st.subheader("Tiến trình tối ưu")
    history = pd.DataFrame(asdict(entry) for entry in result.history).set_index("evaluation")
    hard_column, soft_column = st.columns(2)
    with hard_column:
        st.caption("Vi phạm cứng tốt nhất · theo số lần đánh giá")
        st.line_chart(
            history[["best_hard"]].rename(columns={"best_hard": "H tốt nhất"}), height=230
        )
    with soft_column:
        st.caption("Điểm mềm tốt nhất · chỉ khi H = 0")
        if history.best_soft_if_feasible.notna().any():
            st.line_chart(
                history[["best_soft_if_feasible"]].rename(
                    columns={"best_soft_if_feasible": "S khi H=0"}
                ),
                height=230,
            )
        else:
            st.info("Chưa có lịch H=0 trong lần chạy này.")
    st.caption(
        "12 tiết/ngày: sáng 1–4, chiều 5–8, tối 9–12. "
        "Đang xét S1: preference giảng viên, S3: tiết muộn 11–12, S4: dồn buổi cùng ngày. "
        "H=0 không phải tuyên bố tối ưu toàn cục."
    )
