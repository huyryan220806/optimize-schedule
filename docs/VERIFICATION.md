# Kiểm chứng bản đăng GitHub

Ngày chuẩn bị: 12/11/2026. Repository đích:
[huyryan220806/optimize-schedule](https://github.com/huyryan220806/optimize-schedule).

## Phạm vi bản đăng

Bản đăng giữ ứng dụng Python/Streamlit, cấu hình cài đặt, tests, dữ liệu giả lập,
fixture kiểm thử, toàn bộ kết quả benchmark chín runs, báo cáo Word đã được người
thực hiện sửa, ảnh UI và tài liệu để chạy/trình bày/đối chiếu kết quả.

Môi trường ảo, cache, log server, bản sao Ngày 1, thư mục QA tạo lại, công cụ/prompt
Spec Kit và bộ tạo Word cục bộ không nằm trong bản đăng. Báo cáo Markdown nháp được
giữ cục bộ; bản Word là tài liệu báo cáo được bàn giao trong repository này.

## Kết quả kiểm tra

Chạy trên checkout đã chọn lọc; PYTHONPATH trỏ vào src của checkout này để không
vô tình kiểm thử source ở thư mục phát triển. Dependencies dùng môi trường Python
3.12.10 hiện có; chưa kiểm tra cài toàn bộ dependencies trong một môi trường trống.

| Kiểm tra ngày 12/11/2026 | Kết quả |
|---|---|
| python -m pytest -q | **186 passed in 27.00s** |
| python -m ruff check src tests scripts app.py | All checks passed |
| python -m pip check | No broken requirements found |
| python -m pip wheel . --no-deps | Build wheel thành công bằng isolated build dependencies |
| CLI validate sample | 24 events; fingerprint khớp nguồn |
| CLI solve GA seed42 mặc định | H=0, S=4, actual_evals=2000; thế hệ cuối 49 |
| Đối chiếu demo với checkpoint Ngày 3 | Chromosome, fitness, config và breakdown khớp |
| Đoạn source trong tài liệu GA | 9 đoạn đối chiếu trực tiếp theo file/dòng |
| Liên kết nội bộ README/demo/tài liệu mới | Không có đường dẫn file bị thiếu |
| Báo cáo Word | Giữ nguyên bytes và SHA-256 của bản người thực hiện sửa |

Lần thử wheel với --no-build-isolation ban đầu thiếu setuptools trong môi trường
hiện có; lệnh build chuẩn sử dụng isolation đã tự cài build dependencies theo
pyproject.toml và thành công. Không cần sửa solver hoặc cấu hình đóng gói.

Chứng cứ: [pytest](../checkpoints/release/pytest.txt),
[static checks](../checkpoints/release/static_checks.txt),
[build](../checkpoints/release/build.txt), [CLI](../checkpoints/release/cli.txt),
[audit](../checkpoints/release/audit.json).

## Nguồn gốc dữ liệu và mã nguồn

Benchmark gốc ngày 09/11/2026 được giữ nguyên tại results/benchmark, gồm raw runs,
summary, metadata, hội tụ và metrics/history/schedule của từng run. Runtime được
giữ đúng lần đo; chạy lại để kiểm tra không được tính thành seeds mới hoặc ghi đè
bộ số liệu dùng trong báo cáo.

Các mã commit c603cb1, 67fb65b, 2021a9b, f9591fb trong báo cáo và checkpoint là
mã lịch sử phát triển **cục bộ trước lần đăng đầu tiên**. Repository GitHub bắt đầu
bằng một snapshot đã chọn lọc để không mang theo công cụ, bản dư và lịch sử không
cần thiết. Các commit cục bộ đó không phải liên kết có thể truy cập trong lịch sử
GitHub; mã Python và artifacts tương ứng được giữ trong snapshot. Nguồn solver
không bị thay đổi khi chuẩn bị tài liệu trình bày.

Bản Word được lấy từ file người thực hiện đã sửa, không tái sinh hoặc chỉnh sửa
bằng script trong lần đăng này. Thông tin hash và manifest được lưu ở checkpoint
bản đăng. Các đoạn code trong GA_CODE_WALKTHROUGH được trích tự động từ chính source.

## Giới hạn kiểm chứng

Kiểm thử Windows không thay thế kiểm tra trên mọi hệ điều hành. Sample là dữ liệu
giả lập nhỏ, ba seeds; GA không được tuyên bố tối ưu toàn cục. Bản Word do người
thực hiện chỉnh sửa được giữ nguyên; lần đăng này không thay đổi hay tái xác nhận
toàn bộ bố cục của bản sửa đó. Chứng cứ browser demo ngày 11/11 nằm trong
[browser_smoke.json](../checkpoints/day3/browser_smoke.json).
