# Checkpoint Ngày 3 — DONE

**Ngày:** 11/11/2026, Asia/Saigon.

**Working root:** `D:\VLU\261\Optimizer\Project`.

**Branch:** `001-timetable-mvp`. **Commit UI:** `2021a9b`.

Ngày 1, Ngày 2 và Ngày 3 đều hoàn thành theo scope P0. Không còn task sprint
phải triển khai tiếp. Mục Deferred cần phạm vi mới; không tự chuyển sang repair,
thêm constraints, tuning, upload, auth/database, hosting hoặc export Word/PDF.

## Kết quả bàn giao

- Streamlit một trang: sample, seed/population/generations/mutation, Optimize,
  status H/S, bảng tuần theo group, chi tiết vi phạm, hai đường hội tụ, CSV download.
- Session state giữ nguyên result khi đổi group. UI không gọi evaluator;
  mọi fitness/status/history lấy từ solver result. Lỗi input/no-candidate xóa lịch cũ.
- Lịch nhiều tiết hiện đủ occupied periods; ô trùng giữ tất cả events, có nghỉ trưa;
  dữ liệu được escape trước khi hiển thị HTML. Cửa sổ hẹp dùng cuộn ngang.
- Report Markdown có 9 runs và summary sinh từ CSV, convergence thật, ảnh UI,
  mô hình, pseudocode, kết luận và giới hạn. Khoảng 4.015 từ theo bộ đếm khoảng trắng;
  mục tiêu 8–12 trang khi dàn trang, chưa xuất/đo số trang Word/PDF.
- README cập nhật cài/chạy/test; DEMO_GUIDE có kịch bản 5 phút và ví dụ lịch H>0.

## File thêm hoặc sửa

| Nhóm | File |
|---|---|
| UI / dependencies | `app.py`, `src/timetable_ga/ui.py`, `.streamlit/config.toml`, `pyproject.toml` |
| Tests | `tests/test_ui.py` (7 cases gồm parameterization) |
| Report | `scripts/report_tables.py`, `reports/REPORT_DRAFT.md`, `reports/assets/streamlit_demo.jpg`, `reports/assets/streamlit_group.jpg` |
| Hướng dẫn | `README.md`, `DEMO_GUIDE.md` |
| Theo dõi | `specs/001-timetable-mvp/plan.md`, `specs/001-timetable-mvp/tasks.md`, `SPRINT_STATUS.md`, `checkpoints/progress.json`, checkpoint này |
| Chứng cứ | `checkpoints/day3/` chứa logs test/CLI/install, audit, health, bản CSV tải từ UI |
| Git ignore | `.gitignore` bỏ qua log server còn chạy |

Không thay solver/evaluator, dataset sample, witness hoặc artifacts benchmark Ngày 2.
Kết quả QA tái tạo nằm ở `results/day3_qa/` (local, ignored); audit và logs được commit.

## Lệnh chạy và kết quả thật

Tất cả lệnh dưới chạy tại working root; Python `.venv` là 3.12.10.

| Lệnh / kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| `python -m pip install -e ".[dev]"` | Pass, Streamlit 1.67.0 | `day3/install.txt` |
| `python -m pip check` | No broken requirements found | `day3/pip_check.txt` |
| `python -m pytest -q` | **186 passed in 36.16s** | `day3/pytest.txt` |
| `python -m ruff check src tests scripts app.py` | All checks passed | `day3/ruff.txt` |
| `python -m timetable_ga.cli validate --data data/sample` | Exit 0, 24 events | `day3/validate.json` |
| Validate `data/fixtures/sample_witness_schedule.csv` | Exit 0, H=0/S=4 | `day3/witness.json` |
| Solve GA seed42, output `results/day3_qa/demo` | Exit 0, H=0/S=4, evals=2000 | `day3/solve.json` |
| Solve seed7/population4/generations0 | Exit 1, H=13/S=20, evals=4, “Lịch chưa hợp lệ” | `day3/solve_infeasible.json` |
| Solve population0 | Exit 2, SolverConfigError | `day3/invalid_config.json` |
| Validate thư mục dữ liệu không tồn tại | Exit 2, thông báo file thiếu | `day3/missing_data.json` |
| Benchmark sample, seeds11/22/33, output `results/day3_qa/benchmark` | 9 runs, mỗi run đúng 2000 evals | `day3/benchmark.txt` |
| So QA replay với benchmark Ngày 2 | 9/9 cùng config/chromosome/fitness/schedule/history; mọi lịch được evaluate lại độc lập | `day3/artifact_audit.json` |
| `python scripts/report_tables.py` rồi `--check` | Bảng khớp raw CSV, summary và history | `day3/report_tables.txt` |
| Health server `127.0.0.1:8501/_stcore/health` | HTTP 200, `ok` | `day3/server_health.json` |
| Browser Optimize, đổi G01→G02→G01, tải CSV | H=0/S=4; metrics không đổi khi lọc; tải thành công | `day3/browser_smoke.json`, ảnh report |
| Validate CSV trong Downloads bằng CLI | Exit 0, H=0/S=4 | `day3/ui_validate.json` |

