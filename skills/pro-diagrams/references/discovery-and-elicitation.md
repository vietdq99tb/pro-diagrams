# Khai Thác Thông Tin & Đặt Câu Hỏi Thông Minh Trước Khi Vẽ (`Discovery & Elicitation`)

Mục tiêu của bước khai thác thông tin là giúp Agent **vẽ đúng bản chất nghiệp vụ, đúng chuẩn ký hiệu và đúng loại biểu đồ ngay từ lượt đầu**, thay vì đoán mò số liệu hoặc vẽ lại nhiều lần — đồng thời **không gây phiền hà** khi người dùng đã cung cấp đủ dữ kiện.

---

## 1. Phân Loại Mức Độ Đủ Dữ Kiện (`Readiness Triage`)

Trước khi viết JSON spec hay sinh tệp, đánh giá nhanh yêu cầu của người dùng thuộc mức nào dưới đây:

| Trạng thái đầu vào | Dấu hiệu nhận biết | Hành động bắt buộc |
|---|---|---|
| **Mức 1 — Đủ dữ kiện để vẽ ngay** *(Bỏ qua bước hỏi)* | Người dùng đã cung cấp cụ thể: (a) các bước + nhánh rẽ `Decision` (Flowchart/Swimlane); (b) danh sách việc + tiền nhiệm + thời lượng (CPM/DAG); (c) bảng số liệu thật + đơn vị (Biểu đồ); (d) công thức + miền vẽ (Hàm số); **HOẶC** yêu cầu rõ *"vẽ mẫu / tự đề xuất quy trình chuẩn"*. | **Vẽ ngay không hỏi thừa.** Nếu còn chi tiết nhỏ mang tính trình bày (hướng `TB`/`LR`, nền sáng/tối), chọn mặc định tốt nhất (`tech-warm-light`, `Open Sans`) và ghi chú ngắn các giả định ở cuối câu trả lời. |
| **Mức 2 — Thiếu dữ kiện cốt lõi hoặc mơ hồ** *(Hỏi 1 vòng gọn)* | Yêu cầu chỉ nêu ý định chung chung (ví dụ: *"vẽ quy trình mua hàng giúp tôi"*, *"vẽ biểu đồ doanh thu"*, *"trực quan hóa kế hoạch dự án"*) khiến Agent sẽ phải tự bịa bước duyệt, số liệu thật, hoặc chọn sai loại biểu đồ. | **Hỏi đúng 1 vòng duy nhất gồm 2–5 câu hỏi có đòn bẩy cao nhất.** Gắn rõ lựa chọn `(Khuyến nghị)` / mặc định để người dùng có thể trả lời nhanh trong 5 giây hoặc xác nhận *"dùng mặc định"*. |
| **Mức 3 — Có tệp/ngữ cảnh đi kèm** *(Đọc trước, hỏi phần khuyết)* | Người dùng đính kèm mã nguồn, CSV/JSON, tài liệu SOP, hay file `.drawio` cũ. | **Đọc và trích xuất tối đa dữ kiện từ tệp trước.** Tuyệt đối không hỏi lại thông tin đã có trong tệp; chỉ hỏi ngắn nếu thiếu ngữ cảnh bên ngoài (ví dụ: hạng mục muốn nhấn màu tiêu điểm, đối tượng đọc slide). |

### Ba Nguyên Tắc Vàng Khi Hỏi
1. **Không bao giờ tự bịa số liệu hoặc luật nghiệp vụ thật:** Không đoán doanh thu, chi phí, hạn mức duyệt tiền, thời gian SLA hay hệ số hàm số khi người dùng cần tài liệu thực tế. Nếu chưa có số thật, hãy xin số liệu hoặc hỏi xác nhận dùng bộ số mẫu có gắn nhãn rõ *"Dữ liệu minh họa"*.
2. **Gom tất cả câu hỏi vào đúng 1 lượt (Single-Round Batching):** Tránh hỏi lắt nhắt từng câu qua nhiều lượt chat. Nếu host có công cụ hỏi trắc nghiệm tương tác (`ask_question`), ưu tiên dùng cho các lựa chọn có phương án rõ ràng; nếu không, trình bày danh sách đánh số 1–5 ngắn gọn kèm `(Khuyến nghị)`.
3. **Giải thích ngắn *vì sao cần biết* khi câu hỏi ảnh hưởng trực tiếp tới hình học:** Ví dụ: *"Biết bước nào là thao tác thủ công vs hệ thống giúp chọn đúng hình thang / hình chữ nhật chuẩn ISO 5807"*.

