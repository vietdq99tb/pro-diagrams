# Chuẩn Sơ Đồ Xử Lý Thông Tin ISO 5807:1985 (§4–§11) & Quy Trình Kiểm Định

Tài liệu này quy định cách chọn đúng loại sơ đồ theo **ISO 5807:1985 (§4–§8)**, khai báo đầy đủ **26 ký hiệu nút + 4 loại đường nối (§9 & §11)**, và kiểm định tự động tách bạch giữa **tuân thủ ISO 5807** với **cảnh báo bố cục / tương phản WCAG AA**.

---

## 1. Chọn Đúng 5 Loại Sơ Đồ Chuẩn ISO 5807:1985 (§4–§8)

Trước khi viết JSON và kiểm định, xác định đúng trường `"kind"` tương ứng mục tiêu sơ đồ (trình biên dịch ghi thuộc tính `isoDiagramType` vào `<mxGraphModel>` để `validate_iso5807.py` tự động áp dụng đúng bộ quy tắc theo loại sơ đồ):

| `"kind"` trong JSON | Loại sơ đồ & Điều khoản ISO 5807:1985 | Ví dụ Phụ lục chuẩn | Quy tắc kiểm định đầu vào / đầu ra đặc trưng |
|---|---|---|---|
| `data-flowchart` | **Data Flowchart** (Lưu đồ dữ liệu, `§4`) | Phụ lục **A** | Chấp nhận ký hiệu **dữ liệu / chứng từ** (`document`, `multi_document`, `data`, lưu trữ...) ở điểm bắt đầu và kết thúc (không bắt buộc `Terminator`). Cho phép bước `manual_operation` lưu hồ sơ cuối nhánh; cấm bước `process` tự động bị cụt. |
| `program-flowchart` *(hoặc `iso5807-flowchart`)* | **Program Flowchart** (Lưu đồ chương trình / thuật toán, `§5`) | Phụ lục **B(a), B(b)** | Yêu cầu `Terminator` Bắt đầu & Kết thúc (hoặc nối tiếp qua trang bằng `Connector` §10.2.2), kiểm tra chặt `Decision` 1 lối vào + nhãn nhánh, ghép cặp `Loop Limit` theo mã `loop_id`. |
| `system-flowchart` | **System Flowchart** (Lưu đồ hệ thống, `§6`) | Phụ lục **C** | **Phân biệt luồng điều khiển và luồng dữ liệu/vật mang**: `manual_input`, `direct_data`, `display`, `document` (hóa đơn/màn hình) ở đầu vào hoặc đầu ra của bước xử lý không bị báo nhầm là nút cô lập (`W-ISO-ORPHAN`) hay nhánh cụt (`E-ISO-END`). Hỗ trợ đường 2 chiều đọc/ghi (`bidirectional: true`). |
| `program-network` | **Program Network Chart** (Mạng chương trình, `§7`) | Phụ lục **D** | Không bắt buộc `Terminator`; yêu cầu đơn vị chương trình kết nối không cô lập, hỗ trợ đường **Chuyển điều khiển (`role: "control_transfer"`)** mang tam giác mã `P`, `T`, `I` (`§9.3.2.1`), `Connector` ghép cặp (`Z`) và đường 2 chiều. |
| `system-resources` | **System Resources Chart** (Sơ đồ tài nguyên hệ thống, `§8`) | Phụ lục **E** | Không bắt buộc `Terminator`; yêu cầu có cả đơn vị xử lý và đơn vị dữ liệu/lưu trữ kết nối nhau (`E-ISO-RESOURCES`), hỗ trợ đường 2 chiều đọc/ghi (`bidirectional: true`) và cụm tài liệu chồng lớp có nhãn riêng (`§10.3.2`). |
| `swimlane` | **Swimlane ISO 5807 cho SOP liên phòng ban** | SOP vận hành | Áp dụng bộ quy tắc lưu đồ chuẩn ISO 5807 kết hợp kiểm tra làn (`lanes`), tự động chuẩn hóa khoảng trắng thừa quanh `id` làn và cấm đường nối chạy đè vạch làn (`W-ISO-SWIMLANE-CROSS`). |

