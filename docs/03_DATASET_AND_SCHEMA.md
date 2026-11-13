# 03 — Dataset specification & CSV contract

> **SPRINT 3 NGÀY:** Chỉ triển khai và kiểm tra `data/sample/` + witness, chưa cần generator medium/large. Schema và các validation cơ bản dưới đây vẫn bắt buộc.

## Dữ liệu đầu vào mẫu (đã có file)

```text
data/sample/
  teachers.csv
  student_groups.csv
  rooms.csv
  courses.csv
  assignments.csv
  time_slots.csv
  teacher_unavailability.csv
  room_unavailability.csv
  teacher_preferences.csv
```

### Columns và kiểu dữ liệu

| File | Cột (bắt buộc) | Điều kiện |
|---|---|---|
| `teachers.csv` | `teacher_id,name` | teacher_id duy nhất, khác rỗng |
| `student_groups.csv` | `group_id,name,size` | size nguyên dương |
| `rooms.csv` | `room_id,name,capacity,room_type` | capacity >0; room_type `lecture|lab` |
| `courses.csv` | `course_id,name` | ID duy nhất |
| `assignments.csv` | `assignment_id,course_id,group_id,teacher_id,sessions_per_week,duration_periods,required_room_type` | khóa ngoại tồn tại; sessions>=1, duration 1..4 |
| `time_slots.csv` | `day,period,block,start,end` | day `Mon..Fri`, period 1..12, block `morning` cho 1..4, `afternoon` cho 5..8, `evening` cho 9..12; mỗi tuple `(day,period)` duy nhất |
| `teacher_unavailability.csv` | `teacher_id,day,period` | không được phép dạy tại period; file có thể rỗng có header |
| `room_unavailability.csv` | `room_id,day,period` | phòng đóng tại period; file có thể rỗng có header |
| `teacher_preferences.csv` | `teacher_id,day,period,preference` | `avoid` là phạt mềm, không phải unavailable; file có thể rỗng |

Số sinh viên của event lấy từ `student_groups.size`; nếu một môn có số học viên khác quy mô group, phải mở rộng schema theo version và cập nhật test trước khi triển khai. Không lẳng lặng dùng số người học giả.

**Sinh event:** 1 assignment A01 với sessions_per_week=2 sinh `A01-S01`, `A01-S02`. Trong CSV output `event_id,assignment_id,course_id,group_id,teacher_id,day,start_period,duration_periods,room_id` và một option xuất thêm `occupied_periods` để dễ kiểm tra.

## Bộ dữ liệu mẫu

- 7 teachers, 4 groups, 6 rooms, 7 courses, 12 assignments × 2 sessions = **24 events**.
- 5 ngày × 12 period = 60 period/tuần mỗi phòng.
- Mỗi event dài 2 period.
- Ca tối minh họa: tiết 9 18:00–18:50, tiết 10 18:55–19:45, tiết 11 19:55–20:45, tiết 12 20:50–21:40. Đây là giờ giả lập, không phải lịch chuông chính thức của trường.
- Có room lecture/lab, capacity đủ/không đủ tùy nhóm và room; có unavailable giờ GV/phòng và soft preference.
- Dữ liệu **giả lập**; seed CSV chỉ để demo và test loader/solver. Không có kết quả tối ưu đã đo trước.

## Loader/preflight

Thứ tự: load files → validate schema → check unique IDs & FKs → expand events → precompute candidate placements → fail if any event has no valid candidate → build `ProblemInstance` immutable.

- Bắt buộc reject duration > block length; ngày/period lạ, tham chiếu sai; duplicate ID; data type lỗi.
- Candidate placements phải thỏa **local hard constraints** (độ dài, sức chứa, loại phòng, teacher/room unavailable). Xung đột với event khác kiểm tra ở fitness/repair.
- Đọc CSV UTF-8 (có thể nhận UTF-8 BOM), cung cấp thông báo lỗi dễ hiểu.
- Tạo `dataset_fingerprint` ổn định bằng hash các bảng đã chuẩn hóa sắp xếp theo key để so sánh runs.

## Generator dataset tăng kích thước (Codex sẽ code)

**Đề xuất generator có thể tái lập**:

| Tên | Events mục tiêu | Groups | Teachers | Rooms | Gợi ý mô phỏng |
|---|---:|---:|---:|---:|---|
| small | 24 | 4 | 7 | 6 | dataset CSV mẫu |
| medium | 60 | 10 | 15 | 12 | nhiều tranh chấp teacher/room |
| large | 120 | 20 | 28 | 20 | bài kiểm tra scaling |

Tạo các **feasible instances có witness lịch** bằng cách dựng lịch hợp lệ trước, rồi tạo assignment/constraints tương thích, xáo trộn. Đọc tài liệu `07_TEST_AND_ACCEPTANCE.md` để kiểm chứng witness bằng validator độc lập. Không được giả vờ rằng mọi dữ liệu ngẫu nhiên đều khả thi. Nếu generator sinh dataset không có witness, dán nhãn `feasibility_unknown`.

- `seed` quyết định mọi giá trị giả lập.
- `manifest.json` gồm `schema_version`, `seed`, `events`, `groups`, `teachers`, `rooms`, `feasibility_status` (`witness_validated|unknown`), sha256 fingerprint.
- Tách `witness_schedule.csv` riêng trong `data/generated/...`; **solver không được đọc witness** lúc tối ưu, chỉ dùng trong test/validator và reporting.
- Nên có `adversarial/infeasible` instance cố ý có xung đột để kiểm tra trạng thái thất bại.

## Test datasets bắt buộc

- `sample`: file hiện có, xác thực schema và ngoại khóa.
- `tiny_feasible`: 2–4 events, có lịch witness đã validator xác nhận 0 hard.
- `tiny_conflict`: 2 events cùng teacher/phòng cùng period, assert count đúng.
- `no_candidate`: event cần lab hơn mọi lab capacity hoặc teacher unavailable toàn bộ thời gian, assert preflight fail rõ.
- `jointly_infeasible`: từng event có candidate nhưng cùng tranh tài nguyên khiến không có lịch; solver trả best found/không tuyên bố chứng minh vô nghiệm.

## Tích hợp dữ liệu ngoài (sau v1)

ITC 2007 Curriculum-Based Course Timetabling là benchmark đáng tham khảo, nhưng có schema và quy định capacity/duration **khác**; muốn dùng phải viết adapter + evaluator chuẩn benchmark riêng, không trộn metric. Official: https://www.eeecs.qub.ac.uk/itc2007/curriculmcourse/course_curriculm_index.htm