---

## 2. Bảng Tư Vấn Chọn Loại Sơ Đồ / Biểu Đồ Hợp Lý

Khi người dùng mới nêu mục tiêu (*"tôi muốn trình bày..."*) mà chưa chọn dạng biểu đồ, chủ động đề xuất dạng khớp nhất với câu chuyện dữ liệu:

| Mục tiêu truyền đạt của người dùng | Loại đề xuất (`pro-diagrams` Track) | Lý do nên chọn |
|---|---|---|
| Chuỗi bước xử lý, thuật toán, kiểm tra lỗi, vòng lặp thử lại (1 chủ thể chính) | **`iso5807-flowchart`** (`.drawio` + `.svg`) | Rõ ràng ngữ nghĩa từng bước theo chuẩn quốc tế ISO 5807:1985 và kéo-thả chỉnh sửa được. |
| Quy trình liên phòng ban, phân định trách nhiệm, phê duyệt đa cấp | **`swimlane-sop`** (`.drawio` + `.svg` + tùy chọn `_runbook.html`) | Nhìn rõ ai làm bước nào, bàn giao chứng từ ở đâu và hỗ trợ tra cứu SOP bấm-chọn từng bước. |
| Tiến độ công việc phụ thuộc lẫn nhau, cần tìm đường găng & độ dự trữ | **`cpm`** (có thời lượng) / **`topological-graph`** (DAG/cây/trạng thái) | Tự tính chính xác `ES/EF/LS/LF/TF` và tô nhấn đường găng bằng sắc Hỏa `#AD4333`. |
| So sánh vài nhóm dữ liệu có tên ngắn (theo quý, chi nhánh, sản phẩm) | **`bar`** / **`grouped_bar`** (`chart_builder.py`) | Mắt người so sánh độ dài cột theo cùng đường gốc 0 chính xác nhất. |
| Xếp hạng Top-N, nhãn danh mục tiếng Việt dài, hoặc có cả giá trị âm & dương | **`horizontal_bar`** (`chart_builder.py`) | Nhãn tiếng Việt đọc ngang tự nhiên không bị nghiêng chữ, hỗ trợ trục gốc 0 phân kỳ. |
| Theo dõi biến động liên tục theo thời gian (tháng, quý, năm) | **`line`** (`chart_builder.py`) | Làm rõ độ dốc xu hướng và điểm giao cắt giữa các chuỗi. |
| Giải thích cầu nối *Đầu kỳ → Các yếu tố tăng/giảm → Cuối kỳ* (chi phí, lợi nhuận) | **`waterfall`** (`chart_builder.py`) | Nhìn tức thì yếu tố nào kéo tăng hay giảm kết quả cuối cùng, kiểm định bảo toàn tổng `data-*`. |
| Phân bổ ngân sách, dòng tiền, luồng chuyển đổi nhiều tầng bảo toàn tổng | **`sankey`** (`chart_builder.py`) | Độ dày dòng chảy phản ánh trung thực tỷ trọng từ nguồn sang đích. |
| Khảo sát biến thiên, cực trị, tiệm cận, tiếp tuyến, diện tích tích phân | **`math-plot`** (`plot_math_svg.py`) | Đường cong toán học chính xác theo biểu thức, xử lý mượt điểm gián đoạn. |

---

## 3. Bộ Câu Hỏi Khai Thác Chuyên Sâu Theo Từng Nhánh

