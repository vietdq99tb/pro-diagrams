# Chuẩn Lưu Đồ Quy Trình ISO 5807:1985 & Quy Trình Kiểm Định

Tài liệu này quy định cách xây dựng, kết xuất và kiểm định lưu đồ thuật toán / quy trình nghiệp vụ tuân thủ nghiêm ngặt **ISO 5807:1985**.

---

## 1. Danh Mục Ký Hiệu Chuẩn ISO 5807:1985 (`data/iso5807-shapes.json`)

Khi dùng `scripts/iso5807_builder.py`, khai báo trường `"type"` của từng nút theo đúng bảng sau (trình biên dịch sẽ **từ chối và báo lỗi ngay** nếu gõ sai tên `type`, trỏ cạnh tới ID không tồn tại, hoặc gán sai ID làn Swimlane):

| `type` trong JSON | Tên & Điều khoản ISO 5807:1985 | Ký hiệu hình học | Khi nào sử dụng |
|---|---|---|---|
| `terminator` | Terminator (`§9.4.2`) | Viên thuốc / Stadium | Điểm **Bắt đầu** (`in=0, out>=1`) và **Kết thúc** (`in>=1, out=0`). |
| `process` | Process (`§9.2.1`) | Hình chữ nhật vuông góc | Bước xử lý, tính toán, nghiệp vụ cụ thể. |
| `decision` | Decision (`§9.2.2.4` & `§10.3.1`) | Hình thoi (`diamond`) | Kiểm tra điều kiện rẽ nhánh: **duy nhất 1 lối vào (`in=1`)** và **≥ 2 lối ra**, 100% nhánh phải có nhãn điều kiện. |
| `data` | Data (`§9.1.1.1`) | Hình bình hành | Nhập dữ liệu đầu vào hoặc xuất kết quả đầu ra không phụ thuộc môi trường vật lý. |
| `predefined_process` | Predefined Process (`§9.2.2.1`) | Chữ nhật có 2 vạch dọc | Gọi quy trình con / module / hàm đã định nghĩa riêng. |
| `document` | Document (`§9.1.2.4`) | Chữ nhật đáy lượn sóng | Tạo/xuất một biểu mẫu, biên bản, báo cáo, hóa đơn. |
| `multi_document` | Multi-Document (`§9.1.2.4` & `§10.3.2`) | Tập tài liệu xếp lớp | Bộ hồ sơ gồm nhiều chứng từ đi kèm nhau (biểu diễn lặp lại `§10.3.2`). |
| `database` | Direct Access Storage / DB (`§9.1.2.3`) | Hình trụ đứng | Đọc/ghi cơ sở dữ liệu hoặc đĩa từ truy cập trực tiếp. |
| `direct_data` | Direct Access Storage (`§9.1.2.3`) | Hình trụ ngang | Bộ nhớ truy cập trực tiếp (cache, key-value, SSD store). |
| `stored_data` | Stored Data (`§9.1.1.2`) | Hình cong lồi–lõm | Kho tệp tin / dữ liệu lưu trữ chung. |
| `sequential_data` | Sequential Access Storage (`§9.1.2.2`) | Hình tròn có đuôi ngang | Ghi log tuần tự, băng từ, hàng đợi sự kiện nối tiếp. |
| `internal_storage` | Internal Storage (`§9.1.2.1`) | Chữ nhật kẻ ô góc trái | Cấu trúc dữ liệu / biến trong RAM. |
| `preparation` | Preparation (`§9.2.2.3`) | Hình lục giác dẹt | Khởi tạo biến, thiết lập tham số hoặc bộ đếm vòng lặp. |
| `manual_operation` | Manual Operation (`§9.2.2.2`) | Hình thang cân đáy nhỏ dưới | Thao tác thủ công của con người (kiểm hàng, ký tay). |
| `manual_input` | Manual Input (`§9.1.2.5`) | Tứ giác cạnh trên vát nghiêng | Người dùng nhập liệu qua bàn phím / form / máy quét. |
| `on_page_connector` | Connector (`§9.4.1` & `§10.2.2`) | Hình tròn nhỏ (44×44) | Điểm nối cùng trang tránh cắt dây — **bắt buộc đi theo cặp cùng mã** (`A` vào → `A` ra). |
| `off_page_connector` | Off-Page Connector *(mở rộng ANSI X3.5)* | Ngũ giác mũi nhọn dưới | Chuyển luồng sang trang khác (ghi rõ mã & số trang; ISO 5807 gốc dùng hình tròn `§9.4.1` kèm mô tả trang `§10.2.2`). |
| `loop_limit_start` / `loop_limit_end` | Loop Limit (`§9.2.2.6`) | Lục giác vát 2 góc trên / dưới | Mở và đóng khối lặp (phải cân bằng số lượng mở/đóng). |
| `delay` | Delay *(mở rộng ANSI / ASME)* | Hình chữ D | Chờ phê duyệt, timeout, chờ batch định kỳ (ký hiệu mở rộng ngoài ISO 5807:1985). |
| `display` | Display (`§9.1.2.8`) | Đầu nhọn trái, cong phải | Hiển thị thông báo/cảnh báo lên màn hình. |
| `parallel_mode` | Parallel Mode (`§9.2.2.5`) | Cặp hai vạch ngang song song | Tách (fork) hoặc đồng bộ gom (join) các nhánh chạy song song. |
| `annotation` | Annotation (`§9.4.3`) | Ngoặc vuông mở `[` + dây đứt | Ghi chú giải thích gắn vào một nút qua trường `"attach_to"`. |

