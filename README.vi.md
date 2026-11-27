# Pro. Diagrams (`pro-diagrams`)

[![CI](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml/badge.svg)](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-2B373E.svg)](./LICENSE)

[English](./README.md) | **Tiếng Việt**

**Agent Skill** chuyên dụng giúp AI thiết kế, kiểm định và kết xuất các sơ đồ, đồ thị đạt chuẩn xuất bản: **lưu đồ quy trình ISO 5807:1985**, **Swimlane ISO 5807 cho SOP liên phòng ban & Runbook tương tác**, **đồ thị cấu trúc & mạng đường găng CPM**, **biểu đồ số liệu kiểm chứng tỷ lệ `data-*`** và **đồ thị hàm số toán học ($y = f(x)$)**.

Chạy **100% trên thư viện chuẩn Python 3 (`stdlib`)** — không cần `pip install`, không yêu cầu cài đặt Draw.io Desktop hay Graphviz mới xem được hình. Thiết kế đồng bộ bằng bảng màu **Atelier Technical Warm** (đạt chuẩn tương phản WCAG AA/AAA) và phông chữ **Open Sans** tối ưu hiển thị dấu tiếng Việt.

---

## Tính Năng Nổi Bật

### 1. Khai Thác Thông Tin Thông Minh (`Smart Intake & Targeted Discovery`)
- Tích hợp sẵn quy trình đánh giá mức độ đầy đủ dữ kiện ([`references/discovery-and-elicitation.md`](skills/pro-diagrams/references/discovery-and-elicitation.md)):
  - **Vẽ ngay không hỏi thừa** khi đề bài đã có đủ bước, nhánh rẽ, số liệu thật hoặc người dùng yêu cầu *"vẽ mẫu / tự đề xuất"*.
  - **Đọc tệp nguồn trước** (mã nguồn, CSV/JSON, tài liệu SOP, tệp `.drawio` cũ) rồi chỉ hỏi phần còn khuyết.
  - **Gom 1 lượt hỏi gọn 2–5 câu kèm gợi ý `(Khuyến nghị)`** khi thiếu dữ kiện cốt lõi — tư vấn chọn đúng loại biểu đồ phù hợp mục đích trình bày và **tuyệt đối không tự bịa số liệu thật, hạn mức phê duyệt hay SLA**.