Chỉ chọn lọc **2–5 câu còn khuyết** phù hợp với nhánh mục tiêu — không chép nguyên toàn bộ danh sách để hỏi người dùng.

### 3.1 Lưu đồ Quy trình / Thuật toán ISO 5807 (`iso5807-flowchart`)
1. **Điểm Đầu & Điểm Cuối (`Terminator`):** Quy trình bắt đầu từ sự kiện/tín hiệu nào và có những trạng thái kết thúc nào (Hoàn tất thành công / Từ chối / Hủy lỗi)?
2. **Điểm Rẽ nhánh & Xử lý Ngoại lệ (`Decision` / `Delay` / Loop):** Tại các bước kiểm tra, điều kiện rẽ nhánh cụ thể là gì? Khi kết quả là **Không đạt / Lỗi**, luồng sẽ dừng, rẽ sang nhánh xử lý riêng, hay thử lại (tối đa mấy lần, có thời gian chờ `Delay` không)?
3. **Phân loại Ký hiệu ISO 5807:** Bước nào do con người nhập liệu/thao tác tay (`manual_input`, `manual_operation`), bước nào gọi hệ thống/quy trình con có sẵn (`predefined_process`), bước nào đọc/ghi cơ sở dữ liệu (`database`) hoặc xuất biểu mẫu/hóa đơn (`document`)?
4. **Bố cục & Ngữ cảnh sử dụng:** Sơ đồ dùng cho tài liệu đọc dọc A4 (`TB` trên→dưới, khuyến nghị cho SOP) hay slide trình chiếu ngang (`LR` trái→phải), giao diện sáng hay tối?

### 3.2 Quy trình Liên phòng ban & SOP (`swimlane-sop`)
1. **Danh sách Phòng ban / Vai trò (`lanes`):** Có chính xác những bộ phận hoặc hệ thống nào tham gia (theo đúng thứ tự trách nhiệm)?
2. **Ngưỡng Phê duyệt & Chứng từ Bàn giao:** Có mốc phân cấp thẩm quyền nào không (ví dụ theo hạn mức ngân sách, cấp rủi ro, SLA thời gian), và chứng từ nào được chuyển tay giữa các bộ phận?
3. **Ngoại lệ & Vòng phản hồi:** Khi một phòng ban trả hồ sơ / nghiệm thu không đạt, hồ sơ quay về bước nào của phòng ban nào?
4. **Đầu ra Mở rộng:** Ngoài `.drawio` và `.svg`, bạn có cần xuất thêm **trang SOP Runbook tương tác từng bước (`_runbook.html`)** hoặc **bản dịch song ngữ Việt ↔ Anh (`relabel.py`)** không?

### 3.3 Đồ thị Cấu trúc & Đường găng Dự án (`topological-graph` / `cpm`)
1. **Đỉnh & Quan hệ Phụ thuộc:** Danh sách các hạng mục/module và mối quan hệ tiền nhiệm (*việc nào phải xong trước việc nào*)?
2. **Thời lượng & Đơn vị (cho CPM):** Thời lượng dự kiến của từng công việc (đơn vị: ngày / tuần / giờ) để tự động tính `ES, EF, LS, LF, TF` và tô nổi đường găng?
3. **Điểm cần làm nổi bật:** Có nhóm thành phần, mốc bàn giao hoặc nút rủi ro đơn lẻ (SPOF) nào cần đánh dấu màu nhấn riêng không?