---

## 2. Danh Mục 26 Ký Hiệu Nút (`data/iso5807-shapes.json`) & Phân Loại Theo §11

Khi dùng `scripts/iso5807_builder.py`, khai báo `"type"` theo đúng bảng sau (trình biên dịch sẽ **từ chối và báo lỗi rõ trường sai** nếu gõ sai `type`, trỏ cạnh tới ID không tồn tại, hoặc trùng/sai ID làn):

| `type` trong JSON | Tên & Điều khoản ISO 5807:1985 | Nhóm (§11) | Loại sơ đồ phù hợp (§4–§8) | Khi nào sử dụng |
|---|---|---|---|---|
| `data` | Data (`§9.1.1.1`) | Dữ liệu | A, B, C, D, E | Nhập/xuất dữ liệu tổng quát không phụ thuộc môi trường vật lý (hình bình hành). |
| `stored_data` | Stored Data (`§9.1.1.2`) | Dữ liệu | A, C, D, E | Kho tệp tin / dữ liệu lưu trữ chung (hình cong lồi–lõm). |
| `internal_storage` | Internal Storage (`§9.1.2.1`) | Dữ liệu | A, C, D, E | Biến / cấu trúc dữ liệu trong bộ nhớ RAM. |
| `sequential_data` | Sequential Access Storage (`§9.1.2.2`) | Dữ liệu | A, C, D, E | Tệp tuần tự, băng từ, event log chỉ ghi nối tiếp. |
| `database` | Direct Access Storage / DB (`§9.1.2.3`) | Dữ liệu | A, C, D, E | Cơ sở dữ liệu / đĩa từ truy cập trực tiếp (hình trụ đứng). |
| `direct_data` | Direct Access Storage (`§9.1.2.3`) | Dữ liệu | A, C, D, E | Bộ nhớ truy cập trực tiếp (hình trụ ngang: đĩa từ, cache, SSD). |
| `document` | Document (`§9.1.2.4`) | Dữ liệu | A, C, D, E | Một chứng từ, biểu mẫu, biên bản, báo cáo, hóa đơn. |
| `multi_document` | Multi-Document (`§9.1.2.4` & `§10.3.2`) | Dữ liệu | A, C, D, E | Cụm nhiều chứng từ xếp lớp. Hỗ trợ mảng `"items": ["Chứng từ 1", "Chứng từ 2"]` để gắn nhãn riêng cho từng lớp theo `§10.3.2`. |
| `manual_input` | Manual Input (`§9.1.2.5`) | Dữ liệu | A, C, D, E | Người dùng nhập liệu qua bàn phím, biểu mẫu, máy quét. |
| `card` | Card (`§9.1.2.6`) | Dữ liệu | A, C, D, E | Dữ liệu mang trên thẻ đục lỗ, thẻ từ, thẻ thông minh hoặc thẻ vật lý. |
| `paper_tape` *(alias `punched_tape`)* | Punched / Paper Tape (`§9.1.2.7`) | Dữ liệu | A, C, D, E | Dữ liệu lưu trên băng giấy đục lỗ / băng ghi vật lý (đỉnh & đáy lượn sóng). |
| `display` | Display (`§9.1.2.8`) | Dữ liệu | A, C, D, E | Hiển thị thông tin, kết quả tra cứu, cảnh báo lên màn hình. |
| `process` | Process (`§9.2.1`) | Xử lý | A, B, C, D, E | Bước xử lý, tính toán, chương trình hoặc thao tác nghiệp vụ cụ thể. |
| `predefined_process` | Predefined Process (`§9.2.2.1`) | Xử lý | B, C, D | Gọi quy trình con / module / hàm đã định nghĩa riêng. |
| `manual_operation` | Manual Operation (`§9.2.2.2`) | Xử lý | A, C, E | Thao tác thủ công của con người (kiểm đếm, ký tay, lưu hồ sơ). |
| `preparation` | Preparation (`§9.2.2.3`) | Xử lý | B, C | Khởi tạo biến, thiết lập tham số hoặc chuẩn bị môi trường. |
| `decision` | Decision (`§9.2.2.4` & `§10.3.1`) | Xử lý | B, C | Kiểm tra rẽ nhánh: **duy nhất 1 lối vào (`in=1`)**, **≥ 2 lối ra**, 100% nhánh có nhãn. Hỗ trợ rẽ nhiều nhánh (ví dụ 5 nhánh) qua thân chung `"branch_style": "stem"` (tự bật khi `> 3` nhánh tiến theo `§10.3.1(b)`). |
| `parallel_mode` | Parallel Mode (`§9.2.2.5`) | Xử lý | B, C | Hai vạch ngang song song đánh dấu tách (`fork`) hoặc đồng bộ gom (`join`). |
| `loop_limit_start` / `loop_limit_end` | Loop Limit (`§9.2.2.6`) | Xử lý | B | Mở và đóng khối lặp. Khai báo `"loop_id": "L"` (hoặc đặt mã ở dòng đầu nút mở và dòng đầu/cuối nút đóng); validator kiểm tra khớp từng mã riêng kể cả vòng lồng nhau. |
| `on_page_connector` | Connector (`§9.4.1` & `§10.2.2`) | Đặc biệt | A, B, C, D, E | Nút tròn nhỏ ghép cặp theo mã (`A` → `A` cùng trang hoặc `λ1` xuyên trang kèm `"ref_page": "3.2"` và chú thích `"Đến trang 3.2"` / `"Từ trang 1.4"`). |
| `terminator` | Terminator (`§9.4.2`) | Đặc biệt | A, B, C | Điểm **Bắt đầu** (`in=0, out>=1`) và **Kết thúc** (`in>=1, out=0`) dạng viên thuốc. |
| `annotation` | Annotation (`§9.4.3`) | Đặc biệt | A, B, C, D, E | Chú thích mở ngoặc `[` + dây đứt không mũi tên gắn qua `"attach_to"`. |
| `ellipsis` | Ellipsis (`§9.4.4`) | Đặc biệt | A, B, C, D, E | Ba dấu chấm `• • •` biểu thị bỏ lược các ký hiệu lặp lại không cần vẽ chi tiết. |
| `delay` | **Delay *(Ký hiệu mở rộng ngoài ISO 5807:1985)*** | Mở rộng ANSI/ASME | SOP thực hành | Khoảng chờ bắt buộc (timeout, SLA duyệt, batch đêm). **Lưu ý:** trường `"duration"` trên nút SOP chỉ dùng tính đường găng CPM khi `kind: "cpm"` hoặc `"compute_cpm": true`. |
| `off_page_connector` | **Off-Page Connector *(Ký hiệu mở rộng ANSI X3.5 ngoài ISO 5807:1985)*** | Mở rộng ANSI X3.5 | SOP thực hành | Ngũ giác chuyển trang (ISO 5807:1985 gốc dùng `on_page_connector` hình tròn kèm tham chiếu trang theo `§9.4.1 & §10.2.2`). |

