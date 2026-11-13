# Kiểm chứng bản cập nhật 12 tiết

Ngày kiểm tra: 13/11/2026. Repository đích:
[huyryan220806/optimize-schedule](https://github.com/huyryan220806/optimize-schedule).

## Phạm vi bản cập nhật

Chương trình, dữ liệu và báo cáo dùng 12 tiết/ngày: sáng 1–4, chiều 5–8, tối 9–12.
S3 chỉ phạt tiết 11–12, trọng số 1. Các buổi dài nhiều tiết phải nằm trọn trong
một ca. Bộ sample có 60 time slots và 24 events; giờ học là giả lập.

Hình 2 của Word có bước chọn lọc và lai ghép; code chuyển thành mục 2.6 cuối
chương 2. Báo cáo mới giữ nguyên bìa người thực hiện đã sửa, cập nhật bảng trọng
số, thực nghiệm, hình, nguồn và mục lục. Bản cũ giữ cục bộ và trong lịch sử Git.

## Kết quả kiểm tra

| Kiểm tra | Kết quả |
|---|---|
| pytest toàn bộ | 200 tests pass |
| Ruff | All checks passed |
| Sample mới | 5 × 12 time slots; loader nhận ba ca |
| Ranh giới ca | Không vượt 4→5, 8→9 hoặc 12→13; kiểm tra mọi occupied period |
| S3 | Tiết 7–10 không bị phạt; tiết 11/12 mỗi occupied period phạt 1 |
| Demo GA seed42 mặc định | H=0, S=0, actual_evals=2000 |
| Demo seed7, population4, generations0 | H=6, S=17; Lịch chưa hợp lệ |
| CSV demo | 24 events; đọc lại và chấm độc lập khớp metrics |
| Benchmark 3 phương pháp × 3 seeds | Mỗi run 2000 evaluations; cả ba phương pháp 3/3 khả thi |
| Median S khả thi | GA=0; Greedy=8; Random Search=11 |
| Replay 9 runs | Chromosome, fitness, config, schedule, history khớp; không so runtime |
| Tài liệu giải thích GA | 9 đoạn code khớp source theo file/dòng |
| Word | 17 trang; render bằng Word và kiểm tra toàn bộ ảnh trang; mục lục khớp |

Checkout chọn lọc cũng đạt **200 passed in 28.28s**, Ruff pass và pip check pass.
PYTHONPATH được trỏ vào src của checkout khi chạy để không vô tình kiểm tra
source ở workspace chính. Log: [publication pytest](../checkpoints/12periods/publication_pytest.txt)
và [static checks](../checkpoints/12periods/publication_static.txt).

Chứng cứ: [pytest](../checkpoints/12periods/pytest.txt),
[Ruff](../checkpoints/12periods/ruff.txt),
[demo](../checkpoints/12periods/solve.json),
[CSV](../checkpoints/12periods/schedule.csv),
[validate](../checkpoints/12periods/validate_schedule.json),
[artifact audit](../checkpoints/12periods/artifact_audit.json).

Streamlit AppTest kiểm tra lịch 12 hàng, đổi nhóm không chấm lại và CSV chứa đủ
events. Chứng cứ thao tác trình duyệt cũ ở checkpoints/day3 thuộc phiên bản 8 tiết;
không dùng ảnh cũ để minh họa kết quả mới. Hình 5 mới biểu diễn CSV seed42 và ghi
rõ nguồn CSV, không được mô tả là ảnh chụp UI.

## Truy vết thực nghiệm

Bộ số đo mới nằm ở [benchmark_12periods](../results/benchmark_12periods/metadata.json),
ghi seed, config, fingerprint dữ liệu/mã nguồn và môi trường. Replay QA dùng thư
mục riêng, không ghi đè runtime đã đo và không được cộng thành seeds mới.

results/benchmark và checkpoints/day1, day2, day3, release là chứng cứ lịch sử
8 tiết của sprint và lần đăng 12/11. Miền lựa chọn và S3 đã đổi nên không trộn
hai bộ số liệu hoặc dùng điểm mềm cũ để đánh giá chương trình hiện tại.
Các mã commit phát triển cục bộ trong checkpoint cũ có thể không tồn tại trong
lịch sử GitHub vì bản đăng đầu tiên là một snapshot đã chọn lọc.

## Bản đăng và giới hạn

Giữ code, cấu hình cài đặt, tests, dữ liệu giả lập, fixture kiểm thử, số đo,
báo cáo Word và tài liệu chạy/trình bày. Không đăng môi trường ảo, cache,
log server, bản sao project cũ, công cụ/prompt Spec Kit, bộ tạo Word và ảnh QA.
Fixture witness chỉ dùng kiểm thử, không được đọc vào solver khi đo kết quả.

Kiểm thử dùng Windows/Python 3.12.10 và môi trường dependencies hiện có; chưa
xác minh trên mọi hệ điều hành hoặc cài sạch. Sample nhỏ giả lập, chỉ ba seeds.
Kết quả không chứng minh GA luôn tốt hơn hoặc đạt tối ưu toàn cục.
