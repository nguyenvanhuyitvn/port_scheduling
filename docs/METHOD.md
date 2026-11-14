# Đặc tả mô hình và phương pháp

## 1. Nguồn và phạm vi

Tài liệu nền: Zhou, Y., Cheng, X., Cao, Y. (2026), *Integrated Continuous Berth Allocation and Time-Invariant Specific Quay Crane Assignment: A Mixed-Integer Model and a Greedy Genetic Algorithm*, bản PDF đã dùng trong báo cáo. DOI bản preprint: https://doi.org/10.21203/rs.3.rs-9235581/v1.

Mã này do người thực hiện cài đặt độc lập theo cách diễn giải của báo cáo. Không có mã nguồn tác giả để đối chiếu từng chi tiết. GGA là thuật toán di truyền có thành phần tham lam, không phải Iterated Greedy.

Giả định: ETA biết trước, bến liên tục, cẩu đồng nhất và cùng đường ray, tập cẩu một tàu cố định và liên tiếp; không có preemption. Không mô tả riêng di chuyển cẩu, setup, mớn nước, bãi hoặc suy giảm năng suất do tương tác cẩu. Cần phân biệt bảo đảm thứ tự cẩu trong các khoảng phục vụ đồng thời với mô phỏng toàn bộ chuyển động vật lý.

## 2. MIP được cài đặt

Mục tiêu `Z = sum(end_i - eta_i)`. Biến gồm thời điểm bắt đầu/kết thúc/thời lượng, vị trí bến, chỉ số cẩu đầu/cuối, nhị phân phân công `y_ij`, thời gian hiệu dụng `h_ij`, và bốn nhị phân L/R/B/A cho mỗi cặp i<k.

Các nhóm ràng buộc trong `mip.build()`:

1. `start_i >= eta_i`, `0 <= position_i <= L-length_i`, `end=start+duration`.
2. `q_min <= sum(y) <= q_max`.
3. `QE*sum(h) >= workload`, cùng ba điều kiện tuyến tính hóa để `h=duration` nếu y=1 và h=0 nếu y=0.
4. `last-first+1=sum(y)`; cẩu được chọn phải nằm trong đoạn chỉ số, do đó đoạn không có lỗ.
5. `L+R+B+A >= 1` và bốn bất đẳng thức Big-M tương ứng: trái, phải, trước hoặc sau.
6. `y_ij+y_kj <= 1+B+A`: dùng chung cẩu chỉ được phép khi một thứ tự thời gian được kích hoạt.
7. Hai bất đẳng thức giữ thứ tự đoạn cẩu theo thứ tự tàu khi thời gian chồng lấn; được nới lỏng khi đã tách thời gian.

Cận: tạo lịch tuần tự khả thi với q_min, tính Zbar. Đặt `sum(end) <= Zbar+sum(eta)`. Vì flow time không âm, mỗi `end_i <= eta_i+Zbar`; chọn U=max(eta)+Zbar. Sử dụng Mt=H=U, Ms=L, Mq=số cẩu. Cận này giữ lại ít nhất một nghiệm tối ưu của mô hình xác định đã nêu.

Mô hình gốc trong tài liệu có nhóm (5)–(8) gây vấn đề về kích hoạt. Tùy chọn `printed_core` thay điều kiện phân tách bằng `L+R=1` và `B+A=1`, tương đương đặt `R=1-L`, `A=1-B`. Nó tái hiện **lõi logic (5)–(8)** để kiểm chứng hai ví dụ; các ràng buộc còn lại vẫn thuộc cách cài đặt của gói, không phải toàn bộ bản in của tác giả. Không dùng `printed_core` làm mô hình hiệu năng chính.

Backend HiGHS và Gurobi nhận cùng danh sách biến, hệ số, cận và hàng ràng buộc. Gurobi không được tự động thay bằng HiGHS khi xảy ra lỗi.

Solver tối thiểu hóa sum(end), không cộng hằng -sum(eta) vào vector c. Khi xuất, mã trừ hằng này khỏi objective và dual bound. `solver_relative_gap_on_sum_completion` là gap của solver trên sum(end); `flow_relative_gap` được tính lại trên Z và bound tương ứng. Không nhầm hai đại lượng khi ETA lớn.