---

## 3. Danh Mục 4 Loại Đường Nối Chuẩn ISO 5807:1985 (§9.3)

| Thuộc tính cạnh trong JSON | Điều khoản ISO 5807:1985 | Biểu diễn `.drawio` & `.svg` | Ứng dụng điển hình |
|---|---|---|---|
| *(mặc định)* `arrows: "end"` | Flowline (`§9.3.1`) | Đường liền 1 đầu mũi tên (`endArrow=block`) | Luồng điều khiển và luồng dữ liệu một chiều. |
| `bidirectional: true` *(hoặc `arrows: "both"`)* | Bidirectional Flowline (`§9.3.1` & `§10.2.1`) | Một đường duy nhất có **2 đầu mũi tên** (`startArrow=block;endArrow=block;`) | Quan hệ đọc/ghi tệp trực tiếp trong Lưu đồ hệ thống (**C**), Mạng chương trình (**D**) và Tài nguyên hệ thống (**E**). |
| `role: "control_transfer"`, `label: "P" \| "T" \| "I"` | Control Transfer (`§9.3.2.1`) | Đường liền mang **tam giác định hướng chứa mã `P`, `T`, `I`** (`isoLine=control_transfer`) | Kích hoạt / chuyển điều khiển chương trình trong Phụ lục **D** (`program-network`). |
| `role: "communication_link"` | Communication Link (`§9.3.2.2`) | Đường gấp khúc tia chớp (`isoLine=communication_link`) | Truyền dữ liệu qua kênh viễn thông / mạng. |
| `role: "alternative"` *(hoặc `dashed: true`)* | Alternative / Dashed Path (`§9.3.2.3`) | Đường nét đứt (`dashed=1`) | Nhánh lựa chọn phụ hoặc mối liên hệ không thường trực. |

