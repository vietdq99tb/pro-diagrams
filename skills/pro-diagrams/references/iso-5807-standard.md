# Chuẩn Lưu Đồ Quy Trình ISO 5807:1985 & Quy Trình Kiểm Định

Tài liệu này quy định cách xây dựng, kết xuất và kiểm định lưu đồ thuật toán / quy trình nghiệp vụ tuân thủ nghiêm ngặt **ISO 5807:1985**.

---

## 1. Danh Mục Ký Hiệu Chuẩn ISO 5807:1985 (`data/iso5807-shapes.json`)

Khi dùng `scripts/iso5807_builder.py`, khai báo trường `"type"` của từng nút theo đúng bảng sau (tuyệt đối không dùng hình chữ nhật cho Quyết định hay dùng `ellipse` tròn cho Điểm đầu/cuối):

| `type` trong JSON | Tên chuẩn ISO 5807 | Ký hiệu hình học | Khi nào sử dụng |
|---|---|---|---|
| `terminator` | Terminator (§7.3.1) | Viên thuốc / Stadium | Điểm **Bắt đầu** (`in=0, out>=1`) và **Kết thúc** (`in>=1, out=0`). |
| `process` | Process (§6.2.1) | Hình chữ nhật vuông góc | Bước xử lý, tính toán, nghiệp vụ cụ thể. |
| `decision` | Decision (§7.1.2) | Hình thoi (`diamond`) | Kiểm tra điều kiện rẽ nhánh (**≥ 2 lối ra**, 100% nhánh phải có nhãn). |
| `data` | Data I/O (§6.1.1) | Hình bình hành | Nhập dữ liệu đầu vào hoặc xuất kết quả đầu ra. |
| `predefined_process` | Predefined Process (§6.2.2) | Chữ nhật có 2 vạch dọc | Gọi quy trình con / module / hàm đã định nghĩa riêng. |
| `document` | Document (§6.4.3) | Chữ nhật đáy lượn sóng | Tạo/xuất một biểu mẫu, biên bản, báo cáo, hóa đơn. |
| `multi_document` | Multi-Document (§6.4.3) | Tập tài liệu xếp lớp | Bộ hồ sơ gồm nhiều chứng từ đi kèm nhau. |
| `database` | Magnetic Disk / DB (§6.3.4) | Hình trụ đứng | Đọc/ghi cơ sở dữ liệu có cấu trúc. |
| `direct_data` | Direct Access Storage (§6.3.3) | Hình trụ ngang | Bộ nhớ truy cập trực tiếp (cache, key-value). |
| `stored_data` | Stored Data (§6.1.2) | Hình cong lồi–lõm | Kho tệp tin / dữ liệu lưu trữ chung. |
| `sequential_data` | Sequential Storage (§6.3.1) | Hình tròn có đuôi ngang | Ghi log tuần tự, hàng đợi sự kiện nối tiếp. |
| `internal_storage` | Internal Storage (§6.3.2) | Chữ nhật kẻ ô góc trái | Cấu trúc dữ liệu / biến trong RAM. |
| `preparation` | Preparation (§7.1.3) | Hình lục giác dẹt | Khởi tạo biến, thiết lập tham số hoặc bộ đếm vòng lặp. |
| `manual_operation` | Manual Operation (§6.2.4) | Hình thang cân đáy nhỏ dưới | Thao tác thủ công của con người (kiểm hàng, ký tay). |
| `manual_input` | Manual Input (§6.4.1) | Tứ giác cạnh trên vát nghiêng | Người dùng nhập liệu qua bàn phím / form / máy quét. |
| `on_page_connector` | Connector (§7.3.2) | Hình tròn nhỏ (44×44) | Điểm nối cùng trang tránh cắt dây — **bắt buộc đi theo cặp cùng mã** (`A` vào → `A` ra). |
| `off_page_connector` | Off-Page Connector | Ngũ giác mũi nhọn dưới | Chuyển luồng sang trang khác (ghi rõ mã & số trang). |
| `loop_limit_start` / `loop_limit_end` | Loop Limit (§7.3.3) | Lục giác vát 2 góc trên / dưới | Mở và đóng khối lặp (phải cân bằng số lượng mở/đóng). |
| `delay` | Delay | Hình chữ D | Chờ phê duyệt, timeout, chờ batch định kỳ. |
| `display` | Display (§6.4.6) | Đầu nhọn trái, cong phải | Hiển thị thông báo/cảnh báo lên màn hình. |
| `parallel_mode` | Parallel Mode (§7.3.4) | Cặp hai vạch ngang song song | Tách (fork) hoặc đồng bộ gom (join) các nhánh chạy song song. |
| `annotation` | Annotation (§7.2.4) | Ngoặc vuông mở `[` + dây đứt | Ghi chú giải thích gắn vào một nút qua trường `"attach_to"`. |

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

# 2. Kiểm định cấu trúc + 11 quy tắc ngữ nghĩa ISO 5807 & WCAG AA
python3 <skill-dir>/scripts/validate_iso5807.py output.drawio --strict --score
```

Nếu `validate_iso5807.py` báo lỗi hoặc cảnh báo (`E-ISO-START`, `E-ISO-END`, `W-DECISION-EXIT`, `W-ISO-DECISION-EXIT`, `E-ISO-DECISION-LABEL`, `E-ISO-CONNECTOR-PAIR`, `W-ISO-LOOP-PAIR`, `W-ISO-ORPHAN`, `W-ISO-FLOW-DIR`, `W-ISO-SWIMLANE-CROSS`, `W-ISO-STYLE-STRICT`, `W-ISO-WCAG-CONTRAST`), hãy chạy với cờ `--json` để đọc mảng `supportedFixes[]` và sửa dứt điểm trong **tối đa 2 vòng lặp** rồi kết xuất lại `.svg`/`.html`.
