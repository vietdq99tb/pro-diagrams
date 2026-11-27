# Pro. Diagrams (`pro-diagrams`) — Hướng Dẫn Cài Đặt & Sử Dụng

Skill vẽ **Lưu đồ quy trình chuẩn ISO 5807:1985**, **Swimlane / BPMN liên phòng ban**, **SOP Runbook tương tác**, **Đồ thị cấu trúc (DAG, Tree, Đường găng CPM)**, **Biểu đồ số liệu trung thực (`data-*`)** và **Đồ thị hàm số toán học ($y = f(x)$)** với bảng màu **`Atelier Technical Warm`** (`WCAG AA/AAA`) và phông chữ **`Open Sans`** hỗ trợ đầy đủ dấu tiếng Việt.

---

## 1. Kiến trúc Gói Skill (100% Python 3 Standard Library)

- **Không cần `pip install`**, không yêu cầu cài đặt Draw.io Desktop hay Graphviz mới xem được hình.
- **Khai thác thông tin thông minh (`references/discovery-and-elicitation.md`):** Tự động phân loại mức độ đầy đủ dữ kiện — vẽ ngay khi đề bài đã rõ, hoặc gom **1 vòng hỏi gọn 2–5 câu kèm gợi ý `(Khuyến nghị)`** để chọn đúng loại biểu đồ, đúng ký hiệu ISO 5807 và tuyệt đối không tự bịa số liệu thật.
- **Nhánh 1 (Quy trình & Đồ thị cấu trúc):** Biên dịch JSON → **`.drawio` XML không nén** (kéo-thả chỉnh sửa 100% trên [app.diagrams.net](https://app.diagrams.net) / VS Code) + tự động kết xuất **`.svg` độc lập** + **`.html` phóng to/thu nhỏ/tìm kiếm** + **`_runbook.html` bấm chọn từng bước** + kiểm định **11 quy tắc ISO 5807 & WCAG AA**.
- **Nhánh 2 (Số liệu & Hàm số):** Sinh **`.html` + `.svg` sạch cho PowerPoint/Word** kèm kiểm định trung thực tỷ lệ hình học `data-*` (`chart_verify.py`) và bộ vẽ hàm số giải tích (`plot_math_svg.py`).

---

## 2. Cách Cài Đặt Trên Các Nền Tảng AI Agent

### A. Antigravity
Skill đã được cài sẵn trực tiếp qua `save_skill` với tên **`pro-diagrams`**. Để cập nhật hoặc cài trên máy khác, trỏ vào thư mục `pro-diagrams/` chứa `SKILL.md`.

### B. Claude Code
```bash
# Giải nén tệp pro-diagrams.skill (định dạng ZIP) vào thư mục skills của dự án hoặc toàn cục
unzip pro-diagrams.skill -d ~/.claude/skills/
# Kết quả: ~/.claude/skills/pro-diagrams/SKILL.md
```

### C. Cursor / Codex / GitHub Copilot / OpenCode
```bash
# Giải nén vào thư mục skills chuẩn của Agent Host (ví dụ .agents/skills hoặc .cursor/skills)
unzip pro-diagrams.skill -d .agents/skills/
```

### D. Claude Desktop
Tải trực tiếp tệp **`pro-diagrams.skill`** lên mục *Capabilities → Skills* trong phần cài đặt của Claude Desktop.

---

## 3. Lệnh Kiểm Thử Nhanh

```bash
# Chạy toàn bộ bộ kiểm thử đơn vị + kiểm thử đối kháng ISO 5807 / CPM / Waterfall / Math
python3 -m unittest discover -s pro-diagrams/tests -v

# Biên dịch lưu đồ ISO 5807 + SVG + HTML + Runbook trong 1 lệnh
python3 pro-diagrams/scripts/iso5807_builder.py spec.json \
  -o flow.drawio --render-svg flow.svg --render-html flow.html --render-runbook flow_runbook.html

# Kiểm định nghiêm ngặt chuẩn ISO 5807:1985 & WCAG AA
python3 pro-diagrams/scripts/validate_iso5807.py flow.drawio --strict --score

# Dịch nhãn sơ đồ Việt <-> Anh giữ nguyên 100% bố cục
python3 pro-diagrams/scripts/relabel.py flow.drawio --extract -o labels.json
python3 pro-diagrams/scripts/relabel.py flow.drawio --map labels_en.json -o flow_en.drawio
```

---

## 4. Ghi Công & Giấy Phép

- Mã nguồn skill **`pro-diagrams`**: Giấy phép **MIT** (`LICENSE`), phát triển dựa trên lõi chuẩn từ `Agents365-ai/drawio-skill` (MIT) và kế thừa mẫu kiểm định biểu đồ/SVG từ `cathrynlavery/diagram-design` (MIT).
- Chỉ mục hình vẽ `data/shape-index.json.gz`: Giấy phép **Apache-2.0** từ `jgraph/drawio-mcp` (xem `data/SHAPE-INDEX-NOTICE.md`).
