# Pro. Diagrams (`pro-diagrams`) — Hướng Dẫn Cài Đặt & Sử Dụng

Skill vẽ **Lưu đồ quy trình chuẩn ISO 5807:1985**, **Swimlane ISO 5807 cho SOP liên phòng ban**, **SOP Runbook tương tác**, **Đồ thị cấu trúc (DAG, Tree, Đường găng CPM)**, **Biểu đồ số liệu trung thực (`data-*`)** và **Đồ thị hàm số toán học ($y = f(x)$)** với bảng màu **`Atelier Technical Warm`** (`WCAG AA/AAA`) và phông chữ **`Open Sans`** hỗ trợ đầy đủ dấu tiếng Việt.

---

## 1. Kiến trúc Gói Skill (100% Python 3 Standard Library)

- **Không cần `pip install`**, không yêu cầu cài đặt Draw.io Desktop hay Graphviz mới xem được hình.
- **Khai thác thông tin thông minh (`references/discovery-and-elicitation.md`):** Tự động phân loại mức độ đầy đủ dữ kiện — vẽ ngay khi đề bài đã rõ, hoặc gom **1 vòng hỏi gọn 2–5 câu kèm gợi ý `(Khuyến nghị)`** để chọn đúng loại biểu đồ, đúng ký hiệu ISO 5807 và tuyệt đối không tự bịa số liệu thật.
- **Nhánh 1 (Đầy đủ 5 loại sơ đồ ISO 5807:1985 §4–§8, Swimlane & Đồ thị cấu trúc):** Biên dịch JSON (26 ký hiệu nút + 4 loại đường nối §9.3, sơ đồ nhiều trang với connector xuyên trang §10.2.2, nhãn chồng lớp §10.3.2, kiểm tra chặt schema & chu trình CPM) → **`.drawio` XML không nén** (kéo-thả chỉnh sửa 100% trên [app.diagrams.net](https://app.diagrams.net) / VS Code) + tự động kết xuất **`.svg` độc lập** + **`.html` phóng to/thu nhỏ/tìm kiếm** + **`_runbook.html` bấm chọn từng bước** + kiểm định tách bạch ISO 5807 / bố cục / WCAG AA (`validate_iso5807.py`), đã đối chiếu toàn bộ 6 ví dụ Phụ lục **A–E** của chuẩn ISO 5807:1985.
- **Nhánh 2 (Số liệu & Hàm số):** Sinh **`.html` + `.svg` sạch cho PowerPoint/Word** kèm kiểm định trung thực tỷ lệ hình học `data-*` (`chart_verify.py`) và bộ vẽ hàm số giải tích (`plot_math_svg.py`).

---

## 2. Cách Cài Đặt Trên Các Nền Tảng AI Agent

### A. Cài trực tiếp từ GitHub (Khuyến nghị — mọi Agent Host)
```bash
# CLI Agent Skills dùng chung (Claude Code, Cursor, Codex, Antigravity, Copilot, OpenCode)
npx skills add vietdq99tb/pro-diagrams
```

Hoặc sao chép trực tiếp thư mục `skills/pro-diagrams` từ repo:
```bash
git clone https://github.com/vietdq99tb/pro-diagrams.git
cp -r pro-diagrams/skills/pro-diagrams ~/.claude/skills/pro-diagrams      # Claude Code
# cp -r pro-diagrams/skills/pro-diagrams .agents/skills/pro-diagrams      # Cursor / Codex / Antigravity
```

### B. Cài bằng tệp gói `pro-diagrams.skill` (Claude Desktop / Windows / Offline)
Tải tệp **`pro-diagrams.skill`** tại mục [GitHub Releases](https://github.com/vietdq99tb/pro-diagrams/releases) (hoặc tự đóng gói từ thư mục `skills/pro-diagrams` bằng `zip -r pro-diagrams.skill pro-diagrams`):

- **Claude Desktop:** Tải trực tiếp tệp **`pro-diagrams.skill`** lên mục *Capabilities → Skills* trong phần cài đặt.
- **macOS / Linux (Claude Code / Cursor / Codex):**
  ```bash
  unzip pro-diagrams.skill -d ~/.claude/skills/   # hoặc .agents/skills/
  ```
- **Windows (PowerShell):**
  ```powershell
  Copy-Item pro-diagrams.skill pro-diagrams.zip
  Expand-Archive -Path pro-diagrams.zip -DestinationPath "$env:USERPROFILE\.claude\skills" -Force
  ```

---

## 3. Lệnh Kiểm Thử Nhanh Với Bộ Mẫu Có Sẵn

```bash
# Chạy toàn bộ bộ kiểm thử đơn vị + 6 ví dụ Phụ lục A–E ISO 5807:1985 + CPM / Waterfall / Math
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s skills/pro-diagrams/tests -v

# Biên dịch ngay mẫu Swimlane ISO 5807 -> .drawio + .svg + .html + SOP Runbook trong 1 lệnh
python3 skills/pro-diagrams/scripts/iso5807_builder.py \
  examples/swimlane-rd-procurement/spec.json \
  -o /tmp/procurement.drawio \
  --render-svg /tmp/procurement.svg \
  --render-html /tmp/procurement.html \
  --render-runbook /tmp/procurement_runbook.html

# Kiểm định nghiêm ngặt theo ISO 5807:1985 (§4–§11), Swimlane & WCAG AA
python3 skills/pro-diagrams/scripts/validate_iso5807.py /tmp/procurement.drawio --strict --score

# Dịch nhãn sơ đồ Việt <-> Anh giữ nguyên 100% bố cục
python3 skills/pro-diagrams/scripts/relabel.py /tmp/procurement.drawio --extract -o /tmp/labels.json
python3 skills/pro-diagrams/scripts/relabel.py /tmp/procurement.drawio --map /tmp/labels_en.json -o /tmp/procurement_en.drawio
```

---

## 4. Ghi Công & Giấy Phép

- Mã nguồn skill **`pro-diagrams`**: Giấy phép **MIT** (`LICENSE`), phát triển dựa trên lõi chuẩn từ `Agents365-ai/drawio-skill` (MIT) và kế thừa mẫu kiểm định biểu đồ/SVG từ `cathrynlavery/diagram-design` (MIT).
- Chỉ mục hình vẽ `data/shape-index.json.gz`: Giấy phép **Apache-2.0** từ `jgraph/drawio-mcp` (toàn văn giấy phép đính kèm tại `data/APACHE-2.0.txt` theo mục 4(a); chi tiết ghi công tại `data/SHAPE-INDEX-NOTICE.md`).