Lịch MIP còn được kiểm tra bằng validator và residual/integrality của ma trận. Thời gian gồm cả dựng mô hình; ngân sách optimize được giảm theo phần thời gian đã tiêu thụ. Giới hạn solver có thể bị vượt nhẹ do hoàn tất xử lý; `wall_seconds` ghi thời gian thực đo. SciPy không có tùy chọn `threads` công khai trong lệnh milp ở đây; `--threads` chỉ áp dụng cho Gurobi. Không khẳng định hai backend có cùng cấu hình luồng.

## 3. Bộ kiểm tra độc lập

`validation.validate()` không dùng biến thứ tự của MIP và không gọi decoder. Nó kiểm tra đủ ID, biên bến, ETA, thời lượng dương, đủ năng lực làm hàng, số cẩu, tính liên tiếp, cẩu trùng và thứ tự khi các khoảng thời gian giao nhau. Các khoảng chỉ tiếp giáp được chấp nhận theo dung sai 1e-6.

Tập cẩu được lưu một lần cho mỗi tàu trong suốt khoảng làm hàng; định dạng này tự giới hạn ở time-invariant assignment. Không dùng validator này để xác nhận lịch phân công cẩu thay đổi theo thời gian.

## 4. Gene và decoder

Mỗi tàu có năm gene chuẩn hóa về [0,1]:

1. khóa ưu tiên xử lý (random key);
2. thời điểm bắt đầu mong muốn trên miền từ ETA đến U;
3. vị trí mong muốn trên [0,L-length];
4. số cẩu, làm tròn về [q_min,q_max];
5. cẩu đầu, làm tròn về [1,m-q+1]. Cẩu cuối suy ra bằng first+q-1.

Đây là lựa chọn triển khai; không phải ảnh chụp chính xác nhiễm sắc thể của tài liệu. Khóa ưu tiên là gene phụ phục vụ decoder sửa nghiệm; nó không thay đổi lịch tuyệt đối khi đánh giá GA không Repair.

**GA**: thời gian/vị trí/khối cẩu được giải mã trực tiếp. Gene nguyên được làm tròn và miền chuẩn hóa được giới hạn; lịch vi phạm liên-tàu không được sửa, nhận fitness nhỏ. Quần thể ban đầu là các lịch tuần tự khả thi ngẫu nhiên, không phải các lịch ngẫu nhiên tùy ý thường vô nghiệm. Giữ một lịch tuần tự q_min làm incumbent chung cho GA và GGA.

**GGA**: gene được giải mã theo khóa ưu tiên; q được làm tròn và **giữ cố định trong lượt bố trí tàu**, không tự giảm q để đổi lấy bắt đầu sớm. Cẩu đầu và vị trí là ưu tiên mềm. Các mốc thời gian được thử theo thứ tự ETA rồi các thời điểm hoàn thành tàu đã bố trí. Ở mỗi mốc, xét tàu giao nhau với toàn khoảng phục vụ; vị trí ứng viên gồm hai biên bến, vị trí mong muốn và các biên trái/phải của tàu đang giao nhau. Các vị trí ứng viên đều là số thực, không dùng lưới mét cố định.

Với q cố định và lịch đã chèn cố định, khả năng bố trí thay đổi theo biên tàu; thêm các biên này cho phép tìm một vị trí khả thi nếu tồn tại cho tập tàu giao nhau đang xét. Khả năng bắt đầu mới do giải phóng tài nguyên xuất hiện ở mốc hoàn thành. Tuy nhiên, đây vẫn là xây dựng tuần tự theo thứ tự đã chọn, không bảo đảm lịch toàn cục tối ưu.

Trong một thời điểm khả thi, ưu tiên vị trí gần gene mong muốn, rồi vị trí nhỏ; khối cẩu gần gene mong muốn, rồi chỉ số nhỏ. Quy tắc này giúp giữ thông tin sau Crossover. Nó **khác** quy tắc phá hòa hoàn toàn theo vị trí nhỏ nhất đã dự kiến trong báo cáo. Gene thời gian mong muốn không làm trì hoãn lựa chọn earliest-feasible của GGA. Vì q đã được chọn trước, mã không tối ưu qua mọi giá trị q tại từng thời điểm; khi viết báo cáo cần mô tả đúng điều này.