Các lệnh đầy đủ để lặp lại gate chính:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts app.py
.\.venv\Scripts\python.exe -m timetable_ga.cli validate --data data/sample
.\.venv\Scripts\python.exe -m timetable_ga.cli validate --data data/sample --schedule data/fixtures/sample_witness_schedule.csv
.\.venv\Scripts\python.exe -m timetable_ga.cli solve --data data/sample --algorithm ga --seed 42 --out results/day3_qa/demo
.\.venv\Scripts\python.exe scripts/benchmark.py --data data/sample --seeds 11 22 33 --out results/day3_qa/benchmark
.\.venv\Scripts\python.exe scripts/report_tables.py --check
.\.venv\Scripts\python.exe -m timetable_ga.cli validate --data data/sample --schedule checkpoints/day3/ui_schedule.csv
```

Pytest, cài package và QA benchmark chạy đồng thời trong gate. Runtime replay
không được dùng thay số benchmark Ngày 2; không cộng thành sáu seeds/run.
Revalidation sau khi chạy không thuộc solver evaluation budget. Chỉ runtime
được loại khỏi điều kiện so khớp metrics giữa Ngày 2 và replay.

## Browser và lỗi

Trình duyệt đã thực sự chạy app tại `http://127.0.0.1:8501`. Cấu hình
42/40/50/0.10 cho H=0, S=4, 2.000 evals. Đã đổi nhóm G01→G02, tải CSV
và khôi phục G01; metric và runtime của lần chạy giữ nguyên khi lọc.
CSV tải xuống có 24 events, đủ G01–G04, khớp toàn bộ schedule CLI seed42.
Bản sao chứng cứ: `day3/ui_schedule.csv` (UTF-8 BOM).

AppTest kiểm tra input error, no-candidate, jointly infeasible, đổi cấu hình,
same-seed, no-evaluation-on-filter và download payload. Các lỗi này được kiểm
tra bằng fixture/monkeypatch; không sửa dữ liệu mẫu trong phiên demo trình duyệt.

Server demo được để chạy local (không public hosting), lúc tạo checkpoint PID 11380.
Logs local ở `day3/streamlit.stdout.log`, `day3/streamlit.stderr.log`, không commit.
PID có thể thay đổi hoặc server dừng sau phiên; dùng lệnh Streamlit trong README
để mở lại. Sau khi restart, cần Optimize lại vì result UI nằm trong session memory.

## Benchmark dùng cho báo cáo

Giữ nguyên nguồn Ngày 2: `results/benchmark/`, commit artifacts `f9591fb`, solver
`67fb65b`. GA 3/3 H=0 (median S=3), Greedy 3/3 (median S=0), Random 2/3
(median S=19,5 trên runs khả thi). Greedy tốt hơn GA về soft trên sample.
Chỉ n=3, dataset giả lập, không khẳng định ý nghĩa thống kê hoặc tối ưu toàn cục.
Fixture witness không được đọc/seed vào solver hoặc baseline.

## Spec Kit và trạng thái tiếp tục

Đã dùng skill `speckit-implement` với tasks hiện có, không bootstrap lại.
Script prerequisite được chạy với:

```powershell
$env:SPECIFY_FEATURE_DIRECTORY = 'D:\VLU\261\Optimizer\Project\specs\001-timetable-mvp'
.\.specify\scripts\powershell\check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
```

Không có checklist gate bổ sung. Kiểm tra cuối thấy `.specify/extensions.yml`
không tồn tại, nên không có after_implement hook cần chạy. Tasks D3.1–D3.4 đã tick.
Progress machine-readable: `checkpoints/progress.json`, completed_days `[1,2,3]`.

**Việc chưa làm trong phạm vi đã chốt:** không còn. Các mục Deferred vẫn giữ nguyên.
Bản cũ `GA_Timetable_3Ngay_Codex_SpecKit` còn tồn tại như đã ghi ở checkpoint D2
vì thao tác chuyển/xóa trước đó bị automatic review chặn; đây là việc dọn thư mục
từ lượt trước, không phải blocker P0 hoặc thay đổi mới trong Ngày 3.
