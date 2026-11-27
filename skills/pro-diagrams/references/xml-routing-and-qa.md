# Quy Tắc XML `.drawio` Thủ Công, Định Tuyến Đường Nối & Kiểm Tra Thị Giác

Khi bạn cần chỉnh sửa trực tiếp tệp `.drawio` hoặc vẽ sơ đồ tùy biến vượt ngoài JSON spec của `iso5807_builder.py`, hãy tuân thủ các quy tắc dưới đây.

---

## 1. Quy Tắc Bất Biến Trong `.drawio` XML

1. **Luôn lưu XML không nén** (`<mxGraphModel>` nằm trực tiếp bên trong `<diagram>`) để Git diff được và mọi script `validate.py`, `edgeports.py`, `relabel.py`, `restyle.py` đọc được trực tiếp.
2. **ID dành riêng:** Luôn khai báo `<mxCell id="0"/>` và `<mxCell id="1" parent="0"/>`; mọi đỉnh/cạnh khác phải dùng ID duy nhất khác `"0"` và `"1"`.
3. **Cạm bẫy Python `ElementTree`:** Khi tạo `<mxGeometry>` hoặc `<Array>` bằng Python `ET`, truyền `attrib={"as": "geometry"}` hoặc `attrib={"as": "points"}` — tuyệt đối không viết keyword `as_="geometry"` (gây lỗi `E-AS-LEAK`).
4. **Tọa độ tương đối trong Swimlane:** Mọi nút có `parent="<lane_id>"` lưu tọa độ `(x, y)` **tương đối so với góc trên-trái của làn đó**, trong khi các cạnh nối xuyên làn nên đặt `parent="1"` ở cấp trang với tọa độ waypoint tuyệt đối.
5. **Bắt buộc `whiteSpace=wrap;html=1;` trên mọi hộp có chữ** để chữ tiếng Việt tự xuống dòng mà không tràn khỏi biên hình học.

---

## 2. Sáu Quy Tắc Đường Nối Chuẩn Mực

1. **Chỉ dùng đường gấp khúc vuông góc có bo góc nhẹ** (`edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow=block;endFill=1;endSize=7;`).
2. **Rải đều cổng khi ≥ 2 cạnh cùng vào/ra một mặt hộp:** Chạy `python3 <skill-dir>/scripts/edgeports.py diagram.drawio` sau khi sửa XML thủ công để tự động rải đều `exitX/exitY` và `entryX/entryY` theo thứ tự không cắt chéo.
3. **Lối thoát Hình thoi Quyết định (`Decision`):** Nhánh khẳng định (`Có` / `Đạt`) đi tiếp theo trục chính (`exitX=0.5;exitY=1` với TB, `exitX=1;exitY=0.5` với LR); nhánh phủ định/ngoại lệ (`Không` / `Lỗi`) rẽ ngang qua đỉnh bên (`exitX=1;exitY=0.5` hoặc `exitX=0;exitY=0.5`).
4. **Hành lang biên ngoài cho vòng lặp quay lui:** Mọi cạnh đi ngược chiều chủ đạo (thử lại / trả hồ sơ) phải đi vòng qua hành lang biên ngoài cách mép sơ đồ ≥ 50–80px bằng `<Array as="points">`.
5. **Không cắt xuyên qua hộp trung gian (`W-EDGE-THROUGH-VERTEX`) và không chạy trùng lên vạch biên Swimlane (`W-ISO-SWIMLANE-CROSS`).**
6. **Nền đục cho nhãn mũi tên:** Đặt `labelBackgroundColor=#F8F6F2` (hoặc `#161C20` ở chế độ tối) để nét kẻ không cắt ngang chữ và dấu tiếng Việt.

---

## 3. Quy Trình Kiểm Tra Thị Giác (Render-and-Look 8 Điểm)

Sau khi sinh `.svg` / `.html` (hoặc `.png` qua `--png` khi có Chrome / Draw.io CLI), kiểm tra nhanh 8 lỗi thị giác phổ biến trước khi bàn giao:
1. Chữ tiếng Việt có dấu chồng (`ệ, ổ, ữ`) có bị sát mép trên/dưới của hình thoi hoặc hình trụ không?
2. Có nhánh `Decision` nào bị thiếu nhãn hoặc nhãn đè lên đỉnh hình thoi không?
3. Có hai nhãn mũi tên nào đè lên nhau ở điểm giao không?
4. Các cặp `On-Page Connector` (`A` → `A`) đã rõ chiều mũi tên vào/ra chưa?
5. Màu sắc đã tuân thủ tỷ lệ **Atelier Technical Warm** (nền ấm thoáng, khung Kim sắc nét, điểm nhấn Terracotta đúng chỗ, không lạm dụng xanh lá) chưa?
6. Mọi đường vòng lặp quay lui đã đi gọn ngoài hành lang biên chưa?
7. Tiêu đề bản vẽ, phụ đề và đơn vị đo (nếu là biểu đồ/CPM) đã đầy đủ chưa?
8. Cả tệp gốc chỉnh sửa được (`.drawio` / `.html`) và tệp xem/nhúng ngay (`.svg`) đều đã được lưu và kiểm định `0 error` chưa?