---

## 2. Mẫu JSON Spec Cho `scripts/iso5807_builder.py`

```json
{
  "kind": "iso5807-flowchart",
  "direction": "TB",
  "preset": "tech-warm-light",
  "title": "Quy trình Kiểm tra & Xử lý Đơn hàng (ISO 5807:1985)",
  "subtitle": "SOP-ORD-01 · Phiên bản 2.0",
  "nodes": [
    { "id": "start", "type": "terminator", "label": "Bắt đầu" },
    { "id": "in_order", "type": "data", "label": "Nhận dữ liệu đơn hàng" },
    { "id": "prep", "type": "preparation", "label": "Khởi tạo bộ đếm thử lại k = 0" },
    { "id": "sub_verify", "type": "predefined_process", "label": "Gọi dịch vụ xác thực tồn kho & hạn mức" },
    { "id": "dec_valid", "type": "decision", "label": "Đơn hàng hợp lệ?" },
    { "id": "db_save", "type": "database", "label": "Ghi nhận đơn vào CSDL ERP" },
    { "id": "doc_inv", "type": "document", "label": "Xuất phiếu xuất kho & hóa đơn" },
    { "id": "conn_a_in", "type": "on_page_connector", "label": "A" },
    { "id": "conn_a_out", "type": "on_page_connector", "label": "A" },
    { "id": "end", "type": "terminator", "label": "Kết thúc" },
    { "id": "note1", "type": "annotation", "attach_to": "sub_verify", "label": "SLA phản hồi <= 2 giây;\nkiểm tra đồng thời 2 kho" }
  ],
  "edges": [
    { "from": "start", "to": "in_order" },
    { "from": "in_order", "to": "prep" },
    { "from": "prep", "to": "sub_verify" },
    { "from": "sub_verify", "to": "dec_valid" },
    { "from": "dec_valid", "to": "db_save", "label": "Có" },
    { "from": "dec_valid", "to": "conn_a_in", "label": "Không", "role": "error" },
    { "from": "db_save", "to": "doc_inv" },
    { "from": "doc_inv", "to": "end" },
    { "from": "conn_a_out", "to": "end" }
  ]
}
```

---

## 3. Quy Trình Biên Dịch, Dàn Cổng, Kiểm Định & Xuất Bản (Tối Đa 2 Vòng Tự Sửa)

