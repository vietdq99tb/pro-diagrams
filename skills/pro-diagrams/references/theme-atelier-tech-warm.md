# Hệ Màu Chủ Đề: Atelier Technical Warm & Typography `Open Sans`

Hệ màu mặc định của `pro-diagrams` (**`tech-warm-light`** và biến thể nền tối **`tech-warm-dark`**) được phát triển chuyên biệt cho sơ đồ kỹ thuật, lưu đồ quy trình ISO 5807 và biểu đồ phân tích dữ liệu, dựa trên triết lý cân bằng cấu trúc:

> **Kim tạo cấu trúc · Hỏa tạo dấu ấn · Thổ tạo độ ấm**

---

## 1. Năm Nguyên Tắc Cốt Lõi Khi Áp Dụng Màu

1. **Kim kiến tạo khung kỷ luật (Ưu tiên #1):** Trắng tinh khiết (`#FFFFFF`), Xám Titan (`#4A5860` / `#526068`) và Đá phiến Kim–Thủy (`#2B373E`) làm khung viền chuẩn mực cho các bước xử lý (`Process`, `Predefined Process`, `Preparation`), đường luồng (`Flowline`) và hệ trục tọa độ.
2. **Hỏa tạo điểm nhớ có chủ đích (~10% diện tích):** Sắc **Gốm nung Terracotta trầm (`#AD4333` trên nền sứ hồng cực nhạt `#FDF1EE`)** chỉ tập trung vào nơi mắt người đọc cần dừng lại quyết định hoặc ghi nhớ: hình thoi `Decision`, đường găng dự án (`Critical Path`), nhánh cảnh báo ngoại lệ, và chuỗi KPI tiêu điểm trên biểu đồ. Tuyệt đối không dùng cam neon hay đỏ chói.
3. **Thổ sáng làm nền ấm (~48% nền sáng + 6% điểm ấm):** Dùng nền giấy sứ ấm **Warm Porcelain (`#F8F6F2`)** kết hợp sắc **Cát hổ phách dịu (`#8C5D2B` / nền `#FAF4EA`)** cho khối `Document`, `Manual Operation/Input`, `Delay` — xóa bỏ vẻ lạnh lẽo công nghiệp của xám Kim mà không dùng nâu đất hay vàng sậm nặng nề.
4. **Thủy hỗ trợ lưu thông dữ liệu:** Sắc **Xanh khoáng Kim–Thủy (`#395E73` / nền `#EDF3F6`)** đại diện cho các khối dữ liệu luân chuyển (`Data I/O`, `Database`, `Stored Data`, `Display`) và chuỗi so sánh thứ hai trên biểu đồ.
5. **Tiết chế Mộc tuyệt đối:** Không dùng xanh lá làm màu nhận diện chủ đạo hay tô nút `Start`/`Process` theo lối mòn đèn giao thông. Sắc **Ngọc khoáng trầm (`#2D6A5B` / nền `#EEF4F1`)** chỉ xuất hiện hạn chế khi biểu đồ thống kê cần chỉ báo biến động dương (`+Δ`) hoặc phân biệt đến chuỗi thứ 6.

---

## 2. Bảng Mã Màu Đã Chuẩn Hóa Toán Học WCAG AA / AAA (`tech-warm-light`)

Mọi cặp màu chữ/nền đều đạt tương phản **≥ 13.9:1 (WCAG AAA)**, mọi đường viền/màu nhấn ngữ nghĩa của 7 slot nút đều đạt **≥ 5.2:1 (WCAG AA)** so với nền giấy ấm `#F8F6F2` và nền trắng `#FFFFFF`, và cả 6 màu chuỗi biểu đồ (`chart_series`) đều đạt **≥ 4.5:1 (WCAG AA)** (riêng đường kẻ phụ trang trí `border_subtle #C9D2D8` và lưới nền `grid_line #DCE2E6` không dùng cho chữ hay tín hiệu ngữ nghĩa):

| Vai trò ngữ nghĩa (Slot) | Nền hộp (`fillColor`) | Viền / Nhấn (`strokeColor`) | Chữ (`fontColor`) | Tương phản Chữ | Ánh xạ ISO 5807 & Đồ thị |
|---|---|---|---|---:|---|
| **Canvas / Paper** | `#F8F6F2` / `#FFFFFF` | `#C9D2D8` *(kẻ phụ trang trí)* | `#1C2327` | `14.75:1` | Nền trang sơ đồ, nền khung biểu đồ |
| **`neutral` (Kim chuẩn)** | `#FFFFFF` | `#4A5860` | `#1C2327` | `15.92:1` | `Process`, `Preparation`, `Loop Limit`, `Annotation` |
| **`primary` (Kim–Thủy)** | `#EEF2F5` | `#2B373E` | `#1C2327` | `14.14:1` | `Terminator` (Start/End), `Predefined Process`, `Connector`, `Parallel Mode` |
| **`accent` (Hỏa điểm nhớ)** | `#FDF1EE` | `#AD4333` | `#1C2327` | `14.40:1` | `Decision` (Hình thoi), Đường găng CPM (`TF=0`), KPI tiêu điểm |
| **`secondary` (Thủy dữ liệu)** | `#EDF3F6` | `#395E73` | `#1C2327` | `14.22:1` | `Data I/O`, `Database`, `Direct/Stored/Sequential/Internal Storage`, `Display` |
| **`warning` (Thổ ấm)** | `#FAF4EA` | `#8C5D2B` | `#1C2327` | `14.55:1` | `Document`, `Multi-Document`, `Manual Operation`, `Manual Input`, `Delay` |
| **`danger` (Cảnh báo lỗi)** | `#FCECEB` | `#9E2F2C` | `#1C2327` | `13.90:1` | Nút dừng khẩn cấp, nhánh lỗi nghiêm trọng |
| **`success` (Ngọc khoáng)** | `#EEF4F1` | `#2D6A5B` | `#1C2327` | `14.29:1` | Chỉ báo `+Δ` biểu đồ số liệu hoặc trạng thái nghiệm thu đặc biệt |

**Chuỗi 6 màu cho Biểu đồ Số liệu & Hàm số (`chart_series`):**
1. `#AD4333` — Kiln Terracotta *(KPI tiêu điểm / hàm chính)*
2. `#2B373E` — Structural Slate *(Thực tế / nền tảng đối chiếu)*
3. `#395E73` — Mineral Water *(Luồng dữ liệu / chuỗi 3)*
4. `#8C5D2B` — Burnished Sand *(Cơ cấu tài nguyên / chuỗi 4)*
5. `#64737C` — Titanium Steel *(Tham chiếu / kỳ trước)*
6. `#2D6A5B` — Mineral Sage *(Biến động dương / chuỗi 6)*

*(Biến thể nền tối `tech-warm-dark` trên nền `#161C20`, chữ `#F4F2EE` được định nghĩa đầy đủ trong `styles/built-in/tech-warm-dark.json` và `data/theme-tokens.json`.)*

---

## 3. Quy Tắc Typography Tiếng Việt Với Phông Chữ `Open Sans`

- **Phông chữ bắt buộc:** `'Open Sans', 'Segoe UI', Roboto, Arial, sans-serif` (cỡ chữ nút `12px`, tiêu đề làn `13–14px` đậm, tiêu đề bản vẽ `16–22px` đậm). Số liệu trục & công thức dùng `'JetBrains Mono', monospace`.
- **Bảo vệ dấu thanh chồng tiếng Việt (`ệ, ổ, ữ, ắ, ẫ`):**
  - Chiều cao hộp tối thiểu **≥ 60px** (1–2 dòng) và **≥ 76px** (3 dòng); `spacingTop=6;spacingBottom=6;spacingLeft=8;spacingRight=8;`.
  - Trong HTML/SVG dùng `line-height >= 1.4` và bọc nhãn mũi tên bằng nền đục (`labelBackgroundColor=#F8F6F2`) để đường nối không cắt ngang dấu tiếng Việt.
  - Nhãn nút ngắn gọn bắt đầu bằng động từ (2–6 từ); nhãn nhánh `Decision` súc tích **≤ 18 ký tự** (`Có` / `Không`, `Đạt` / `Thử lại`).
- **Tùy biến bảng màu khác khi người dùng yêu cầu:** Dùng `python3 <skill-dir>/scripts/restyle.py diagram.drawio --preset <preset_or_json_path>` để đổi sang bất kỳ preset nào (`tech-warm-light`, `tech-warm-dark`, `colorblind-safe`, `handdrawn`, hoặc tệp JSON tùy chỉnh tuân thủ `styles/schema.json`).
