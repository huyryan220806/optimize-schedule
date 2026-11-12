# Demo GA Timetable — khoảng 5 phút

Thực hiện từ thư mục gốc repository. Đây là dữ liệu giả lập 24 buổi;
không dùng fixture witness làm đầu vào solver. Kết quả đã kiểm chứng ngày 11/11/2026.

## Chuẩn bị

Nếu chưa có môi trường, làm bước cài đặt trong [README](README.md). Khởi động:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Mở [http://127.0.0.1:8501](http://127.0.0.1:8501). Nếu cổng đang có phiên demo,
dùng phiên đó. Muốn mở phiên riêng có thể thêm `--server.port 8502` rồi mở cổng 8502.
Cửa sổ hẹp: mở sidebar bằng mũi tên góc trên trái; bảng lịch có cuộn ngang.

## Kịch bản trình bày

| Thời gian | Thao tác | Nội dung giải thích |
|---|---|---|
| 0:00–1:00 | Chọn sample; seed42, population40, generations50, mutation0.10; Optimize | GA tự viết, tối đa 2.000 lần chấm lịch đầy đủ; không dùng witness |
| 1:00–2:00 | Đọc trạng thái và H/S; chọn G01 rồi G02 | Đã đo H=0, S=4; mỗi event chiếm đủ hai tiết; đổi nhóm không tìm lại lịch |
| 2:00–3:00 | Mở chi tiết ràng buộc và xem convergence | H0–H8; soft S1/S3/S4; ưu tiên tuple H rồi S; soft chart chỉ khi H=0 |
| 3:00–4:00 | Tải toàn bộ lịch CSV; chạy CLI validate bên dưới | 24 events của bốn nhóm; bộ lọc chỉ đổi bảng; CSV có thể kiểm tra độc lập |
| 4:00–5:00 | Mở bảng benchmark trong báo cáo | GA 3/3 khả thi, Greedy 3/3, Random 2/3; Greedy soft tốt hơn GA trên sample; n=3 |

H=0 chỉ xác nhận các hard constraints trong mô hình. Không nói “tối ưu toàn cục”.
Runtime có thể khác ảnh và benchmark; chromosome/fitness tái lập theo seed/config/data.

## Ba lệnh demo có thể chạy trực tiếp

Lệnh 1 kiểm tra bộ dữ liệu, trả 24 events và fingerprint:

```powershell
.\.venv\Scripts\python.exe -m timetable_ga.cli validate --data data/sample
```

Lệnh 2 chạy GA và lưu đầy đủ schedule/metrics/history, kết quả đã đo H=0/S=4:

```powershell
.\.venv\Scripts\python.exe -m timetable_ga.cli solve --data data/sample --algorithm ga --seed 42 --out results/demo
```

Lệnh 3 kiểm tra CSV tải về (thay tên nếu trình duyệt lưu thành schedule (1).csv):

```powershell
.\.venv\Scripts\python.exe -m timetable_ga.cli validate --data data/sample --schedule "$env:USERPROFILE\Downloads\schedule.csv"
```

CSV tải từ UI đã được kiểm chứng: 24 dòng, nhóm G01–G04, H=0/S=4,
giống lịch CLI seed42. Bản chứng cứ ở `checkpoints/day3/ui_schedule.csv`.

## Minh họa cảnh báo khi chưa tìm được lịch hợp lệ

Trong UI đặt seed7, population4, generations0, mutation0.10 rồi Optimize.
Cấu hình này chỉ chấm bốn cá thể khởi tạo, chưa chạy thế hệ tiến hóa.
CLI tương đương đã đo **H=13, S=20**, trạng thái **Lịch chưa hợp lệ**:

```powershell
.\.venv\Scripts\python.exe -m timetable_ga.cli solve --data data/sample --seed 7 --population 4 --generations 0 --out results/demo_short
```

Exit code 1 ở ví dụ này là kết quả chưa khả thi, vẫn có files để kiểm tra.
Không kết luận dataset vô nghiệm: mặc định seed42 đã tìm được lịch H=0.
Sau minh họa, khôi phục 42/40/50/0.10 và nhấn Optimize.

## Lỗi thường gặp và cách tiếp tục

| Dấu hiệu | Cách xử lý |
|---|---|
| Không thấy controls | Mở sidebar bằng mũi tên góc trái |
| Không thấy đủ năm ngày | Cuộn ngang bảng hoặc mở cửa sổ trình duyệt rộng hơn |
| Đổi seed nhưng metric chưa đổi | Nhấn Optimize; metric mô tả lần chạy đã lưu |
| Lịch chưa hợp lệ | Xem H1/H2/H3 và chi tiết event-period; dùng lại cấu hình demo đã kiểm chứng |
| Input lỗi / no-candidate | Đọc thông báo file/ID; sửa CSV theo schema rồi chạy lại; không bỏ constraint |
| Module không tìm thấy | Dùng Python trong .venv và cài `-m pip install -e ".[dev]"` tại root |
| Tắt app làm mất kết quả | Dùng CSV đã tải hoặc chạy CLI để lưu metrics/history lâu dài |

Tests đã mô phỏng dữ liệu sai và no-candidate; không cần sửa dataset gốc để demo lỗi.
Không có upload hoặc tài khoản trong bản sprint. Dừng server terminal bằng Ctrl+C.

## Tài liệu trình bày

- [Giải thích chi tiết code GA và câu hỏi vấn đáp](docs/GA_CODE_WALKTHROUGH.md).
- [Báo cáo Word đã chỉnh sửa](reports/BAO_CAO_GA_THOI_KHOA_BIEU_HK261.docx).
- [Convergence đã lưu](results/benchmark/convergence.png).
- [Kiểm chứng bản đăng](docs/VERIFICATION.md).
