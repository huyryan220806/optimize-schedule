# 00 — CHỐT PHẠM VI 3 NGÀY (nguồn sự thật cho sprint)

## Đầu bài

Xếp **thời khóa biểu 1 tuần** cho **24 buổi học** thuộc dataset giả lập `data/sample`: 5 ngày × 8 tiết/ngày (4 sáng + 4 chiều); mỗi buổi thuộc một lớp sinh viên, một giảng viên, một học phần và chiếm một phòng trong **2 tiết liên tiếp**. Không phá các `duration_periods` từ CSV, code vẫn nên xử lý 1..4 trong cùng ca theo docs/02.

## P0 — Must have

| ID | Yêu cầu | Kiểm chứng |
|---|---|---|
| P0.1 | Load 9 CSV, validate FK, ID, types, expand assignments thành events; tính candidate placements hợp lệ local | pytest loader, lỗi malformed/no-candidate |
| P0.2 | Pure evaluator với **H0–H8** và violations chi tiết | pytest collision, room capacity/type, unavailable, multi-period |
| P0.3 | Tối thiểu S1 teacher preference, S3 late, S4 repeated-day; các soft S2/S5/S6 là stretch | pytest điểm soft so với fixtures |
| P0.4 | GA tự cài: tournament, uniform crossover theo event, random-reset mutation, elitism; seeded RNG | pytest operators, reproduce cùng seed |
| P0.5 | 2 baseline Random Search + Greedy; dùng **cùng evaluate** và ghi evaluation budget | `benchmark` xuất CSV |
| P0.6 | Đánh giá 3 solver seeds `11,22,33` trên `data/sample`; convergence + bảng kết quả `GA / Greedy / Random` | CSV + PNG sinh từ code; không bịa |
| P0.7 | UI Streamlit: chạy GA sample, nhập population/generations/mutation/seed, lịch lọc group, status & hard/soft, convergence, CSV download | demo thao tác từ đầu đến cuối |
| P0.8 | README có install/run/test; draft report 8–12 trang Markdown và ít nhất 1 hình kết quả thực | files + lệnh chạy được |

## Cách đánh giá bắt buộc

- **Thứ tự từ điển:** best = min `(hard_count, soft_penalty)`; 0 hard là *hợp lệ*, không đồng nghĩa tối ưu toàn cục.
- **Hard H0–H8:** giữ toàn bộ theo `docs/02_DOMAIN_AND_CONSTRAINTS.md` không rút gọn.
- **Soft P0:** chỉ tính S1, S3, S4 nếu config `active_soft_constraints={S1,S3,S4}`; không được báo tuân thủ S2/S5/S6. S1/S3/S4 định nghĩa và weights theo docs/02.
- **Fairness:** so sánh cùng instance, cùng evaluation budget (ví dụ 2.000 full evaluations/solver/seed), đếm toàn bộ lời gọi evaluate trong solver. Nếu Greedy dùng incremental scoring, đếm/giải thích chi phí và tuyệt đối không gọi là so sánh hoàn toàn ngang bằng nếu không tương đương.
- `witness_schedule.csv` chỉ phục vụ evaluator unit test; KHÔNG dùng làm lời giải khởi tạo GA/Greedy/Random khi benchmark.
- Nếu sample 24 events chưa tìm được 0 hard: báo feasible rate theo thực tế; vẫn có thể hoàn thành demo với cảnh báo rõ.

## Gợi ý cấu hình ban đầu (không bảo đảm tốt)

`GAConfig(population=40, generations=50, crossover=0.85, mutation=0.10, elitism=2, tournament=3, seed=42)`; nên kiểm soát `max_evals=2000` (và đếm full evaluator calls). Nếu runtime chậm, giảm đồng loạt budget, ghi thay đổi. Nên lưu `elapsed_sec` nhưng không coi runtime ngang bằng evaluation effort.

## Day-by-day / thời điểm chốt

- **D1:** dataset + evaluator + tests đúng; CLI `validate` chạy, fixture witness được chấm 0 hard. Không viết UI/GA sớm.
- **D2:** GA + 2 baseline chạy, đúng seed/reproducibility, `results/` có `raw_runs.csv`, `summary.csv`, `convergence.png`; kiểm tra lịch 0 hard nếu tìm được.
- **D3:** demo Streamlit hoạt động, CSV download, end-to-end smoke test, report ngắn có số đo thực + hướng dẫn setup.

## Bỏ / hoãn để chắc chắn xong

**Không thực hiện trong sprint:** repair nâng cao, multi-objective/NSGA-II, CP-SAT, hyperparameter sweep đầy đủ, 10 seeds, medium/large datasets, tuning theo benchmark seeds, import ZIP, authentication, database, đồ thị Gantt phức tạp, export PDF/Word, triển khai server.

**Nếu có thêm giờ:** repair 1-pass bị chặn evaluation; thí nghiệm 2 mutation rates `0.05,0.15` trên *seeds riêng*, nhóm GV/phòng trong UI; bổ sung S2/S5/S6 và tests. Không làm stretch nếu P0 chưa pass.

## Định nghĩa hoàn thành / DoD

- `python -m pytest -q` pass (giữ output thực).
- `python -m timetable_ga.cli validate --data data/sample` chạy thành công.
- Một lịch 0 hard từ fixture đã được evaluator xác nhận; thuật toán tự tìm được 0 hard hay chưa phải báo trung thực.
- `run benchmark` tạo 9 dòng raw runs (3 algos × 3 seeds), status + hard + soft-feasible-only + eval count + runtime; đồ thị từ raw results.
- Streamlit chạy trên CPU, lịch khó/không khả thi hiển thị cảnh báo, không crash.
- Báo cáo mô tả thuật toán, thí nghiệm, hạn chế, hình thật, không phóng đại kết quả.

## Nêu rõ "không làm" không có nghĩa "bỏ kiểm thử"

Không hy sinh evaluator và correctness để chạy demo. Nếu thiếu thời gian hơn dự kiến: giữ D1+D2 và làm UI chỉ gồm bảng lịch + nút tải CSV; cắt chart đẹp/tùy chỉnh mở rộng, **không** bỏ H0–H8 hoặc sửa dữ liệu để tạo thành công giả.