### Cấu trúc Sơ Đồ Nhiều Trang (`"pages": [...]`) Với Connector Xuyên Trang (§10.2.2)

```json
{
  "kind": "program-flowchart",
  "pages": [
    {
      "page_name": "1.4",
      "title": "Trang 1.4",
      "nodes": [
        { "id": "start", "type": "terminator", "label": "Bắt đầu" },
        { "id": "p1", "type": "process", "label": "Xử lý bước 1" },
        { "id": "c_out", "type": "on_page_connector", "label": "λ1", "ref_page": "3.2" },
        { "id": "n1", "type": "annotation", "attach_to": "c_out", "label": "Đến trang 3.2" }
      ],
      "edges": [
        { "from": "start", "to": "p1" },
        { "from": "p1", "to": "c_out" }
      ]
    },
    {
      "page_name": "3.2",
      "title": "Trang 3.2",
      "nodes": [
        { "id": "c_in", "type": "on_page_connector", "label": "λ1", "ref_page": "1.4" },
        { "id": "p2", "type": "process", "label": "Xử lý bước 2" },
        { "id": "finish", "type": "terminator", "label": "Kết thúc" },
        { "id": "n2", "type": "annotation", "attach_to": "c_in", "label": "Từ trang 1.4" }
      ],
      "edges": [
        { "from": "c_in", "to": "p2" },
        { "from": "p2", "to": "finish" }
      ]
    }
  ]
}
```

---

## 4. Quy Trình Biên Dịch, Kiểm Định & Tách Bạch Kết Quả (`validate_iso5807.py`)

```bash
# 1. Biên dịch từ JSON -> .drawio + .svg + .html tương tác
python3 <skill-dir>/scripts/iso5807_builder.py spec.json \
  -o output.drawio \
  --render-svg output.svg \
  --render-html output.html

# 2. Kiểm định toàn diện (tự đọc isoDiagramType trong XML, hoặc ép kiểu bằng --diagram-type)
python3 <skill-dir>/scripts/validate_iso5807.py output.drawio --strict --score

# 3. Kiểm định thuần ISO 5807 (tách riêng khỏi cảnh báo bố cục / tương phản)
python3 <skill-dir>/scripts/validate_iso5807.py output.drawio --diagram-type system-flowchart --strict --iso-only --json
```

### Bảng Quy Tắc Kiểm Định & Phân Nhóm (`category`)