### 3.4 Biểu đồ Số liệu & Báo cáo KPI (`quantitative-chart`)
1. **Thông điệp chính (Key Takeaway):** Bạn muốn người xem kết luận điều gì ngay khi nhìn vào biểu đồ (nhóm dẫn đầu, xu hướng cải thiện, nguyên nhân đội chi phí, hay tỷ trọng phân bổ)?
2. **Dữ liệu Thật & Đơn vị tính:** Bộ số liệu chính xác (hoặc tệp CSV/JSON), đơn vị hiển thị (`tỷ VNĐ`, `triệu đồng`, `%`), khoảng thời gian và dòng ghi nguồn?
3. **Điểm nhấn Thị giác & KPI Strip:** Hạng mục/chuỗi nào là tiêu điểm cần nhấn bằng sắc **Kiln Terracotta (`#AD4333`)**? Có muốn thêm 2–3 thẻ KPI tóm tắt (giá trị tổng, `% YoY`, chênh lệch mục tiêu) phía trên biểu đồ không?
4. **Kênh xuất bản:** Chèn vào PowerPoint/Word nền sáng (`tech-warm-light`, khuyến nghị) hay dashboard/slide nền tối (`tech-warm-dark`)?

### 3.5 Đồ thị Hàm số Toán học (`math-plot`)
1. **Biểu thức Hàm số:** Công thức chính xác $y = f(x)$ (và hàm so sánh / tiếp tuyến nếu có)?
2. **Miền hiển thị:** Khoảng trục hoành `[x_min, x_max]` và trục tung `[y_min, y_max]` cần tập trung khảo sát?
3. **Chi tiết giải tích cần nhấn mạnh:** Có cần vẽ đường tiệm cận (đứng/ngang/xiên), gắn nhãn tọa độ cực trị/điểm uốn/giao điểm, hay tô miền diện tích tích phân trên đoạn `[a, b]` không?

---

## 4. Ví Dụ Mẫu Thực Hành

### Ví dụ A — Yêu cầu mơ hồ → Hỏi 1 vòng gọn (NÊN LÀM)
- **Người dùng:** *"Vẽ giúp mình biểu đồ so sánh chi phí vận hành năm 2026 so với 2025 để đưa vào slide báo cáo."*
- **Phản hồi khai thác mẫu của Agent:**
  > Để biểu đồ đúng thông điệp báo cáo và khớp số liệu thật, bạn chốt nhanh giúp mình 3 ý (hoặc trả lời *"dùng mặc định"* để mình dựng bản nháp trước):
  > 1. **Số liệu & Đơn vị:** Bạn cung cấp các con số chi phí 2025–2026 (theo từng khoản mục tăng/giảm hoặc theo từng quý) và đơn vị (`triệu đồng` / `tỷ VNĐ`) nhé?
  > 2. **Kiểu biểu đồ phù hợp:**
  >    - *(Khuyến nghị nếu giải trình nguyên nhân tăng/giảm)* **Biểu đồ thác nước (Waterfall):** 2025 → các yếu tố tăng/giảm → 2026.
  >    - **Biểu đồ cột ghép (`grouped_bar`):** So sánh trực tiếp 2025 vs 2026 theo từng quý/phòng ban.
  > 3. **Điểm nhấn & Giao diện:** Khoản mục nào cần tô màu nhấn tiêu điểm (`#AD4333`), và slide của bạn dùng nền sáng *(khuyến nghị)* hay nền tối?

### Ví dụ B — Yêu cầu đã đầy đủ chi tiết → Vẽ ngay (KHÔNG HỎI THỪA)
- **Người dùng:** *"Vẽ lưu đồ ISO 5807 cho quy trình đăng nhập: Bắt đầu → Nhập email/mật khẩu → Gọi dịch vụ xác thực → Hợp lệ? Nếu Có: ghi log vào CSDL, hiển thị Dashboard → Kết thúc. Nếu Không: tăng số lần sai, kiểm tra >= 5 lần? Nếu Có thì khóa tài khoản 15 phút rồi Kết thúc; nếu Không thì quay lại bước Nhập email/mật khẩu."*
- **Hành động của Agent:** Đã đủ 100% nút, nhánh `Decision`, vòng lặp, ký hiệu (`terminator`, `manual_input`, `predefined_process`, `decision`, `database`, `display`, `delay`). **Không hỏi thêm** — tiến hành biên dịch `.drawio` + `.svg` + `.html` và kiểm định `validate_iso5807.py --strict --score` ngay lập tức.
