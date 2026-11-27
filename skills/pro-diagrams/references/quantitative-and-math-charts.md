# Biểu Đồ Số Liệu (`data-*` Honesty) & Đồ Thị Hàm Số Toán Học (`y = f(x)`)

Tài liệu này bao phủ nghĩa thứ hai của từ **"đồ thị"**: trực quan hóa dữ liệu định lượng (KPI, tài chính, thống kê) và vẽ đồ thị hàm số giải tích.

---

## 1. Biểu Đồ Số Liệu Trung Thực (`scripts/chart_builder.py` + `scripts/chart_verify.py`)

Tuyệt đối không ước lượng chiều cao cột hay tọa độ điểm bằng mắt trong LLM. Luôn khai báo dữ liệu nguồn vào JSON spec và biên dịch bằng `chart_builder.py`, sau đó xác minh toán học bằng `chart_verify.py`.

### Các loại biểu đồ hỗ trợ sẵn
- `"bar"`: Biểu đồ cột đứng (tự động nhấn màu **Kiln Terracotta `#AD4333`** cho các cột gắn `"focal": true`, giữ màu **Structural Slate `#2B373E`** cho cột nền).
- `"grouped_bar"`: Biểu đồ cột ghép nhiều chuỗi (`categories` + mảng `series`).
- `"horizontal_bar"`: Biểu đồ thanh ngang xếp hạng (lí tưởng khi nhãn danh mục tiếng Việt dài).
- `"line"`: Biểu đồ đường xu hướng 1 hoặc nhiều chuỗi theo thời gian.
- `"waterfall"`: Biểu đồ thác nước phân rã biến động (`kind`: `"start"` → các bước `"delta"` dương/âm → `"total"`).
- `"sankey"`: Biểu đồ dòng chảy bảo toàn lưu lượng (`links: [{"source", "target", "value"}]`).

### Mẫu JSON Spec (`waterfall` kèm thẻ tóm tắt KPI)

```json
{
  "chart_type": "waterfall",
  "eyebrow": "PHÂN TÍCH HIỆU QUẢ VẬN HÀNH Q1–Q4",
  "title": "Cầu nối Biến động Lợi nhuận Hoạt động Năm 2026 (Tỷ VNĐ)",
  "subtitle": "Đóng góp từ tăng trưởng sản lượng, tối ưu tự động hóa quy trình và biến động chi phí nguyên liệu",
  "unit": " tỷ",
  "decimals": 1,
  "kpis": [
    { "label": "Đầu kỳ (2025)", "value": "120.0 tỷ" },
    { "label": "Cuối kỳ (2026)", "value": "164.5 tỷ", "delta": "+37.1% YoY" },
    { "label": "Động lực lớn nhất", "value": "+38.0 tỷ", "delta": "+Tăng sản lượng lõi" }
  ],
  "steps": [
    { "label": "LN 2025", "kind": "start", "value": 120.0 },
    { "label": "Tăng sản lượng", "kind": "delta", "value": 38.0 },
    { "label": "Tự động hóa SOP", "kind": "delta", "value": 24.5 },
    { "label": "Giá nguyên liệu", "kind": "delta", "value": -12.0 },
    { "label": "Đầu tư R&D", "kind": "delta", "value": -6.0 },
    { "label": "LN 2026", "kind": "total" }
  ],
  "source": "Nguồn: Báo cáo Quản trị Nội bộ · Đơn vị tính: Tỷ VNĐ"
}
```

### Quy trình thực thi & kiểm định bắt buộc

```bash
# 1. Sinh trang HTML+SVG tương phản WCAG AA + xuất kèm file .svg sạch để chèn PowerPoint/Word
python3 <skill-dir>/scripts/chart_builder.py chart_spec.json \
  -o kpi_chart.html \
  --svg kpi_chart.svg

# 2. Kiểm định tỷ lệ hình học trung thực với dữ liệu (sai số <= 3%, bảo toàn tổng Waterfall/Sankey)
python3 <skill-dir>/scripts/chart_verify.py kpi_chart.html
```

---

## 2. Đồ Thị Hàm Số Toán Học (`scripts/plot_math_svg.py`)

Chạy hoàn toàn bằng Python 3 stdlib (không cần cài `matplotlib`), hỗ trợ vẽ nhiều hàm số $y = f(x)$ (dùng toán tử lũy thừa `**` của Python, không dùng `^`), đường tiệm cận đứng (`"x"`), ngang (`"y"`), xiên (`"expr"`), tô miền diện tích tích phân và đánh dấu cực trị / giao điểm bằng phông `Open Sans` + `JetBrains Mono`:

```json
{
  "title": "Khảo sát Hàm Phân thức Hữu tỷ & Tiệm cận",
  "x_range": [-4, 5],
  "y_range": [-5, 6],
  "x_step": 1,
  "y_step": 1,
  "x_label": "x",
  "y_label": "y",
  "shade_area": { "expr": "x - 1 + 1/(x - 1)", "from": 2, "to": 4 },
  "asymptotes": [
    { "x": 1 },
    { "y": 2 },
    { "expr": "x - 1" }
  ],
  "functions": [
    { "expr": "x - 1 + 1/(x - 1)", "label": "f(x) = x - 1 + 1/(x - 1)" },
    { "expr": "2 - 3/(x**2 + 1)", "label": "g(x) = 2 - 3/(x² + 1)", "dashed": true }
  ],
  "points": [
    { "x": 0, "y": -2, "label": "Cực đại (0, -2)", "dx": -52, "dy": -12 },
    { "x": 2, "y": 2, "label": "Cực tiểu (2, 2)", "dx": 10, "dy": 16 }
  ]
}
```

```bash
python3 <skill-dir>/scripts/plot_math_svg.py math_spec.json -o function_plot.svg --html function_plot.html
```
