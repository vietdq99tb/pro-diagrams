# Pro. Diagrams (`pro-diagrams`)

[![CI](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml/badge.svg)](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-2B373E.svg)](./LICENSE)

[English](./README.md) | **Tiếng Việt**

**Agent Skill** chuyên dụng giúp AI thiết kế, kiểm định và kết xuất các sơ đồ, đồ thị đạt chuẩn xuất bản: **lưu đồ quy trình ISO 5807:1985**, **sơ đồ liên phòng ban Swimlane / BPMN & SOP Runbook tương tác**, **đồ thị cấu trúc & mạng đường găng CPM**, **biểu đồ số liệu kiểm chứng tỷ lệ `data-*`** và **đồ thị hàm số toán học ($y = f(x)$)**.

Chạy **100% trên thư viện chuẩn Python 3 (`stdlib`)** — không cần `pip install`, không yêu cầu cài đặt Draw.io Desktop hay Graphviz mới xem được hình. Thiết kế đồng bộ bằng bảng màu **Atelier Technical Warm** (đạt chuẩn tương phản WCAG AA/AAA) và phông chữ **Open Sans** tối ưu hiển thị dấu tiếng Việt.

---

## Tính Năng Nổi Bật

### 1. Khai Thác Thông Tin Thông Minh (`Smart Intake & Targeted Discovery`)
- Tích hợp sẵn quy trình đánh giá mức độ đầy đủ dữ kiện ([`references/discovery-and-elicitation.md`](skills/pro-diagrams/references/discovery-and-elicitation.md)):
  - **Vẽ ngay không hỏi thừa** khi đề bài đã có đủ bước, nhánh rẽ, số liệu thật hoặc người dùng yêu cầu *"vẽ mẫu / tự đề xuất"*.
  - **Đọc tệp nguồn trước** (mã nguồn, CSV/JSON, tài liệu SOP, tệp `.drawio` cũ) rồi chỉ hỏi phần còn khuyết.
  - **Gom 1 lượt hỏi gọn 2–5 câu kèm gợi ý `(Khuyến nghị)`** khi thiếu dữ kiện cốt lõi — tư vấn chọn đúng loại biểu đồ phù hợp mục đích trình bày và **tuyệt đối không tự bịa số liệu thật, hạn mức phê duyệt hay SLA**.

