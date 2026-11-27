# Sơ Đồ Quy Trình Liên Phòng Ban (Swimlane / BPMN), Runbook SOP & Dịch Song Ngữ

Tài liệu này hướng dẫn thiết kế quy trình phối hợp nhiều vai trò / phòng ban không giới hạn số bước, xuất trang hướng dẫn vận hành bấm-chọn (`runbook.py`) và dịch giữ nguyên bố cục (`relabel.py`).

---

## 1. Quy Trình Liên Phòng Ban (`kind: "swimlane"`)

- Chọn hướng **`direction: "TB"`** (các làn đứng cạnh nhau thành cột, luồng chảy từ trên xuống dưới — chuẩn phổ biến nhất cho tài liệu SOP ISO Việt Nam trên khổ dọc) hoặc **`direction: "LR"`** (các làn xếp ngang từ trên xuống dưới, luồng chảy từ trái sang phải — chuẩn BPMN 2.0 màn hình rộng).
- Khai báo `"pool_title"` cho tên quy trình tổng và mảng `"lanes"` cho từng phòng ban / hệ thống; mỗi nút chỉ cần gắn `"lane": "<lane_id>"`.

```json
{
  "kind": "swimlane",
  "direction": "TB",
  "pool_title": "QUY TRÌNH PHÊ DUYỆT MUA SẮM THIẾT BỊ R&D",
  "title": "Lưu đồ Liên phòng ban: Đề xuất, Thẩm định & Giải ngân Mua sắm",
  "subtitle": "Chuẩn ký hiệu ISO 5807:1985 · 4 phòng ban phối hợp",
  "lanes": [
    { "id": "rd", "title": "Bộ phận R&D (Đề xuất)" },
    { "id": "proc", "title": "Phòng Mua hàng" },
    { "id": "fin", "title": "Phòng Tài chính – Kế toán" },
    { "id": "dir", "title": "Ban Giám đốc" }
  ],
  "nodes": [
    { "id": "s1", "lane": "rd", "type": "terminator", "label": "Bắt đầu nhu cầu" },
    { "id": "n1", "lane": "rd", "type": "manual_input", "label": "Lập phiếu yêu cầu mua sắm & thông số kỹ thuật" },
    { "id": "n2", "lane": "proc", "type": "process", "label": "Thu thập báo giá tối thiểu 3 nhà cung cấp" },
    { "id": "d1", "lane": "fin", "type": "decision", "label": "Ngân sách <= 100 triệu?" },
    { "id": "n3", "lane": "dir", "type": "manual_operation", "label": "Phê duyệt chủ trương đầu tư" },
    { "id": "e1", "lane": "fin", "type": "terminator", "label": "Hoàn tất đặt hàng" }
  ],
  "edges": [
    { "from": "s1", "to": "n1" },
    { "from": "n1", "to": "n2" },
    { "from": "n2", "to": "d1" },
    { "from": "d1", "to": "e1", "label": "Có" },
    { "from": "d1", "to": "n3", "label": "Không (>100tr)" },
    { "from": "n3", "to": "e1" }
  ]
}
```

### Quy tắc kiểm tra chất lượng Swimlane
1. Không để đường nối chạy chồng dọc trên vạch phân cách giữa hai làn (`W-ISO-SWIMLANE-CROSS`).
2. Các bước thực hiện thủ công bởi con người dùng `manual_operation` hoặc `manual_input`; các bước hệ thống tự động dùng `process` hoặc `predefined_process`; kho dữ liệu dùng `database`; chứng từ bàn giao giữa hai phòng ban dùng `document`.
3. Chạy `validate_iso5807.py output.drawio --score` để xác minh 0 lỗi chồng lấn hộp trong làn và 0 lỗi cắt xuyên nút.

---

## 2. Xuất Cẩm Nang Vận Hành Tương Tác (`runbook.py`)

Mọi tệp `.drawio` chuẩn ISO 5807 (kể cả sơ đồ Swimlane nhiều phòng ban) đều có thể xuất tức thì thành trang **HTML Runbook bấm-chọn từng bước** cho nhân viên vận hành tra cứu trực tiếp:

```bash
python3 <skill-dir>/scripts/runbook.py workflow.drawio -o workflow_runbook.html
```

- Tự động nhận diện điểm `Start` (`mxgraph.flowchart.terminator`), hiển thị từng bước hành động, tạo nút bấm cho từng nhánh `Decision` (`Có` / `Không` / ngoại lệ), lưu lịch sử đường đi (breadcrumbs) và cho phép quay lui từng bước.

---

## 3. Dịch Song Ngữ Việt ↔ Anh Giữ Nguyên 100% Bố Cục (`relabel.py`)

Khi cần xuất song song bản Tiếng Việt và bản Tiếng Anh mà không muốn dàn trang lại:

```bash
# 1. Trích xuất từ điển nhãn hiện tại ra JSON
python3 <skill-dir>/scripts/relabel.py workflow_vi.drawio --extract -o labels_vi.json

# 2. Dịch các giá trị chuỗi trong labels_en.json rồi nạp ngược vào bản vẽ
python3 <skill-dir>/scripts/relabel.py workflow_vi.drawio --map labels_en.json -o workflow_en.drawio
python3 <skill-dir>/scripts/drawio_render_svg.py workflow_en.drawio -o workflow_en.svg
```