### 2. Nhánh 1 — Lưu Đồ ISO 5807, Swimlane ISO 5807 cho SOP & Đồ Thị Cấu Trúc (`.drawio` + `.svg` + `.html`)
- **Đầy đủ 23 ký hiệu ISO 5807:1985 & mở rộng tiêu chuẩn** ánh xạ đúng từng điều khoản `§9.x / §10.x`: `terminator` (`§9.4.2`), `process` (`§9.2.1`), `decision` (`§9.2.2.4`), `data` (`§9.1.1.1`), `predefined_process` (`§9.2.2.1`), `document` (`§9.1.2.4`), `multi_document` (`§9.1.2.4 & §10.3.2`), `database` & `direct_data` (`§9.1.2.3`), `stored_data` (`§9.1.1.2`), `sequential_data` (`§9.1.2.2`), `internal_storage` (`§9.1.2.1`), `preparation` (`§9.2.2.3`), `manual_operation` (`§9.2.2.2`), `manual_input` (`§9.1.2.5`), `on_page_connector` (`§9.4.1`), `off_page_connector` *(mở rộng ANSI X3.5)*, `loop_limit_start`/`end` (`§9.2.2.6`), `delay` *(mở rộng ANSI/ASME)*, `display` (`§9.1.2.8`), `parallel_mode` (`§9.2.2.5`), `annotation` (`§9.4.3`).
- **Biên dịch tất định & chặn lỗi ngay từ JSON (`iso5807_builder.py`):**
  - Kiểm tra chặt loại nút `type`, ID đầu mút cạnh `from`/`to`, ID làn `lane`, `slot`, `attach_to`, `kind`, `direction` trước khi dàn trang — dừng biên dịch và báo rõ trường sai kèm gợi ý sửa nếu JSON lỗi.
  - **Chặn chu trình trong CPM (`kind: "cpm"`):** Phát hiện phụ thuộc vòng (ví dụ `A <-> B`) và dừng biên dịch kèm danh sách công việc liên quan; trong khi các vòng lặp thử lại của lưu đồ quy trình vẫn được định tuyến gọn qua hành lang biên ngoài (`score: 0`).
  - Xuất `.drawio` XML không nén mở kéo-thả chỉnh sửa 100% trên [diagrams.net](https://app.diagrams.net) / VS Code.
- **Bộ kiểm định 12 quy tắc ISO 5807:1985, Swimlane & WCAG AA (`validate_iso5807.py`):** Bắt lỗi hình thoi `Decision` có `> 1` lối vào (`E-ISO-DECISION-ENTRY` theo **§9.2.2.4**), gắn điều khoản chuẩn cho từng mục chẩn đoán trong `diagnostics[]` + `supportedFixes[]`.
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

## Bộ Mẫu Chạy Ngay (`examples/`)

Mỗi thư mục mẫu đều kèm sẵn `spec.json` đầu vào cùng đầy đủ sản phẩm đầu ra đã qua kiểm định nghiêm ngặt:

| Mẫu minh họa | Nhánh áp dụng | Tệp đầu vào | Đầu ra đã kiểm định |
|---|---|---|---|
| **Lưu đồ Thanh toán & Thử lại** | ISO 5807:1985 (`TB`, vòng thử lại + điểm nối `A→A`) | [`spec.json`](examples/iso5807-payment-retry/spec.json) | [`.drawio`](examples/iso5807-payment-retry/payment_retry.drawio) · [`.svg`](examples/iso5807-payment-retry/payment_retry.svg) · [`.html`](examples/iso5807-payment-retry/payment_retry.html) (`0 lỗi, 0 cảnh báo, score: 0`) |
| **SOP Mua sắm Thiết bị R&D (4 làn)** | Swimlane ISO 5807 liên phòng ban + Runbook | [`spec.json`](examples/swimlane-rd-procurement/spec.json) | [`.drawio`](examples/swimlane-rd-procurement/procurement.drawio) · [`.svg`](examples/swimlane-rd-procurement/procurement.svg) · [`.html`](examples/swimlane-rd-procurement/procurement.html) · [`_runbook.html`](examples/swimlane-rd-procurement/procurement_runbook.html) (`0 lỗi, 0 cảnh báo, score: 0`) |
| **Thác nước Chi phí Vận hành 2026** | Biểu đồ định lượng (`850 → 860 tr`, kiểm định `data-*`) | [`spec.json`](examples/waterfall-opex-2026/spec.json) | [`.html`](examples/waterfall-opex-2026/waterfall_opex_2026.html) · [`.svg`](examples/waterfall-opex-2026/waterfall_opex_2026.svg) (`6/6 data-* PASS`) |

---

## Cài Đặt Nhanh

### Cài qua CLI Agent Skills (Claude Code, Cursor, Codex, Antigravity, Copilot, OpenCode)

```bash
npx skills add vietdq99tb/pro-diagrams
```

### Cài thủ công từ GitHub hoặc tệp `.skill`

```bash
git clone https://github.com/vietdq99tb/pro-diagrams.git

# Cho Claude Code (toàn cục):
cp -r pro-diagrams/skills/pro-diagrams ~/.claude/skills/pro-diagrams

# Hoặc cho thư mục dự án (Codex / Cursor / Antigravity):
cp -r pro-diagrams/skills/pro-diagrams .agents/skills/pro-diagrams
```

Với Claude Desktop hoặc cài offline bằng tệp ZIP `pro-diagrams.skill`, tải bản phát hành tại [GitHub Releases](https://github.com/vietdq99tb/pro-diagrams/releases) (hoặc tự đóng gói tại chỗ bằng `(cd pro-diagrams/skills && zip -r ../../pro-diagrams.skill pro-diagrams)`). Xem hướng dẫn chi tiết tại [`skills/pro-diagrams/INSTALL_GUIDE.md`](skills/pro-diagrams/INSTALL_GUIDE.md).

---

## Lệnh Chạy Thử Ngay & Kiểm Thử (Quick Start)

Chạy trực tiếp ngay sau khi clone repo bằng các tệp mẫu trong `examples/`:

```bash
# 1. Chạy toàn bộ 30 bài kiểm thử đơn vị & đối kháng (thuần Python 3 stdlib)
PYTHONDONTWRITEBYTECODE=1 python3 -B -W error::ResourceWarning -m unittest discover -s skills/pro-diagrams/tests -v

# 2. Biên dịch mẫu Swimlane ISO 5807 (4 phòng ban) -> .drawio + .svg + .html + SOP Runbook trong 1 lệnh
python3 skills/pro-diagrams/scripts/iso5807_builder.py \
  examples/swimlane-rd-procurement/spec.json \
  -o /tmp/procurement.drawio \
  --render-svg /tmp/procurement.svg \
  --render-html /tmp/procurement.html \
  --render-runbook /tmp/procurement_runbook.html

# 3. Kiểm định nghiêm ngặt theo 12 quy tắc ISO 5807:1985, Swimlane & WCAG AA
python3 skills/pro-diagrams/scripts/validate_iso5807.py /tmp/procurement.drawio --strict --score

# 4. Dịch nhãn sơ đồ Việt <-> Anh giữ nguyên 100% bố cục
python3 skills/pro-diagrams/scripts/relabel.py /tmp/procurement.drawio --extract -o /tmp/labels.json
python3 skills/pro-diagrams/scripts/relabel.py /tmp/procurement.drawio --map /tmp/labels_en.json -o /tmp/procurement_en.drawio

# 5. Tạo & kiểm định trung thực tỷ lệ data-* cho biểu đồ thác nước OpEx 2026
python3 skills/pro-diagrams/scripts/chart_builder.py \
  examples/waterfall-opex-2026/spec.json \
  -o /tmp/waterfall.html --svg /tmp/waterfall.svg
python3 skills/pro-diagrams/scripts/chart_verify.py /tmp/waterfall.html
```

---

## Cấu Trúc Repository

```text
pro-diagrams/
├── README.md                     # Tài liệu tổng quan (Tiếng Anh)
├── README.vi.md                  # Tài liệu tổng quan (Tiếng Việt)
├── LICENSE                       # Giấy phép MIT & ghi công bên thứ ba
├── .github/workflows/ci.yml      # GitHub Actions CI chạy 30 test & kiểm định examples/ (Python 3.11 & 3.12)
├── examples/
│   ├── iso5807-payment-retry/    # Mẫu lưu đồ ISO 5807 chạy ngay (spec.json + .drawio + .svg + .html)
│   ├── swimlane-rd-procurement/  # Mẫu Swimlane ISO 5807 (4 làn) + SOP Runbook tương tác
│   └── waterfall-opex-2026/      # Mẫu biểu đồ thác nước kiểm chứng data-* (.html + .svg)
└── skills/pro-diagrams/
    ├── SKILL.md                  # Bộ định tuyến chính (Progressive Disclosure)
    ├── INSTALL_GUIDE.md          # Hướng dẫn cài đặt & sử dụng chi tiết
    ├── LICENSE                   # Giấy phép MIT + Third-Party Notices
    ├── data/                     # Danh mục 23 hình ISO 5807 §9.x, theme tokens, chỉ mục 10.446 hình + APACHE-2.0.txt
    ├── references/               # 7 tài liệu tham chiếu (gồm discovery-and-elicitation.md)
    ├── scripts/                  # 20 script thuần Python 3 stdlib (0 phụ thuộc ngoài)
    ├── styles/                   # JSON Schema + 4 preset màu tích hợp
    ├── evals/                    # Bộ kịch bản đánh giá benchmark
    └── tests/                    # 30 bài kiểm thử hồi quy & đối kháng
```

---

## Giấy Phép & Ghi Công

Phát hành theo **Giấy phép MIT** ([`LICENSE`](./LICENSE)).
Phát triển dựa trên lõi `.drawio` mô-đun từ [`Agents365-ai/drawio-skill`](https://github.com/Agents365-ai/drawio-skill) (MIT), sử dụng chỉ mục hình vẽ Draw.io giấy phép Apache-2.0 từ `jgraph/drawio-mcp` (đính kèm toàn văn giấy phép tại [`skills/pro-diagrams/data/APACHE-2.0.txt`](skills/pro-diagrams/data/APACHE-2.0.txt) theo mục 4(a) và ghi công tại [`skills/pro-diagrams/data/SHAPE-INDEX-NOTICE.md`](skills/pro-diagrams/data/SHAPE-INDEX-NOTICE.md)), tham khảo ý tưởng kiểm định trung thực `data-*` từ [`cathrynlavery/diagram-design`](https://github.com/cathrynlavery/diagram-design) (MIT) và hợp đồng chẩn đoán `diagnostics[]`/`supportedFixes[]` từ [`tt-a1i/archify`](https://github.com/tt-a1i/archify) (Apache-2.0).
