# Giải thích code GA để trình bày đồ án thời khóa biểu

Tài liệu này giải thích **đúng thuật toán đang chạy trong repository**, từ CSV đến lịch
được trả về. Các đoạn code trích nguyên từ source; ví dụ số tự đặt đều ghi là minh họa.
Phần cuối có kịch bản nói, câu hỏi vấn đáp và kết quả thực nghiệm để đối chiếu.

Nếu chỉ còn 30 phút: đọc mục 1, 3, 5–10 và phần Câu hỏi thầy có thể hỏi. Khi trình bày,
mở song song file [ga.py](../src/timetable_ga/ga.py) và tài liệu này.

## 1. Cách giới thiệu trong một phút

> Bài toán của nhóm là gán ngày, tiết bắt đầu và phòng cho 24 buổi học. Mỗi lịch đầy đủ
> được mã hóa thành một chromosome gồm 24 gene. Mỗi gene chọn một vị trí hợp lệ cục bộ
> cho một buổi. GA tạo nhiều lịch ngẫu nhiên, chấm theo tuple (H, S), chọn cha mẹ bằng
> tournament, lai đồng đều, đột biến từng gene và giữ lại cá thể tốt bằng elitism.
> H là tổng vi phạm cứng, luôn được ưu tiên trước điểm phạt mềm S. Sau tối đa 2.000 lần
> đánh giá, chương trình trả lịch tốt nhất đã gặp. Kết quả demo seed 42 là H=0, S=0.
> Với ba seed thực nghiệm, GA tìm được lịch hợp lệ cả ba lần, GA có median điểm mềm thấp hơn Greedy và Random trên sample 12 tiết. Nhóm không kết luận GA luôn tốt hơn hoặc đã tối ưu toàn cục.

Số demo đối chiếu [solve.json](../checkpoints/12periods/solve.json); kết quả so sánh nằm trong
[raw_runs.csv](../results/benchmark_12periods/raw_runs.csv), không lấy từ ví dụ minh họa.

## 2. Các file cần hiểu và thứ tự đọc

