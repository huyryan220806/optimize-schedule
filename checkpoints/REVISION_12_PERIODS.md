# Checkpoint cập nhật 12 tiết theo góp ý giảng viên

Ngày 13/11/2026, Asia/Saigon. D1–D3 đã hoàn thành; đây là yêu cầu sửa sau sprint.

## Thay đổi đã thực hiện

- Domain, loader, candidates, evaluator và UI dùng 12 tiết, ba ca 1–4/5–8/9–12.
- Sample có 60 time slots; ca tối evening. S3 chỉ phạt tiết 11/12, trọng số 1.
- H0–H8 vẫn đầy đủ, fitness lexicographic; không đổi toán tử GA, không dùng witness.
- Hình 2 thêm chọn lọc và lai ghép; code chuyển thành mục 2.6 cuối chương 2.
- Word mới giữ bìa người dùng sửa, có bảng trọng số, số đo mới, hình và nguồn.
- README, hướng dẫn demo, giải thích code, domain/schema và spec được đồng bộ.

## Lệnh và kết quả

Chạy từ root với `.venv/Scripts/python.exe`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts app.py
.\.venv\Scripts\python.exe scripts/benchmark.py --data data/sample --seeds 11 22 33 --out results/benchmark_12periods
.\.venv\Scripts\python.exe -m timetable_ga.cli solve --data data/sample --seed 42 --out results/demo_12periods
.\.venv\Scripts\python.exe -m timetable_ga.cli validate --data data/sample --schedule results/demo_12periods/schedule.csv
```

200 tests pass, Ruff pass. Demo seed42 H=0/S=0, 2000 evaluations; CSV đủ 24 events.
Demo ngắn seed7/population4/generations0: H=6/S=17, hiển thị lịch chưa hợp lệ.
Benchmark mới: cả ba phương pháp khả thi 3/3; median S GA=0, Greedy=8, Random=11.
Replay 9/9 khớp chromosome/fitness/config/schedule/history, bỏ qua runtime.

Word 17 trang được xuất PDF bằng Microsoft Word, rasterize qua render_docx.py và
kiểm tra ảnh toàn bộ trang. Mục lục đã sửa đúng số trang 7/8/9/10 cho mục 2.3–2.6.
PDF/ảnh QA và bản nguồn sao lưu chỉ giữ cục bộ dưới reports/generated/12periods.

Chứng cứ: [artifact audit](12periods/artifact_audit.json), [pytest](12periods/pytest.txt),
[Ruff](12periods/ruff.txt), [demo](12periods/solve.json),
[CSV](12periods/schedule.csv), [validate](12periods/validate_schedule.json).

Các số đo 8 tiết trong results/benchmark và checkpoint cũ là lịch sử, không dùng
thay cho bộ 12 tiết. Không khẳng định GA tối ưu toàn cục hoặc luôn thắng baseline.

## Trạng thái bàn giao

Code, dữ liệu, báo cáo và tài liệu đã hoàn tất kiểm tra cục bộ. Checkout chọn lọc
cũng đạt 200 tests pass (28.28s), Ruff pass và pip check pass. Bản đăng chỉ giữ
các file cần thiết; commit push và xác nhận remote được lưu tại
checkpoints/progress.json của workspace phát triển sau khi push.
Không còn việc triển khai chức năng ngoài phạm vi đã yêu cầu.