| Mã chẩn đoán | Mức độ | Nhóm (`category`) | Chuẩn / Điều khoản | Ý nghĩa kiểm tra |
|---|---|---|---|---|
| `E-ISO-EMPTY` | Error | `iso` | `ISO 5807:1985 §4–§8` | Từ chối tệp/trang `.drawio` rỗng hoặc chỉ có khung tiêu đề mà không có ký hiệu sơ đồ nào. |
| `E-ISO-START` | Error | `iso` | `ISO 5807:1985 §4 / §5 / §9.4.2` | Kiểm tra điểm bắt đầu phù hợp loại sơ đồ (`Terminator` ở `§5`, dữ liệu/chứng từ ở `§4`, đơn vị xử lý ở `§7`). |
| `E-ISO-END` | Error | `iso` | `ISO 5807:1985 §4 / §5 / §9.4.2` | Kiểm tra điểm kết thúc phù hợp loại sơ đồ và cấm bước xử lý điều khiển bị cụt (`out=0`). |
| `E-ISO-DECISION-ENTRY` | Error | `iso` | `ISO 5807:1985 §9.2.2.4` | Mỗi `Decision` chỉ được có **duy nhất 1 lối vào (`in=1`)**. |
| `E-ISO-DECISION-LABEL` | Error | `iso` | `ISO 5807:1985 §9.2.2.4 / §10.3.1` | 100% nhánh ra khỏi `Decision` phải có nhãn điều kiện rõ ràng. |
| `E-ISO-LOOP-PAIR` | Error | `iso` | `ISO 5807:1985 §9.2.2.6` | Kiểm tra khớp từng cặp mở–đóng `Loop Limit` theo đúng mã `loop_id` / dòng mã (cặp `L`–`M` bị từ chối dù cân bằng số lượng). |
| `E-ISO-CONNECTOR-PAIR` | Error | `iso` | `ISO 5807:1985 §9.4.1 / §10.2.2` | Ghép cặp `Connector` theo mã, vai trò vào/ra và tham chiếu trang xuyên toàn bộ các trang `<diagram>`; báo rõ mã và trang thiếu đầu nối. |
| `E-ISO-RESOURCES` | Error | `iso` | `ISO 5807:1985 §8` | Sơ đồ `system-resources` phải có cả đơn vị xử lý và đơn vị dữ liệu/lưu trữ. |
| `W-DECISION-EXIT` | Warning | `iso` | `ISO 5807:1985 §9.2.2.4 / §10.3.1` | `Decision` có `< 2` nhánh ra. |
| `W-ISO-STYLE-STRICT` | Warning | `iso` | `ISO 5807:1985 §9.4.2 / §10.1.2` | Cấm dùng `ellipse` tròn thay cho stadium `terminator`. |
| `W-ISO-ORPHAN` | Warning | `iso` | `ISO 5807:1985 §9.3.1 / §10.2.1` | Nút cô lập hoàn toàn hoặc không đi tới được theo ngữ nghĩa từng loại sơ đồ. |
| `W-ISO-CONTROL-TRANSFER` | Warning | `iso` | `ISO 5807:1985 §9.3.2.1` | Cạnh `control_transfer` thiếu mã loại chuyển điều khiển (`P`, `T`, `I`...). |
| `I-LAYOUT-DECISION-FANOUT` | **Info (Gợi ý)** | `layout` | `ISO 5807:1985 §10.3.1` | Gợi ý bố cục khi `Decision` có `> 3` nhánh (hợp lệ hoàn toàn theo ISO 5807, **không bao giờ đánh trượt `iso_compliant` hay `--strict`**). |
| `W-ISO-FLOW-DIR` | Warning | `layout` | `ISO 5807:1985 §10.2.1.1` | Nhánh quay lui một chiều thiếu waypoint hành lang biên ngoài. |
| `W-ISO-SWIMLANE-CROSS` | Warning | `layout` | `Pro. Diagrams Swimlane Layout` | Cạnh nối chạy đè dọc lên vạch phân cách làn Swimlane. |
| `W-ISO-WCAG-CONTRAST` | Warning | `contrast` | `WCAG 2.1 AA (SC 1.4.3)` | Tương phản chữ/nền trong nút `< 4.5:1` (tách biệt với `iso_compliant`). |

Báo cáo `--json` xuất riêng `iso_compliant`, `layout_clean`, `contrast_clean`, `passed`, `summary`, và `supportedFixes[]` để vòng tự sửa (`<= 2` vòng) xác định chính xác cần sửa chuẩn ISO hay chỉ chỉnh bố cục/màu sắc.
