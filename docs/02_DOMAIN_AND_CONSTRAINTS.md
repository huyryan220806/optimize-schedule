# 02 — Domain model, constraints, objective

> **SPRINT 3 NGÀY:** H0–H8 vẫn BẮT BUỘC. Chỉ bật soft S1, S3, S4 trong MVP; S2/S5/S6 là mở rộng. Hàm evaluate dùng `active_soft_constraints` để không vô tình tính các soft chưa implement.

## Miền dữ liệu

- `Teacher`: teacher_id, name.
- `StudentGroup`: group_id, name, size.
- `Room`: room_id, name, capacity, room_type (`lecture|lab`).
- `Course`: course_id, course_name.
- `Assignment`: assignment_id, course_id, group_id, teacher_id, sessions_per_week, duration_periods, required_room_type.
- `Event`: event_id, assignment_id, derived group_id, teacher_id, course_id, size, duration (sinh từ assignment).
- `TimeSlot`: day ∈ {Mon,Tue,Wed,Thu,Fri}, period ∈ {1..8}, block ∈ {morning,afternoon}, start/end.
- `Placement`: (day, start_period, room_id), occupancy là mọi `(day, period)` từ start tới start+duration-1.

## Quy tắc thời gian

- Mon–Fri: tiết 1..4 buổi sáng, 5..8 buổi chiều; tiết học phải chiếm **các period liên tiếp trong cùng block**. Không xếp sự kiện bắt đầu vào tiết 4 khi duration=2; cũng không xếp 8 với duration=2. Không được đi qua ngày khác.
- Mỗi sự kiện chọn **chính xác một** placement thuộc candidate domain; không chọn cùng lúc hai phòng.
- Teacher/room unavailable được khai báo theo từng `(id, day, period)`; nếu bất kỳ tiết chiếm nào trùng unavailable thì placement bị cấm.

## H: hard constraints

H0. **Tính toàn vẹn**: đúng 1 placement/event, không thiếu event, không event ID lạ, không placement vô hiệu, không split-session.
H1. **Giảng viên**: không có hai event cùng teacher chiếm cùng day-period.
H2. **Nhóm sinh viên**: không có hai event cùng group chiếm cùng day-period.
H3. **Phòng**: không có hai event cùng room chiếm cùng day-period.
H4. **Sức chứa**: `room.capacity >= group.size`.
H5. **Loại phòng**: `room.room_type == required_room_type`, trừ khi data schema sau này định nghĩa compatibility matrix rõ ràng.
H6. **Teacher unavailable**: mọi tiết chiếm không thuộc danh sách cấm của teacher.
H7. **Room unavailable**: mọi tiết chiếm không thuộc danh sách cấm của room.
H8. **Ca học**: liên tiếp, không vượt quá 1 ca hoặc lịch tuần.

### Cách đếm vi phạm để tránh double count

- Đếm H1/H2/H3 **theo số cặp event xung đột trên từng period**; với 3 event chung phòng tại 1 tiết là C(3,2)=3, không phải 2 hoặc 1.
- H4/H5/H8: mỗi event vi phạm 1 lỗi/loại; H6/H7: mỗi `(event, period)` cấm tính 1 lỗi.
- H0: mỗi event bị thiếu hoặc lặp hoặc có placement lạ là 1 lỗi theo loại, và ghi danh sách cụ thể.
- Một lịch có thể có nhiều loại lỗi cho cùng event; report từng loại; `hard_count = sum(count_by_type)`.
- Candidate domain được lọc H4–H8 ngay từ đầu nhưng **validator chạy độc lập** trên kết quả, không mặc định mọi gene đều sạch.

## S: soft constraints (giá trị gợi ý, cho phép config)

| Mã | Mô tả | Định nghĩa điểm phạt gốc | Weight mặc định |
|---|---|---|---:|
| S1 | Không hợp preference GV | số occupied periods trong danh sách `avoid` | 3 |
| S2 | Khoảng trống nhóm trong 1 ca | số period trống giữa min/max occupied period trong mỗi group/day/block | 2 |
| S3 | Tiết cuối ngày | số occupied periods ở period 7 hoặc 8 | 1 |
| S4 | Cùng assignment dồn một ngày | với mỗi assignment, `max(0, sessions - distinct_days)` | 5 |
| S5 | Phòng quá rộng | tổng `max(0, room.capacity - group.size)` trên mỗi event, chia 10 | 0.2 |
| S6 | Một assignment nhiều phòng | `max(0, distinct_rooms_for_assignment - 1)` | 2 |

`soft_penalty = Σ(weight_i × raw_penalty_i)`. Điểm S2 chỉ tính **bên trong mỗi ca** để không phạt nghỉ trưa. S4 bằng 0 nếu các buổi ở ngày khác nhau; với 2 buổi cùng ngày phạt 1. S1 chỉ áp dụng trên tiết preference avoid (khác unavailable hard).

## Fitness và so sánh

**Quan trọng: dùng thứ tự từ điển**:

```text
fitness(schedule) = (hard_count, soft_penalty)
A tốt hơn B nếu A.hard_count < B.hard_count,
hoặc cùng hard_count thì A.soft_penalty < B.soft_penalty.
```

Điều này luôn ưu tiên lịch 0 hard hơn lịch 1 hard dù soft rất cao; không cần dựa vào một hệ số phạt tùy ý như `1000*H + S`. Nên expose `total_display_score` cho UI nếu muốn nhưng **không dùng để rank**.

## Không có lịch khả thi / dữ liệu thiếu

- Nếu 1 event không có placement vượt qua lọc H4..H8 ⇒ preflight trả `UnschedulableEvent` và không chạy GA.
- Nếu từng event có domain nhưng các event cùng tranh chấp tài nguyên khiến toàn cục bất khả thi, GA có thể không đạt 0 hard; trạng thái: `best_found_infeasible`, hiển thị số lỗi và lý do, **không tuyên bố vô nghiệm** nếu không có bằng chứng đầy đủ.
- Tránh nhầm `zero hard` với `global optimum`: điểm mềm vẫn có thể cải thiện.

## Mini-example kiểm chứng

2 events cùng teacher `T01`, duration=2:
- E01 ở Mon tiết 1–2 phòng R101.
- E02 ở Mon tiết 2–3 phòng R102.
⇒ H1 = 1 (chồng 1 period), H2/H3 tùy group/room. Nếu E02 cũng R101 thì thêm H3 = 1.

## Khác benchmark ITC2007

ITC 2007 xem room capacity là soft và thường mô hình mỗi lecture một period; dự án này cố ý xem capacity là hard, event kéo dài nhiều period. Không so sánh trực tiếp raw benchmark score. Tham khảo: https://www.eeecs.qub.ac.uk/itc2007/curriculmcourse/course_curriculm_index_files/problemmodel.htm