| Thứ tự | File và hàm | Vai trò |
|---|---|---|
| 1 | [domain.py](../src/timetable_ga/domain.py) | Event, Placement, ProblemInstance, ScheduledEvent |
| 2 | [io.py](../src/timetable_ga/io.py) | Đọc 9 CSV, kiểm tra dữ liệu, mở rộng assignment thành events |
| 3 | [candidates.py: build_candidates](../src/timetable_ga/candidates.py#L18) | Tạo danh sách placement của từng event |
| 4 | [search.py](../src/timetable_ga/search.py) | Chromosome, decode, budget, best-so-far, history |
| 5 | [evaluator.py: evaluate](../src/timetable_ga/evaluator.py#L90) | Chấm H0–H8 và S1/S3/S4 |
| 6 | [ga.py](../src/timetable_ga/ga.py) | Các toán tử và vòng lặp tiến hóa |
| 7 | [baselines.py](../src/timetable_ga/baselines.py) | Hai đối chứng dùng chung bộ chấm |
| 8 | [ui.py](../src/timetable_ga/ui.py) | Gọi GA và hiển thị kết quả, không tự chấm fitness |

~~~mermaid
flowchart TD
    A[9 CSV] --> B[Loader kiểm tra dữ liệu]
    B --> C[Events và candidate domains]
    C --> D[Khởi tạo quần thể bằng RNG có seed]
    D --> E[Chấm từng cá thể và lưu best]
    E --> F{Còn budget và thế hệ?}
    F -->|Có| G[Chọn hai cha mẹ bằng tournament]
    G --> H[Uniform crossover]
    H --> I[Random reset mutation]
    I --> J[Chấm con và cập nhật best cùng history]
    J --> K{Đủ con hoặc hết budget?}
    K -->|Chưa| G
    K -->|Rồi| L[Giữ parent elites và con tốt nhất]
    L --> F
    F -->|Không| M[OptimizationResult chứa best đã gặp]
    M --> N[UI hoặc CSV và metrics]
~~~

## 3. Gene và chromosome thực sự chứa gì?

### 3.1 Từ phân công đến buổi học

Assignment là một phân công giảng dạy. Nếu A01 có sessions_per_week=2, loader tạo
A01-S01 và A01-S02. Mỗi event giữ course, teacher, group, sĩ số, loại phòng và số tiết.
Thứ tự events được cố định để gene ở vị trí i luôn nói về cùng một event.

Placement chứa ba thành phần: **ngày, tiết bắt đầu, phòng**. Duration lấy từ event,
không nằm trong gene để GA tự sửa. Ví dụ event dài hai tiết đặt Mon, 2, R101 sẽ chiếm
cả tiết 2 và 3; không được tách hai tiết sang hai phòng.

### 3.2 Mã hóa bằng chỉ số candidate

Ví dụ minh họa rút gọn, không phải dataset benchmark:

| Event | Candidate 0 | Candidate 1 | Candidate 2 |
|---|---|---|---|
| E1 | Mon, 1, R101 | Tue, 1, R101 | Wed, 5, R101 |
| E2 | Mon, 3, LAB1 | Thu, 5, LAB1 | Không có |
| E3 | Tue, 5, R102 | Wed, 1, R102 | Fri, 1, R102 |

Chromosome (2, 0, 1) chọn candidate 2 của E1, candidate 0 của E2 và candidate 1 của E3.
**Gene=2 không có nghĩa tiết 2, phòng số 2 hoặc thứ Ba.** Nó chỉ là vị trí trong domain
của event tương ứng. Cùng số 0 ở hai gene có thể chỉ hai placements hoàn toàn khác nhau.

Nếu kích thước domains là (3, 2, 3), số tổ hợp trước khi xét xung đột toàn cục là
3×2×3=18. Tổng quát là tích các kích thước domain, không phải tổng. Với nhiều events,
việc duyệt hết tổ hợp nhanh chóng trở nên tốn kém.

Nguồn code khởi tạo:

Nguồn: [search.py, dòng 96–97](../src/timetable_ga/search.py#L96).

~~~python
def random_chromosome(sizes: Sequence[int], rng: Random) -> Chromosome:
    return tuple(rng.randrange(size) for size in sizes)
~~~

rng.randrange(size) lấy chỉ số từ 0 đến size−1. Mỗi event có size riêng, vì vậy sinh
gene luôn nằm trong domain của event đó. Kết quả là tuple bất biến; các toán tử tạo
tuple mới, không âm thầm sửa chromosome cha mẹ.

Nguồn code giải mã:

Nguồn: [search.py, dòng 100–110](../src/timetable_ga/search.py#L100).

~~~python
def decode(problem: ProblemInstance, chromosome: Chromosome) -> tuple[ScheduledEvent, ...]:
    """Reject bad gene lengths/types/indices before constructing a complete schedule."""
    if len(chromosome) != len(problem.events):
        raise ValueError("Chromosome length differs from event count")
    schedule = []
    for event, index in zip(problem.events, chromosome, strict=True):
        candidates = problem.candidates.get(event.event_id, ())
        if type(index) is not int or not 0 <= index < len(candidates):
            raise ValueError(f"Invalid candidate index for {event.event_id}: {index!r}")
        schedule.append(ScheduledEvent(event.event_id, candidates[index]))
    return tuple(schedule)
~~~

decode kiểm tra độ dài chromosome, kiểu int và giới hạn chỉ số trước khi tra candidate.
Kiểm tra type(index) is int còn loại cả bool: trong Python bool có quan hệ kế thừa với
int, nhưng True/False không được chấp nhận làm gene ở đây. Hàm này trả lịch đầy đủ,
chưa khẳng định lịch không xung đột.

## 4. Vì sao sinh candidate rồi vẫn cần evaluator?

[build_candidates](../src/timetable_ga/candidates.py#L18) duyệt ngày, tiết bắt đầu,
phòng và lọc các điều kiện **của riêng một event**:

- Sức chứa phòng đủ và loại phòng đúng: H4, H5.
- Giảng viên và phòng đều rảnh ở **mọi tiết chiếm**: H6, H7.
- Duration từ 1 đến 4, đủ tiết tồn tại và chỉ nằm trong một ca: H8.

Ví dụ duration=2, start=4 bị loại vì chiếm cả tiết 4 và 5, đi qua nghỉ trưa.
Start=6 bị loại nếu giảng viên bận tiết 7, dù rảnh tiết 6. Đây là lý do code dùng
vòng lặp trên periods thay vì kiểm tra riêng start_period.

Candidate chưa biết các event khác chọn gì. Hai gene riêng lẻ đều hợp lệ vẫn có thể
chọn cùng phòng, cùng giảng viên hoặc cùng nhóm ở cùng tiết, gây H1/H2/H3.
Evaluator kiểm tra độc lập cả H0–H8, kể cả khi nhận lịch CSV từ bên ngoài và kể cả
nếu candidate generator có lỗi. Không có domain cho một event thì dừng preflight;
có domain cho tất cả events vẫn chưa chứng minh khả thi toàn cục.

Chi tiết định nghĩa và đơn vị đếm: [docs/02](02_DOMAIN_AND_CONSTRAINTS.md).

## 5. Fitness và bảng trọng số

### 5.1 Luôn ưu tiên H trước S

Nguồn: [evaluator.py, dòng 59–62](../src/timetable_ga/evaluator.py#L59).

~~~python
@property
def fitness(self) -> tuple[int, float]:
    """Native tuple comparison is the only ranking rule."""
    return self.hard_count, self.soft_penalty
~~~

Python so tuple từ trái sang phải. Vì dùng min, giá trị nhỏ hơn là tốt hơn. Ví dụ:

| Cá thể | Fitness | So sánh |
|---|---|---|
| A | (0, 10000) | Tốt hơn B vì không có lỗi cứng |
| B | (1, 0) | Xấu hơn mọi lịch H=0, dù S thấp |
| C | (0, 4) | Tốt hơn A vì H bằng nhau và 4 < 10000 |

Không cộng 1000×H+S để xếp hạng: công thức đó sẽ cho B=1000 thấp hơn A=10000,
trái yêu cầu ưu tiên tính hợp lệ. Dự án không dùng roulette selection và không cần
đổi fitness thành nghịch đảo. Quy tắc tuple áp dụng ở tournament, survivor và global best.
Ngữ nghĩa so sánh sequence: tài liệu Python [3] ở phần nguồn.

### 5.2 H được đếm như thế nào?

| Mã | Vi phạm | Đơn vị đếm |
|---|---|---|
| H0 | Thiếu, trùng, ID lạ hoặc placement không hợp lệ | Theo event và loại lỗi toàn vẹn |
| H1 | Trùng giảng viên | Mỗi cặp event trên mỗi tiết |
| H2 | Trùng nhóm sinh viên | Mỗi cặp event trên mỗi tiết |
| H3 | Trùng phòng | Mỗi cặp event trên mỗi tiết |
| H4 | Phòng thiếu sức chứa | Một lỗi/event |
| H5 | Sai loại phòng | Một lỗi/event |
| H6 | Giảng viên bận | Mỗi event và tiết bị cấm |
| H7 | Phòng đóng | Mỗi event và tiết bị cấm |
| H8 | Vượt ca/tuần hoặc thiếu tiết chiếm | Một lỗi/event |

Hai buổi cùng giáo viên chiếm tiết 1–2 và 2–3 thì H1=1 vì chỉ chồng tiết 2.
Nếu cùng phòng thì có thêm H3=1. Ba events cùng phòng tại một tiết tạo ba cặp
(A,B), (A,C), (B,C), nên H3=3. Code dùng combinations(..., 2), không chỉ đánh dấu
một ô bị trùng. Một event có thể vi phạm nhiều mã; H là tổng breakdown.

### 5.3 S được tính từ điểm gốc và trọng số

| Mã | Điểm gốc | Trọng số mặc định |
|---|---|---:|
| S1 | Số tiết event chiếm thuộc preference avoid của giảng viên | 3 |
| S3 | Số tiết event chiếm ở tiết 11 hoặc 12 | 1 |
| S4 | Tổng max(0, số buổi − số ngày khác nhau) theo assignment | 5 |

S = 3×S1_raw + 1×S3_raw + 5×S4_raw.

Ví dụ minh họa S1_raw=2, S3_raw=1, S4_raw=1 cho S=12. Một tiết có thể đồng thời
thuộc avoid và tiết muộn nên đóng góp vào cả S1 và S3. Unavailable là cấm cứng;
avoid chỉ là không mong muốn. S2/S5/S6 chưa được bật trong MVP; cấu hình yêu cầu
các mã đó sẽ bị từ chối. Bộ trọng số 3–1–5 là lựa chọn mô hình, chưa được chứng minh
tối ưu bằng khảo sát hoặc thí nghiệm độ nhạy.

## 6. Cấu hình và khởi tạo quần thể

Nguồn [GAConfig](../src/timetable_ga/ga.py#L23) kế thừa SearchConfig:

| Tham số | Mặc định | Giải thích đúng trong code |
|---|---:|---|
| seed | 42 | Trạng thái khởi tạo RNG cục bộ |
| max_evals | 2000 | Tổng số full evaluations, tính cả khởi tạo |
| population_size | 40 | Số cá thể quần thể và tối đa số con chấm mỗi thế hệ |
| generations | 50 | Số vòng tạo con sau quần thể khởi tạo |
| crossover_rate | 0.85 | Xác suất lai một cặp cha mẹ |
| mutation_rate | 0.10 | Xác suất xét đổi từng gene |
| elite_count | 2 | Số cha mẹ tốt nhất được giữ |
| tournament_size | 3 | Số cá thể tham gia mỗi lượt chọn |
| repair_enabled | False | Chưa triển khai sửa lịch |

Config kiểm tra kiểu, khoảng giá trị, elite_count < population_size và tournament_size
không vượt quần thể cấu hình. Population tối thiểu 2; budget tối thiểu 1; generations
có thể bằng 0 để chỉ chấm quần thể khởi tạo. Các xác suất phải hữu hạn và thuộc [0,1].

Trong optimize, rng = Random(config.seed) tạo bộ phát số giả ngẫu nhiên riêng, rồi
chấm min(population_size, budget.remaining) lịch khởi tạo. Nếu budget nhỏ hơn 40,
chỉ tạo đủ số cá thể có thể chấm; budget cạn ngay nên không vào tournament với
quần thể thiếu. Không đưa witness hoặc kết quả Greedy vào quần thể đầu.

Random(seed) là công cụ tái lập, không phải cơ chế làm lịch tốt hơn. Cùng dữ liệu,
cấu hình, thứ tự domain và môi trường sẽ tái tạo chromosome/fitness/history.
Runtime phụ thuộc tải máy nên không yêu cầu giống nhau. Python cho phép tạo Random
với trạng thái riêng; không nên suy rộng cam kết tái lập qua mọi phiên bản [2].

## 7. Tournament selection

Nguồn: [ga.py, dòng 55–57](../src/timetable_ga/ga.py#L55).

~~~python
def tournament(population: Sequence[Individual], size: int, rng: Random) -> Individual:
    """Sample without replacement, then compare lexicographic fitness."""
    return min(rng.sample(list(population), size), key=lambda item: item.evaluation.fitness)
~~~

1. rng.sample chọn size cá thể **không lặp chỉ số trong một tournament**.
2. min chọn cá thể có tuple fitness nhỏ nhất trong nhóm đó.
3. Hàm được gọi hai lần để lấy hai cha mẹ. Hai lần gọi độc lập nên cha mẹ có thể là
   cùng một cá thể. Các chromosome giống nhau cũng có thể tồn tại trong quần thể.

Ví dụ một tournament có fitness (2,0), (0,9), (0,4), người thắng là (0,4).
Không nhất thiết luôn chọn cá thể tốt nhất toàn quần thể; điều này để lại cơ hội
cho các cá thể khác tham gia. Size lớn làm lựa chọn thiên về cá thể tốt hơn;
size=1 tương đương lấy một cá thể ngẫu nhiên. Dự án dùng 3, chưa tuning để kết luận
đây là giá trị tốt nhất.

Cách nói khi chỉ code: “Em chọn ngẫu nhiên ba cá thể, so bằng cùng tuple H/S và lấy
nhỏ nhất. Em lặp lại để chọn cha và mẹ, thay vì dùng xác suất từ một fitness vô hướng.”

## 8. Uniform crossover

Nguồn: [ga.py, dòng 60–76](../src/timetable_ga/ga.py#L60).

~~~python
def uniform_crossover(
    first: Chromosome,
    second: Chromosome,
    rate: float,
    rng: Random,
) -> tuple[Chromosome, Chromosome]:
    if len(first) != len(second):
        raise ValueError("Parents must have equal chromosome lengths")
    if rng.random() >= rate:
        return first, second
    left, right = [], []
    for one, two in zip(first, second, strict=True):
        if rng.random() < 0.5:
            one, two = two, one
        left.append(one)
        right.append(two)
    return tuple(left), tuple(right)
~~~

Đọc theo thứ tự:

1. Hai cha mẹ phải cùng độ dài, vì cùng biểu diễn tập events.
2. Nếu số ngẫu nhiên >= rate, trả hai chromosome cha mẹ nguyên vẹn.
3. Nếu thực hiện lai, duyệt từng cặp gene cùng vị trí. Với xác suất 0,5, đổi hai gene.
4. Ghép các gene thành hai tuple con mới.

Hai tầng xác suất cần phân biệt: **0,85 quyết định có lai cặp**, **0,5 quyết định
đổi gene khi cặp đã được lai**. Không phải 85% events bị thay đổi. Kể cả có lai,
gene của con vẫn có thể giống cha mẹ nếu gene ban đầu bằng nhau hoặc không đổi.

Ví dụ minh họa, giả sử mọi domain đủ lớn:

~~~text
Cha A:       (0, 1, 2, 3)
Mẹ B:        (4, 5, 6, 7)
Đổi vị trí:   có không có không
Con 1:       (4, 1, 6, 3)
Con 2:       (0, 5, 2, 7)
~~~

Gene chỉ được đổi **cùng vị trí**, nên vẫn thuộc domain của cùng event. Code không
đổi gene E1 sang vị trí E2. Placement được giữ nguyên cả ngày/tiết/phòng, không
cắt rời ba thành phần. Tuy nhiên các gene ghép lại có thể tạo xung đột H1/H2/H3;
vì vậy phải chấm lại lịch con. Không có bảo đảm con tốt hơn cha mẹ.

## 9. Random-reset mutation và dòng code dễ bị hỏi

Nguồn: [ga.py, dòng 79–86](../src/timetable_ga/ga.py#L79).

~~~python
def mutate(chromosome: Chromosome, sizes: Sequence[int], rate: float, rng: Random) -> Chromosome:
    """Random reset to a different candidate whenever mutation fires and size > 1."""
    genes = list(chromosome)
    for index, (gene, size) in enumerate(zip(chromosome, sizes, strict=True)):
        if rng.random() < rate and size > 1:
            alternative = rng.randrange(size - 1)
            genes[index] = alternative + (alternative >= gene)
    return tuple(genes)
~~~

Hàm sao chép chromosome sang list, xét từng gene với mutation_rate rồi trả tuple.
Khi size > 1 và mutation xảy ra, nó **bắt buộc chọn candidate khác gene cũ**.
Nếu chỉ có một candidate thì giữ nguyên vì không có lựa chọn khác.

Dòng quan trọng là alternative + (alternative >= gene). Trong phép cộng này,
False tương đương 0 và True tương đương 1. Ví dụ size=5, gene cũ=2:

| alternative lấy từ range(4) | alternative >= 2 | Gene mới |
|---:|---|---:|
| 0 | False | 0 |
| 1 | False | 1 |
| 2 | True | 3 |
| 3 | True | 4 |

Như vậy tập {0,1,2,3} được ánh xạ một-một sang {0,1,3,4}, bỏ đúng gene cũ=2.
Không cần vòng lặp lấy lại đến khi khác, không thể vượt size−1. Các lựa chọn còn lại
được lấy đều vì mỗi alternative có đúng một ảnh.

Mutation mở cơ hội đến candidate chưa có ở cha mẹ. Nó giữ miền hợp lệ cục bộ,
nhưng cũng có thể làm lịch xấu đi. Với 24 gene, rate=0,10 và mọi domain >1,
số gene thay đổi kỳ vọng là 24×0,10=2,4 mỗi con; **không phải luôn đúng 2 hoặc 3**.
Nếu domain một phần tử, kỳ vọng số thay đổi thực tế giảm tương ứng.

Nếu crossover_rate=0, con vẫn có thể thay đổi vì mutation chạy sau crossover.
Nếu mutation_rate=0, GA chỉ kết hợp các gene có trong quần thể khởi tạo; nó không
tự tạo giá trị candidate mới ngoài những giá trị đã có ở vị trí đó.

## 10. Elitism và chọn quần thể kế tiếp

Nguồn: [ga.py, dòng 89–100](../src/timetable_ga/ga.py#L89).

~~~python
def elitist_survivors(
    parents: Sequence[Individual],
    children: Sequence[Individual],
    elite_count: int,
    size: int,
) -> list[Individual]:
    """Retain parent elites without additional calls, then best evaluated offspring."""
    elite = sorted(parents, key=lambda item: item.evaluation.fitness)[:elite_count]
    offspring = sorted(children, key=lambda item: item.evaluation.fitness)
    # A last budget-limited generation can contain fewer children than a population.
    pool = offspring + sorted(parents, key=lambda item: item.evaluation.fitness)[elite_count:]
    return elite + pool[: size - elite_count]
~~~

elite là các cha mẹ có fitness tốt nhất, được giữ nguyên cùng kết quả đã chấm.
offspring là các con đã đánh giá, sắp tăng theo tuple. Bình thường có 40 con,
nên quần thể mới gồm **2 parent elites + 38 con tốt nhất**.

Cần nói chính xác: code **chấm tối đa 40 con**, không chỉ chấm 38 con. Hai con
bị loại vẫn tiêu thụ budget. Nếu thế hệ cuối bị budget cắt ngắn, pool bổ sung
cha mẹ còn lại để quần thể không hụt. Không tính lại fitness của elites vì input
và chromosome của chúng không thay đổi.

Đây không phải cách trộn toàn bộ 40 cha mẹ + 40 con rồi chọn 40 tốt nhất: ngoài
2 elites, con được ưu tiên trước cha mẹ dự phòng. Quần thể vẫn có thể có các cá thể
xấu hơn trước. Khi elite_count >= 1, cá thể tốt nhất của quần thể được bảo tồn;
ngoài ra EvaluationBudget luôn giữ global best qua mọi lần chấm.

## 11. Vòng lặp optimize và điều kiện dừng

Đây là hàm nên mở đầu tiên khi thầy yêu cầu “chỉ code GA ở đâu”:

Nguồn: [ga.py, dòng 103–133](../src/timetable_ga/ga.py#L103).

~~~python
def optimize(
    problem: ProblemInstance,
    config: GAConfig | None = None,
    soft: EvaluationConfig | None = None,
) -> OptimizationResult:
    config = config or GAConfig()
    rng = Random(config.seed)
    budget = EvaluationBudget(problem, config, soft)
    population = [
        budget.score(random_chromosome(budget.sizes, rng), 0)
        for _ in range(min(config.population_size, budget.remaining))
    ]
    for generation in range(1, config.generations + 1):
        if not budget.remaining:
            break
        children = []
        while len(children) < config.population_size and budget.remaining:
            first = tournament(population, config.tournament_size, rng)
            second = tournament(population, config.tournament_size, rng)
            pair = uniform_crossover(
                first.chromosome, second.chromosome, config.crossover_rate, rng
            )
            for child in pair:
                if len(children) == config.population_size or not budget.remaining:
                    break
                child = mutate(child, budget.sizes, config.mutation_rate, rng)
                children.append(budget.score(child, generation))
        population = elitist_survivors(
            population, children, config.elite_count, config.population_size
        )
    return budget.finish("ga", "max_evals" if not budget.remaining else "generations")
~~~

Đọc hàm theo năm khối:

1. Lấy cấu hình, tạo RNG và budget; khởi tạo/chấm quần thể ở generation=0.
2. Duyệt generation=1 đến generations, dừng nếu budget hết.
3. Trong mỗi vòng, chọn hai cha mẹ, lai cặp, rồi đột biến và chấm từng con.
4. Khi đủ con hoặc cạn budget, dùng elitist_survivors tạo quần thể tiếp theo.
5. finish trả **best từng gặp**, không trả ngẫu nhiên một cá thể và cũng không
   bắt buộc là con cuối cùng vừa sinh.

Có kiểm tra budget trước vòng thế hệ, trong vòng tạo con và trước từng con trong
cặp. Nếu budget chỉ còn một lần chấm thì chỉ chấm một con, không vượt thêm một
lượt vì crossover tạo cặp hai con.

### Vì sao 40 cá thể × 50 thế hệ lại chỉ có 2.000 evaluations?

Nếu không bị budget giới hạn, tổng là 40 cá thể đầu + 50×40 con = **2.040**.
Budget=2.000 cắt sau 40 + 49×40 = 2.000 evaluations, nên với cấu hình mặc định
chỉ hoàn tất đến generation 49. Nếu chọn budget không chia hết theo kích thước
quần thể, có thể dừng giữa thế hệ.

Với generations=0 chỉ chấm khởi tạo. Với generations=2 và population=6, budget
đủ lớn sẽ có 6+2×6=18 evaluations; đây cũng là một trường hợp được test.
Không dừng chỉ vì H=0, vì S còn có thể cải thiện. Cũng chưa có dừng sớm theo
stagnation hoặc bằng chứng tối ưu.

## 12. EvaluationBudget bảo đảm so sánh công bằng ra sao?

Nguồn: [search.py, dòng 132–151](../src/timetable_ga/search.py#L132).

~~~python
def score(self, chromosome: Chromosome, generation: int) -> Individual:
    if not self.remaining:
        raise RuntimeError("Evaluation budget exhausted")
    schedule = decode(self.problem, chromosome)
    result = evaluator.evaluate(self.problem, schedule, self.soft)
    self.count += 1
    individual = Individual(chromosome, result)
    if self.best is None or result.fitness < self.best.evaluation.fitness:
        self.best = individual
    best = self.best.evaluation
    self.history.append(
        HistoryEntry(
            generation,
            self.count,
            best.hard_count,
            best.soft_penalty,
            best.soft_penalty if best.feasible else None,
        )
    )
    return individual
~~~

score là điểm gọi evaluator chung của cả ba solver:

- Kiểm tra còn budget trước khi chấm.
- decode chromosome thành lịch đầy đủ, gọi cùng evaluator.evaluate.
- Tăng count một lần cho một lời gọi đánh giá lịch đầy đủ.
- Cập nhật self.best khi tuple mới nhỏ hơn; nếu bằng nhau giữ best trước đó.
- Ghi history **sau mỗi evaluation**, dùng best-so-far, không phải fitness con hiện tại.

Nếu đánh giá lại chromosome trùng một lần trước, code vẫn gọi evaluator và vẫn
tính một lượt; không có bộ nhớ đệm cho mọi trial. Riêng elites và fitness hiện tại
của Greedy đã biết được tái sử dụng mà không phát sinh lời gọi.

History gồm generation, evaluation, best_hard, best_soft và best_soft_if_feasible.
Trước khi H=0, trường cuối là None; đồ thị S khả thi vì vậy không dùng điểm mềm
của lịch lỗi. Khi H giảm, S của tuple tốt hơn có thể tăng. Chỉ sau khi H đã bằng 0
thì đường best soft khả thi không tăng. H=0 mới xác nhận tính hợp lệ, không tự
chứng minh điểm mềm là tốt nhất toàn cục.

Cùng budget là cùng số lần chấm đầy đủ. GA còn có chi phí selection/crossover/
mutation/sort; baseline có cách sinh trial khác, nên không thể nói runtime phải
bằng nhau. Thời gian lưu trong metrics là thời gian solver, không gồm load/export/plot.

## 13. Ví dụ đi qua một thế hệ

Đây là ví dụ minh họa tự đặt, không phải log của sample. Giả sử population=4,
elite_count=1, mọi domain phù hợp, quần thể cha mẹ có fitness:

~~~text
A (1, 2, 0) -> (2, 3)
B (0, 1, 2) -> (0, 8)
C (2, 0, 1) -> (1, 1)
D (1, 1, 1) -> (0, 5)
~~~

1. Tournament trong {A,B,C} chọn B vì H=0; tournament trong {A,C,D} chọn D.
2. Uniform crossover ghép gene B và D theo một mặt nạ ngẫu nhiên.
3. Mutation có thể đổi một số gene sang candidate khác của đúng event.
4. Evaluator tính lại H/S; không suy ra điểm con bằng trung bình điểm cha mẹ.
5. Giả sử bốn con có fitness (0,4), (1,0), (0,6), (2,1), quần thể mới giữ
   elite D=(0,5) và ba con tốt nhất: (0,4), (0,6), (1,0).
6. Best-so-far cập nhật từ (0,5) thành (0,4). Con (2,1) bị loại nhưng vẫn đã
   dùng một evaluation.

Ví dụ cho thấy không cần mọi con đều tốt; lựa chọn và bộ nhớ best giữ kết quả
đã đạt được, còn mutation/crossover tiếp tục thử các tổ hợp khác.

## 14. Vì sao cần Random Search và Greedy?

Random Search lấy độc lập các chromosome ngẫu nhiên cho tới hết budget, giữ best.
Nó giúp xem GA có cải thiện so với chỉ thử ngẫu nhiên trong cùng số lần chấm hay không.

Greedy ở đây là **multi-start coordinate sweep**. Mỗi restart bắt đầu bằng một
lịch đầy đủ ngẫu nhiên; ưu tiên event có domain nhỏ, rồi event có nhiều liên hệ
teacher/group. Nó thử các candidate của event hiện tại trong bối cảnh các gene khác
giữ nguyên, chọn tốt nhất rồi chuyển sang event kế tiếp. Xong một sweep thì restart.
Mọi trial đều là lịch đầy đủ và gọi chung evaluate, không có bộ chấm lịch thiếu event.

Kết quả đã lưu cho seeds 11,22,33, mỗi run 2.000 evaluations:

| Phương pháp | Số run H=0 | Median S trên runs H=0 | Diễn giải |
|---|---:|---:|---|
| GA | 3/3 | 0 | Tìm được lịch hợp lệ trong cả ba seed |
| Greedy | 3/3 | 8 | Điểm mềm cao hơn GA ở sample này |
| Random Search | 3/3 | 11 | Cả ba run đều khả thi |

Nguồn: [summary.csv](../results/benchmark_12periods/summary.csv) và
[raw_runs.csv](../results/benchmark_12periods/raw_runs.csv). Không lấy trung bình S của cả
lịch chưa hợp lệ để so chất lượng lịch sử dụng được. Chỉ có n=3, chưa kiểm định
thống kê, chưa khảo sát khả năng mở rộng. Số đo 12 tiết ngày 13/11/2026 thay cho bộ 8 tiết trong phần trình bày hiện tại;
miền lựa chọn và S3 khác nhau nên không trộn hai bộ kết quả.

## 15. Kiểm thử nào bảo vệ các điểm quan trọng?

Nguồn [test_solvers.py](../tests/test_solvers.py),
[test_evaluator.py](../tests/test_evaluator.py),
[test_candidates.py](../tests/test_candidates.py), [test_ui.py](../tests/test_ui.py).

| Điều cần bảo đảm | Kiểm thử tiêu biểu |
|---|---|
| Mọi solver dùng đúng full evaluator, không vượt budget | test_shared_full_evaluator_exact_budget_and_returned_fitness |
| Cùng seed/config/data tái lập kết quả | test_reproducible_seed_chromosome_fitness_history |
| Crossover giữ đúng domain theo event | test_crossover_whole_event_genes_and_different_domains |
| Mutation đổi gene và xử lý singleton | test_mutation_different_candidate_and_singleton |
| Tournament và elite ưu tiên H trước S | test_tournament_and_elite_lexicographic |
| Số evaluations gồm cả khởi tạo | test_ga_generation_limit_and_initial_only |
| Trả trạng thái trung thực khi H>0 | test_jointly_infeasible_returns_honest_status |
| Domain rỗng không gọi evaluator | test_empty_domain_preflight_no_evaluations |
| Không làm thay đổi RNG toàn cục | test_random_sampling_and_seed_do_not_use_global_rng |

Fixture witness chỉ xác nhận evaluator chấm được một lịch biết trước. Nó không
chứng minh GA tự tìm được lịch đó; vì vậy báo cáo tách số liệu witness và solver.

## 16. Chi phí tính toán nên giải thích thế nào?

Gọi N là số events, P là kích thước quần thể, G là số thế hệ và B là budget.
Số full evaluations tối đa của GA là min(B, P×(G+1)). Mỗi lần đánh giá còn phải
decode N gene và kiểm tra mọi tiết chiếm. Duration tối đa 4 trong mô hình.

Crossover và mutation đi qua N gene nên có chi phí tuyến tính theo N. Chọn survivors
sort cha mẹ/con khoảng O(P log P). Tournament trong bản code này còn tạo list từ
population trước rng.sample, nên không nên nói toàn hàm chỉ O(k) với k=tournament_size.

Evaluator xây occupancy theo tài nguyên/ngày/tiết và duyệt các cặp xung đột.
Trong trường hợp nhiều events cùng tranh một tài nguyên ở một tiết, số cặp có thể
tăng bậc hai theo N. Vì vậy không mô tả toàn bộ solver đơn giản là O(G×P×N) trong
mọi trường hợp. Cách trả lời thực tế: chi phí chính phụ thuộc số evaluations và
chi phí evaluator trên kích thước/mức xung đột của dataset.

Đây là phân tích từ vòng lặp trong source, không phải số đo scaling. Dự án mới đo
sample 24 events, chưa có benchmark medium/large.

## 17. Kịch bản mở code trong 8 phút

| Thời gian | Mở phần nào | Ý chính cần nói |
|---|---|---|
| 0–1 phút | domain và một dòng CSV | Assignment sinh events; placement chiếm đủ duration |
| 1–2 phút | search.random_chromosome và decode | Gene là candidate index theo event, không phải số tiết |
| 2–3 phút | evaluator.fitness và bảng weights | Tuple H/S, H0–H8, mềm 3–1–5 |
| 3–4 phút | ga.tournament và uniform_crossover | Tournament 3; xác suất cặp 0.85 khác xác suất gene 0.5 |
| 4–5 phút | ga.mutate | Giải thích phép dịch để loại gene cũ bằng bảng size=5 |
| 5–6 phút | elitist_survivors và optimize | Chấm 40 con, giữ 2 elites + 38 con, không chấm lại elites |
| 6–7 phút | EvaluationBudget.score | Budget bao gồm khởi tạo, global best, history mỗi evaluation |
| 7–8 phút | UI và summary.csv | Seed42 H=0/S=0; GA median S=0, Greedy S=8, Random S=11; giới hạn n=3 |

Nếu nhóm chia hai người: người thứ nhất phụ trách dữ liệu, chromosome và evaluator;
người thứ hai phụ trách operators, vòng lặp, budget và thực nghiệm. Cả hai cần hiểu
tuple H/S, mutation và giới hạn kết quả để trả lời chéo.

## Câu hỏi thầy có thể hỏi

**1. Tại sao chọn GA?** Vì bài toán là tổ hợp nhiều quyết định có ràng buộc; nhóm có
thể biểu diễn lịch thành chromosome và chấm chất lượng độc lập. GA cho phép tìm kiếm
trong ngân sách hữu hạn. Đây là lựa chọn để nghiên cứu/triển khai, chưa có chứng cứ
GA là lựa chọn tốt nhất cho mọi dữ liệu thời khóa biểu.

**2. Một cá thể có phải một buổi học không?** Không. Một cá thể là một lịch đầy đủ;
một gene tương ứng một buổi học. Quần thể 40 nghĩa là 40 lịch ứng viên, mỗi lịch 24 gene.

**3. Tại sao crossover không dùng PMX/OX như bài toán người bán hàng?** Chromosome
này là dãy chỉ số theo các domain riêng, không phải hoán vị. Gene có thể cùng giá trị
số mà vẫn chỉ placement khác nhau. Uniform theo cùng vị trí phù hợp cách mã hóa này.

**4. Con có chắc hợp lệ không?** Gene giữ local domain, nhưng cả lịch vẫn có thể
xung đột giữa events. Phải evaluate lịch con, không xem crossover là bước sửa lịch.

**5. Mutation có thể chọn lại gene cũ không?** Khi nhánh mutation được thực hiện và
domain >1 thì không; phép dịch chỉ số loại gene cũ. Domain=1 giữ nguyên.

**6. Hai cha mẹ có thể giống nhau không?** Có, hai tournament độc lập; quần thể cũng
có thể chứa chromosome trùng. Mutation vẫn có thể tạo thay đổi sau đó.

**7. Có cần tính lại fitness của elites không?** Không trong mô hình tĩnh này vì
chromosome và problem không đổi. Cần tính lại các con được tạo, kể cả con trùng trước đó
vì code hiện tại không cache mọi trial.

**8. Nếu tất cả cá thể còn lỗi cứng thì sao?** Chọn H nhỏ nhất rồi mới S. Hết budget
vẫn H>0 thì trả best_found_infeasible và UI ghi Lịch chưa hợp lệ; không gán thành công giả.

**9. H=0 có nghĩa tối ưu chưa?** Chỉ có nghĩa thỏa các hard constraints đã mô hình hóa.
S vẫn có thể giảm. GA là tìm kiếm hữu hạn, chưa có chứng minh tối ưu toàn cục.

**10. Sao không dừng ở H=0?** Vì mục tiêu thứ hai là giảm S. Code tiếp tục cho tới
hết budget hoặc giới hạn thế hệ, không có dừng sớm tại lịch hợp lệ đầu tiên.

**11. GA có luôn thắng Greedy không?** Không. Bộ 12 tiết hiện tại cho GA median S=0,
Greedy=8 và Random=11. Bộ 8 tiết lịch sử từng cho Greedy tốt hơn. Thay đổi miền lịch
và S3 làm bài toán khác đi; ba seed chưa đủ kết luận tổng quát.

**12. Dùng 40 cá thể và 50 thế hệ có được tuning không?** Đây là cấu hình đã chọn
cho sprint. Chưa tìm siêu tham số tối ưu, không tune lại theo ba benchmark seeds rồi
trình bày chúng như một đánh giá độc lập.

**13. Seed làm gì?** Khởi tạo RNG để tái lập quá trình lấy mẫu trong cùng môi trường.
Seed khác có thể cho lịch khác; cùng seed không đồng nghĩa runtime giống nhau.

**14. Vì sao không dùng tổng phạt lớn cho hard?** Tuple biểu đạt trực tiếp ưu tiên
cứng. Tổng hữu hạn có thể đảo thứ tự khi S đủ lớn; ví dụ (0,10000) và (1,0).

**15. Dữ liệu có phải của trường không?** Không, là 24 events giả lập. Có schema và
fixture để kiểm thử nhưng chưa có dữ liệu vận hành được xác nhận từ trường.

**16. Nếu thầy hỏi phần chưa làm?** Repair, nhiều datasets/seeds, tuning rộng,
S2/S5/S6, upload và database. Hướng tiếp theo là mở rộng kiểm chứng trước khi tuyên bố
hiệu quả trên dữ liệu thực; không nói các mục này đã có trong code.

## Nguồn tham khảo

Mọi mô tả chi tiết của thuật toán, ràng buộc, budget và tests ở trên lấy trực tiếp
từ mã nguồn trong repository, với các liên kết file/hàm ở từng mục. Kết quả lấy từ
artifacts đã chạy; ví dụ tự đặt không được trộn vào benchmark.

1. Sean Luke, *Essentials of Metaheuristics*, second edition, Lulu, 2013, chương 3
   về phương pháp quần thể và GA. [Trang chính thức của tác giả](https://people.cs.gmu.edu/~sean/book/metaheuristics/),
   [PDF](https://people.cs.gmu.edu/~sean/book/metaheuristics/Essentials.pdf).
   Dùng để tham khảo các khái niệm GA; cấu hình và hiện thực cụ thể là của project.
2. Python Software Foundation, *random — Generate pseudo-random numbers*, Python 3.12:
   [Random, sample, randrange và reproducibility](https://docs.python.org/3.12/library/random.html).
3. Python Software Foundation, *Data Structures*, mục 5.8:
   [Comparing Sequences and Other Types](https://docs.python.org/3.12/tutorial/datastructures.html#comparing-sequences-and-other-types).
4. Nội bộ: [mô hình ràng buộc](02_DOMAIN_AND_CONSTRAINTS.md),
   [schema](03_DATASET_AND_SCHEMA.md), [spec](../specs/001-timetable-mvp/spec.md),
   [GA](../src/timetable_ga/ga.py), [budget](../src/timetable_ga/search.py),
   [evaluator](../src/timetable_ga/evaluator.py), [tests](../tests/test_solvers.py).
5. Thực nghiệm 12 tiết ngày 13/11/2026: [raw runs](../results/benchmark_12periods/raw_runs.csv),
   [summary](../results/benchmark_12periods/summary.csv), [metadata](../results/benchmark_12periods/metadata.json)
   và history/metrics/schedule của từng run. Chứng cứ mới: [12periods](../checkpoints/12periods/).

Nguồn trực tuyến được đối chiếu ngày 12/11/2026. Bản 13/11 cập nhật miền lịch,
loader, evaluator và UI; các toán tử GA giữ nguyên. Số dòng ứng với source hiện tại.