Sau sửa, gene vật lý được cập nhật theo lịch mới, còn khóa ưu tiên giữ lại (Lamarckian repair). GGA đưa lịch Greedy xác định theo ETA và q_max vào quần thể ban đầu, bên cạnh incumbent tuần tự chung; phần còn lại dùng gene ngẫu nhiên và decoder tham lam. Elitism cùng lưu incumbent bảo toàn chất lượng của lịch Greedy đã tìm được. Những chi tiết này phải được ghi như quyết định của bản cài đặt.

## 5. Toán tử và đối chứng

Roulette selection theo 1/(Z+epsilon), Arithmetic Crossover với một alpha cho một cặp, Mutation mỗi gene với xác suất pm, bước beta giảm theo tiến trình. Các gene được clip về [0,1]. Elitism giữ hai cá thể theo fitness; có thêm lưu incumbent tốt nhất.

Ở chế độ `--generations`, bước giảm theo số thế hệ; ở chế độ `--seconds`, bước giảm theo tỷ lệ wall time đã sử dụng. Cách thứ hai là biến thể thực thi so với công thức theo thế hệ của tài liệu. Cùng seed và số thế hệ cho kết quả xác định trên cùng môi trường; cùng seed và thời gian không bảo đảm cùng kết quả vì số đánh giá phụ thuộc tốc độ máy.

GA và GGA khác cả khởi tạo lẫn cơ chế xử lý khả thi và vai trò decoder. So sánh riêng hai phương pháp là so sánh **hai cấu hình đầy đủ**. Để tách đóng góp, gói có thêm hai biến thể ablation; cả bốn dùng chung chọn lọc, lai ghép, đột biến, elitism, incumbent tuần tự và ngân sách:

| Thuật toán | Khởi tạo | Decoder |
|---|---|---|
| `ga` | lịch tuần tự khả thi ngẫu nhiên | trực tiếp, không Repair |
| `ga_greedy` | như GGA: lịch Greedy theo ETA + khóa ngẫu nhiên giải mã tham lam | trực tiếp, không Repair |
| `ga_repair` | như GA | Repair (decoder tham lam) |
| `gga` | như GGA | Repair |

Với `ga_greedy`, việc xây dựng tham lam chỉ chạy một lần lúc khởi tạo; lịch thu được được ghi ngược vào gene vật lý để decoder trực tiếp tái tạo đúng lịch đó. Con cháu sau Crossover/Mutation không được sửa. Khóa ưu tiên vẫn chỉ có tác dụng khi có Repair. Cấu hình được ghi trong `parameters.initialization` và `parameters.decoder` của run.json. Kết quả ablation đã chạy xem `EXECUTION_STATUS.md`.

`greedy` là baseline không tiến hóa: xử lý theo ETA, ưu tiên q_max, giải mã một lịch rồi so với incumbent tuần tự chung; không phải nghiệm tối ưu.

## 6. Dữ liệu

12 tàu được chép từ Bảng 1 tài liệu; ETA gốc được giữ ở CSV và metadata JSON. Quy ước ngày:giờ:phút cho ETA là giả định chưa được xác nhận bằng mã nguồn tác giả. Chiều dài công bố được dùng làm chiều dài hiệu dụng, không cộng thêm safety margin chưa biết.

Dữ liệu tổng hợp của gói dùng đúng tỷ lệ 40/40/20 cho n là bội của 5; chiều dài và khối lượng lấy mẫu đều rời rạc trong khoảng của Bảng 3. ETA độc lập đều trên [0,horizon], làm tròn 0,001 giờ. Đây là dữ liệu tự sinh, không phải các instance gốc. Hướng dẫn dùng seed 2026 và horizon 48 giờ.

## 7. Tài liệu API

- SciPy milp: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
- Gurobi Python Model: https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html
- Gurobi parameters: https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html

Số liệu trong `results_verified` thuộc môi trường tạo gói. Không gộp thời gian của chúng với thời gian chạy trên máy cá nhân để tính trung bình.