### 2. Nhánh 1 — Lưu Đồ ISO 5807, Swimlane SOP & Đồ Thị Cấu Trúc (`.drawio` + `.svg` + `.html`)
- **Đầy đủ 23 ký hiệu ISO 5807:1985 & mở rộng tiêu chuẩn:** `terminator`, `process`, `decision`, `data`, `predefined_process`, `document`, `multi_document`, `database`, `direct_data`, `stored_data`, `sequential_data`, `internal_storage`, `preparation`, `manual_operation`, `manual_input`, `on_page_connector`, `off_page_connector`, `loop_limit_start`/`end`, `delay`, `display`, `parallel_mode`, `annotation`.
- **Biên dịch tất định JSON → `.drawio` XML không nén (`iso5807_builder.py`):** Mở kéo-thả chỉnh sửa 100% trên [diagrams.net](https://app.diagrams.net) / VS Code. Hỗ trợ sắp lớp Sugiyama 3 lượt, Swimlane đa phòng ban hướng dọc (`TB`) & ngang (`LR`), tự động tính mạng đường găng **CPM** (`ES`, `EF`, `LS`, `LF`, `TF`), và định tuyến vuông góc tránh chồng lấn (`score: 0`).
- **Bộ kiểm định 11 quy tắc ISO 5807 & WCAG AA (`validate_iso5807.py`):** Xuất chẩn đoán có cấu trúc `diagnostics[]` + gợi ý sửa tự động `supportedFixes[]`.
- **Kết xuất & Tái sử dụng không cần app ngoài:**
  - `drawio_render_svg.py` & `drawiohtml.py`: Xuất `.svg` độc lập, `.html` phóng to/thu nhỏ/tìm kiếm nút (và `--png` qua headless Chrome khi có sẵn).
  - `runbook.py`: Chuyển sơ đồ quy trình thành **trang SOP Runbook tương tác bấm-chọn từng bước** cho nhân viên vận hành.
  - `relabel.py`: Dịch nhãn sơ đồ **Việt ↔ Anh giữ nguyên 100% bố cục**.
  - `restyle.py`: Chuyển đổi Sáng ↔ Tối bảo toàn trọn vẹn 7 vai trò màu ngữ nghĩa và màu nền Swimlane.
  - `drawio2mermaid.py`, `shapesearch.py` (tra cứu 10.446 hình Draw.io chính thức), `edgeports.py`, `encode_drawio_url.py`.

### 3. Nhánh 2 — Biểu Đồ Số Liệu Trung Thực & Đồ Thị Hàm Số (`HTML` + `SVG`)
- **6 loại biểu đồ định lượng (`chart_builder.py`):** `bar` (cột đứng), `grouped_bar` (cột ghép), `horizontal_bar` (thanh ngang hỗ trợ trục gốc 0 phân kỳ âm/dương), `line` (đường xu hướng), `waterfall` (thác nước biến động), `sankey` (dòng chảy bảo toàn tổng), kèm dải thẻ tóm tắt KPI.
- **Kiểm định trung thực toán học & WCAG 2.1 AA (`chart_verify.py`):** Tự động kiểm tra tỷ lệ hình học `data-*` (sai số `<= 3%` cho cột/thanh ngang/waterfall và tuyến tính `cy` biểu đồ đường), bảo toàn tổng nút nội bộ Sankey, và đo độ tương phản chữ sRGB trên cả SVG lẫn HTML.
- **Vẽ đồ thị hàm số $y = f(x)$ thuần Python (`plot_math_svg.py`):** Kiểm duyệt biểu thức bằng AST whitelist an toàn, tự tách miền qua điểm gián đoạn (`1/x`), hỗ trợ đường tiệm cận (đứng/ngang/xiên), tô miền diện tích tích phân và gắn nhãn cực trị/điểm uốn/giao điểm.

---

## Hệ Màu Chủ Đề: Atelier Technical Warm (`Open Sans`)

Triết lý cân bằng cấu trúc: **Kim tạo khung kỷ luật · Hỏa tạo điểm nhớ · Thổ tạo nền ấm · Thủy lưu thông dữ liệu**.

| Vai trò (Slot) | Nền hộp (Sáng) | Viền / Nhấn (Sáng) | Tương phản Chữ | Ánh xạ ISO 5807 & Biểu đồ |
|---|---|---|---:|---|
| **Canvas / Surface** | `#F8F6F2` / `#FFFFFF` | `#C9D2D8` | `14.75:1` AAA | Nền giấy sứ ấm & thẻ trắng sạch chuẩn in ấn/slide |
| **`neutral`** | `#FFFFFF` | `#4A5860` | `15.92:1` AAA | `Process`, `Preparation`, `Loop Limit`, `Annotation` |
| **`primary`** | `#EEF2F5` | `#2B373E` | `14.14:1` AAA | `Terminator`, `Predefined Process`, `Connector`, `Parallel Mode` |
| **`accent`** | `#FDF1EE` | `#AD4333` | `14.40:1` AAA | `Decision` (Hình thoi), Đường găng CPM (`TF=0`), KPI tiêu điểm |
| **`secondary`** | `#EDF3F6` | `#395E73` | `14.22:1` AAA | `Data I/O`, `Database`, Các khối lưu trữ, `Display` |
| **`warning`** | `#FAF4EA` | `#8C5D2B` | `14.55:1` AAA | `Document`, `Manual Operation`, `Manual Input`, `Delay` |
| **`danger`** | `#FCECEB` | `#9E2F2C` | `13.90:1` AAA | Nhánh lỗi nghiêm trọng / ngắt khẩn cấp |
| **`success`** | `#EEF4F1` | `#2D6A5B` | `14.29:1` AAA | Chỉ báo biến động dương `+Δ` tiết chế trên biểu đồ |

Kèm sẵn bộ giao diện nền tối (`tech-warm-dark`), bộ màu thân thiện người mù màu (`colorblind-safe` Okabe-Ito) và phong cách phác thảo (`handdrawn`).

---

## Cài Đặt Nhanh

### Cài qua CLI Agent Skills (Claude Code, Cursor, Codex, Antigravity, Copilot, OpenCode)

```bash
npx skills add vietdq99tb/pro-diagrams
```

### Cài thủ công từ GitHub

```bash
git clone https://github.com/vietdq99tb/pro-diagrams.git

# Cho Claude Code (toàn cục):
cp -r pro-diagrams/skills/pro-diagrams ~/.claude/skills/pro-diagrams

# Hoặc cho thư mục dự án (Codex / Cursor / Antigravity):
cp -r pro-diagrams/skills/pro-diagrams .agents/skills/pro-diagrams
```

Xem thêm hướng dẫn chi tiết và cách đóng gói cho Claude Desktop tại [`skills/pro-diagrams/INSTALL_GUIDE.md`](skills/pro-diagrams/INSTALL_GUIDE.md).

---

## Lệnh CLI & Kiểm Thử Nhanh

```bash
# Chạy toàn bộ 26 bài kiểm thử đơn vị & đối kháng (thuần Python 3 stdlib)
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s skills/pro-diagrams/tests -v

# Biên dịch lưu đồ ISO 5807 / Swimlane -> .drawio + .svg + .html + SOP Runbook trong 1 lệnh
python3 skills/pro-diagrams/scripts/iso5807_builder.py spec.json \
  -o flow.drawio \
  --render-svg flow.svg \
  --render-html flow.html \
  --render-runbook flow_runbook.html

# Kiểm định nghiêm ngặt theo 11 quy tắc ISO 5807:1985 & WCAG AA
python3 skills/pro-diagrams/scripts/validate_iso5807.py flow.drawio --strict --score

# Dịch nhãn sơ đồ Việt <-> Anh giữ nguyên 100% bố cục
python3 skills/pro-diagrams/scripts/relabel.py flow.drawio --extract -o labels.json
python3 skills/pro-diagrams/scripts/relabel.py flow.drawio --map labels_en.json -o flow_en.drawio

# Tạo & kiểm định trung thực tỷ lệ data-* cho biểu đồ số liệu
python3 skills/pro-diagrams/scripts/chart_builder.py chart_spec.json -o chart.html --svg chart.svg
python3 skills/pro-diagrams/scripts/chart_verify.py chart.html

# Vẽ đồ thị hàm số y = f(x) ra SVG/HTML độc lập
python3 skills/pro-diagrams/scripts/plot_math_svg.py math_spec.json -o plot.svg --html plot.html
```

---

## Cấu Trúc Repository

```text
pro-diagrams/
├── README.md                     # Tài liệu tổng quan (Tiếng Anh)
├── README.vi.md                  # Tài liệu tổng quan (Tiếng Việt)
├── LICENSE                       # Giấy phép MIT & ghi công bên thứ ba
├── .github/workflows/ci.yml      # GitHub Actions CI chạy 26 unit test (Python 3.11 & 3.12)
└── skills/pro-diagrams/
    ├── SKILL.md                  # Bộ định tuyến chính (Progressive Disclosure)
    ├── INSTALL_GUIDE.md          # Hướng dẫn cài đặt & sử dụng chi tiết
    ├── LICENSE                   # Giấy phép MIT + Third-Party Notices
    ├── data/                     # Danh mục 23 hình ISO 5807, theme tokens, chỉ mục 10.446 hình Draw.io
    ├── references/               # 7 tài liệu tham chiếu (gồm discovery-and-elicitation.md)
    ├── scripts/                  # 20 script thuần Python 3 stdlib (0 phụ thuộc ngoài)
    ├── styles/                   # JSON Schema + 4 preset màu tích hợp
    ├── evals/                    # Bộ kịch bản đánh giá benchmark
    └── tests/                    # 26 bài kiểm thử hồi quy & đối kháng
```

---

## Giấy Phép & Ghi Công

Phát hành theo **Giấy phép MIT** ([`LICENSE`](./LICENSE)).
Phát triển dựa trên lõi `.drawio` mô-đun từ [`Agents365-ai/drawio-skill`](https://github.com/Agents365-ai/drawio-skill) (MIT), sử dụng chỉ mục hình vẽ Draw.io giấy phép Apache-2.0 từ `jgraph/drawio-mcp` (xem `skills/pro-diagrams/data/SHAPE-INDEX-NOTICE.md`), tham khảo ý tưởng kiểm định trung thực `data-*` từ [`cathrynlavery/diagram-design`](https://github.com/cathrynlavery/diagram-design) (MIT) và hợp đồng chẩn đoán `diagnostics[]`/`supportedFixes[]` từ [`tt-a1i/archify`](https://github.com/tt-a1i/archify) (Apache-2.0).