Chạy tuần tự các lệnh sau:

```bash
# 1. Biên dịch từ JSON sang .drawio chuẩn + xuất ngay bản xem trước SVG & HTML tương tác
python3 <skill-dir>/scripts/iso5807_builder.py spec.json \
  -o output.drawio \
  --render-svg output.svg \
  --render-html output.html

# 2. Kiểm định cấu trúc + 12 quy tắc ngữ nghĩa ISO 5807:1985, Swimlane & WCAG AA
python3 <skill-dir>/scripts/validate_iso5807.py output.drawio --strict --score
```

### Bảng 12 Quy Tắc Kiểm Định (`validate_iso5807.py`) & Điều Khoản Ánh Xạ

| Mã chẩn đoán | Mức độ | Chuẩn / Điều khoản | Ý nghĩa kiểm tra |
|---|---|---|---|
| `E-ISO-START` | Error | `ISO 5807:1985 §9.4.2` | Phải có ít nhất 1 `Terminator` bắt đầu (`in=0, out>=1`). |
| `E-ISO-END` | Error | `ISO 5807:1985 §9.4.2` | Phải có `Terminator` kết thúc và không có nút xử lý cụt (`out=0`). |
| `E-ISO-DECISION-ENTRY` | Error | `ISO 5807:1985 §9.2.2.4` | Mỗi hình thoi `Decision` chỉ được có **duy nhất 1 lối vào** (nếu cần gom nhiều luồng, gom ở bước xử lý hoặc `Connector` trước khi vào hình thoi). |
| `E-ISO-DECISION-LABEL` | Error | `ISO 5807:1985 §9.2.2.4 / §10.3.1` | 100% nhánh ra khỏi `Decision` phải có nhãn điều kiện rõ ràng. |
| `E-ISO-CONNECTOR-PAIR` | Error | `ISO 5807:1985 §9.4.1 / §10.2.2` | Mỗi mã `On-Page Connector` phải đủ cặp vào (`in>0, out=0`) và đúng 1 nút ra (`in=0, out>0`); `Off-Page Connector` không được để trống nhãn. |
| `W-DECISION-EXIT` / `W-ISO-DECISION-EXIT` | Warning | `ISO 5807:1985 §9.2.2.4 / §10.3.1` | `Decision` phải có `2–3` lối ra (`<2` hoặc `>3` đều bị cảnh báo). |
| `W-ISO-STYLE-STRICT` | Warning | `ISO 5807:1985 §9.4.2 / §10.1.2` | Cấm dùng `ellipse` tròn thay cho stadium `terminator`. |
| `W-ISO-LOOP-PAIR` | Warning | `ISO 5807:1985 §9.2.2.6` | Số lượng `loop_limit_start` phải khớp `loop_limit_end`. |
| `W-ISO-ORPHAN` | Warning | `ISO 5807:1985 §9.3.1 / §10.2.1` | Không có nút cô lập hoặc không đi tới được từ điểm `Start`. |
| `W-ISO-FLOW-DIR` | Warning | `ISO 5807:1985 §10.2.1.1 / §10.2.1.2` | Nhánh quay lui ngược chiều chính phải có waypoint hành lang biên ngoài. |
| `W-ISO-SWIMLANE-CROSS` | Warning | `Pro. Diagrams Swimlane Layout` | Cạnh nối không được chạy đè dọc lên vạch phân cách Swimlane. |
| `W-ISO-WCAG-CONTRAST` | Warning | `WCAG 2.1 AA (SC 1.4.3)` | Tương phản chữ/nền trong mọi nút phải đạt `>= 4.5:1`. |

Nếu `validate_iso5807.py` báo lỗi hoặc cảnh báo, chạy với cờ `--json` để đọc mảng `supportedFixes[]` (kèm trường `clause`) và sửa dứt điểm trong **tối đa 2 vòng lặp** rồi kết xuất lại `.svg`/`.html`.
