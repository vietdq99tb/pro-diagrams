# Đồ Thị Cấu Trúc (Topological Graphs): DAG, Cây, Mạng Phụ Thuộc & Đường Găng CPM

Tài liệu này bao phủ nghĩa thứ nhất của từ **"đồ thị"** trong tiếng Việt: đồ thị đỉnh–cạnh ($G = (V, E)$), đồ thị có hướng không chu trình (DAG), cây phân cấp, máy trạng thái, và mạng lịch trình đường găng **CPM (Critical Path Method)**.

---

## 1. Mạng Đường Găng Dự Án (`kind: "cpm"`)

Khi người dùng cần vẽ mạng công việc dự án, phân tích phụ thuộc hoặc tìm đường găng (Critical Path), sử dụng `scripts/iso5807_builder.py` với `"kind": "cpm"` và trường `"duration"` trên từng đỉnh:

- Trình biên dịch **tự động giải thuật toán quy hoạch động lượt đi & lượt về** để tính chính xác:
  - `ES` (*Earliest Start*), `EF` (*Earliest Finish*)
  - `LS` (*Latest Start*), `LF` (*Latest Finish*)
  - `TF` (*Total Float / Độ dự trữ toàn phần* $= LS - ES$)
- Mọi đỉnh và cung thuộc **Đường găng (`TF = 0`)** được tự động tô nhấn bằng màu **Gốm nung Terracotta (`#AD4333` / nền `#FDF1EE`, nét dày `2.5px`)** đúng tinh thần *"Hỏa tạo dấu ấn"*, còn các công việc có dự trữ (`TF > 0`) giữ khung Kim trung tính sắc nét.

```json
{
  "kind": "cpm",
  "direction": "LR",
  "duration_unit": "ngày",
  "title": "Đồ thị Mạng Phụ thuộc & Đường găng Triển khai Hệ thống (CPM)",
  "nodes": [
    { "id": "A", "code": "A", "label": "Khảo sát & Đặc tả", "duration": 4 },
    { "id": "B", "code": "B", "label": "Thiết kế Kiến trúc CSDL", "duration": 5 },
    { "id": "C", "code": "C", "label": "Thiết kế Giao diện UI", "duration": 3 },
    { "id": "D", "code": "D", "label": "Xây dựng API Lõi", "duration": 7 },
    { "id": "E", "code": "E", "label": "Phát triển Frontend", "duration": 5 },
    { "id": "F", "code": "F", "label": "Tích hợp & Kiểm thử tải", "duration": 4 }
  ],
  "edges": [
    { "from": "A", "to": "B" },
    { "from": "A", "to": "C" },
    { "from": "B", "to": "D" },
    { "from": "C", "to": "E" },
    { "from": "D", "to": "F" },
    { "from": "E", "to": "F" }
  ]
}
```

> **Lưu ý kiểm định:** Với đồ thị cấu trúc (`topological-graph` hoặc `cpm`), chạy `validate.py diagram.drawio --score` (kiểm định cấu trúc hình học, không bắt buộc `E-ISO-START`/`E-ISO-END` của lưu đồ quy trình nếu các đỉnh là tác vụ/module).

---

## 2. Đồ Thị DAG, Cây Phân Cấp & Mạng Tổng Quát (`kind: "topological-graph"`)

- Với đồ thị phụ thuộc module, cây quyết định, sơ đồ phân rã công việc (WBS) hoặc đồ thị trạng thái:
  - Đặt `"kind": "topological-graph"`, chọn `"direction": "LR"` (cho mạng phụ thuộc ngang) hoặc `"direction": "TB"` (cho cây phân cấp từ gốc xuống lá).
  - Có thể gán `"slot"` cho từng nhóm đỉnh (`"primary"`, `"neutral"`, `"secondary"`, `"warning"`, `"accent"`) để phân tầng kiến trúc rõ ràng mà vẫn giữ chuẩn tương phản WCAG AAA.
  - Nếu máy có cài sẵn Graphviz (`dot` / `tred`), có thể chạy thêm `python3 <skill-dir>/scripts/autolayout.py graph.json -o diagram.drawio --tune` để so sánh tự động điểm đọc giữa bố cục TB và LR; nếu không có `dot`, `iso5807_builder.py` đã tích hợp sẵn giải thuật phân tầng DAG + giảm cắt chéo barycenter bằng Python thuần.
  - Để phân tích cấu trúc đồ thị (tìm chu trình, đường đi ngắn nhất, điểm nghẽn đơn lẻ SPOF, hoặc phạm vi ảnh hưởng `whatif`), có thể gọi các hàm phân tích trong `scripts/diagram_ir.py` hoặc tóm tắt đồ thị bằng `scripts/explain.py diagram.drawio`.
