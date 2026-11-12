# 001 — GA timetable MVP

Nguồn yêu cầu: `docs/00_3_DAY_SCOPE.md`, schema và cách đếm tại `docs/02`, `docs/03`.

## User stories và acceptance

1. D1: người dùng kiểm tra 9 CSV và biết chính xác file/dòng/cột lỗi. Sample nở
   thành 24 events, mỗi event có local candidate domain. Không có candidate thì
   trả lỗi `UnschedulableEvent`. Fingerprint ổn định với thứ tự dòng CSV.
2. D1: evaluator độc lập chấm lịch theo `(hard_count, soft_penalty)`, trả đủ
   H0–H8, từng violation và raw/weighted S1/S3/S4. Witness H=0 chỉ là fixture.
   CLI `validate --data data/sample` chạy; pytest kiểm tra toàn bộ quy tắc.
3. D2: Random Search, Greedy và GA dùng cùng evaluator, candidate indices và
   seeded RNG. Cùng seed/config/data cho cùng chromosome/fitness; không đọc witness.
   Budget tối đa 2.000 full evaluations/run; benchmark 3 phương pháp × seeds
   11,22,33 xuất raw_runs.csv, summary.csv và convergence.png từ thực thi thật.
4. D3: Streamlit chạy GA, lọc group, hiển thị lịch và violations, H/S, convergence,
   tải CSV. H>0 phải hiện “Lịch chưa hợp lệ”. README, báo cáo và smoke test hoàn tất.

## Quy ước evaluator cần chốt

- Schedule là dãy `ScheduledEvent(event_id, placement)`, giữ được bản ghi trùng
  để H0 phát hiện; placement luôn là một day/start_period/room, duration lấy từ
  event gốc, nên không cho client tự sửa duration hoặc split-session.
- H0: mỗi ID thiếu/trùng/lạ tính một lỗi theo loại; mỗi event có placement không
  xác định được (room/day/start không hợp lệ hoặc period không tồn tại) tính một
  lỗi invalid-placement. Candidate vi phạm local H4–H8 được báo theo đúng mã đó,
  không nhân đôi H0 chỉ vì nằm ngoài candidate domain.
- Với input H0-invalid, các bản ghi placement có thể diễn giải vẫn được chấm
  H4–H8; collision đếm cặp **event ID khác nhau** trên từng period. Kết quả soft
  của lịch malformed không được dùng để suy ra chất lượng lịch hợp lệ.
- H8 đếm một lần/event cho vượt ca/tuần hoặc thiếu occupied period; H6/H7 đếm
  từng event-period. H4/H5 cũng chỉ một lần/event dù bản ghi bị lặp.
- Time slots có thể là tập con của tuần; unavailable/preferences phải tham chiếu
  slot tồn tại. Validate HH:MM, start < end, đúng thứ tự và không chồng giờ trong ngày.
- Soft chưa implement (S2/S5/S6) bị từ chối rõ khi cấu hình, không âm thầm bỏ qua.

## Deferred

Repair, S2/S5/S6, dataset generator, tuning, >3 benchmark seeds, upload ZIP,
auth/database, triển khai server, export Word/PDF và khẳng định tối ưu toàn cục.
