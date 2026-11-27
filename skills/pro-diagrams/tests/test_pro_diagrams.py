#!/usr/bin/env python3
"""Comprehensive stdlib unit, CLI, WCAG & adversarial regression suite for `pro-diagrams`.

Covers all 20 shipped scripts under `scripts/`, design-system WCAG 2.1 tokens &
secondary presets, strict ISO 5807:1985 & Swimlane routing, CPM calculation,
Track B statistical charts + adversarial honesty verification, mathematical
function plotting, error-handling hygiene, and stdlib/path portability.
"""
import ast
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import autolayout
import chart_verify
import diagram_ir
import iso5807_builder
import plot_math_svg
import validate_iso5807

EXPECTED_SCRIPTS = {
    "autolayout.py",
    "chart_builder.py",
    "chart_verify.py",
    "diagram_ir.py",
    "drawio2mermaid.py",
    "drawio_cli.py",
    "drawio_render_svg.py",
    "drawiohtml.py",
    "edgeports.py",
    "encode_drawio_url.py",
    "explain.py",
    "iso5807_builder.py",
    "plot_math_svg.py",
    "relabel.py",
    "repair_png.py",
    "restyle.py",
    "runbook.py",
    "shapesearch.py",
    "validate.py",
    "validate_iso5807.py",
}


def _run_script(script_name, args, cwd, env_override=None):
    """Run a shipped script from an external CWD with bytecode disabled."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_override:
        env.update(env_override)
    cmd = [sys.executable, "-B", os.path.join(SCRIPTS_DIR, script_name)] + list(args)
    return subprocess.run(cmd, check=False, cwd=cwd, env=env, capture_output=True, text=True)


def _extract_first_json_fence(md_path):
    """Extract the first ```json ... ``` fenced block from a Markdown reference."""
    with open(md_path, encoding="utf-8") as fh:
        content = fh.read()
    m = re.search(r"```json\s*\n(.*?)\n```", content, flags=re.DOTALL)
    if not m:
        raise AssertionError(f"No ```json fenced block found in {md_path}")
    return json.loads(m.group(1))


def _extract_style_key(style, key):
    m = re.search(rf"(?:^|;){re.escape(key)}=([^;]*)", style or "")
    return m.group(1) if m else None


def _eval1_payment_retry_spec(with_hints=True):
    nodes = [
        {"id": "start", "type": "terminator", "label": "Bắt đầu", "rank": 0, "col": 0},
        {"id": "input_order", "type": "data", "label": "Nhập thông tin đơn hàng &\nphương thức thanh toán", "rank": 1, "col": 0},
        {"id": "init_k", "type": "preparation", "label": "Khởi tạo biến đếm\nthử lại k = 0", "rank": 2, "col": 0},
        {"id": "call_gateway", "type": "predefined_process", "label": "Gọi dịch vụ cổng\nthanh toán định sẵn", "rank": 3, "col": 0},
        {"id": "dec_tx_ok", "type": "decision", "label": "Giao dịch\nthành công?", "rank": 4, "col": 0},
        {"id": "save_db", "type": "database", "label": "Ghi giao dịch vào\ncơ sở dữ liệu", "rank": 5, "col": 0},
        {"id": "issue_invoice", "type": "document", "label": "Xuất hóa đơn điện tử\n(chứng từ)", "rank": 6, "col": 0},
        {"id": "inc_k", "type": "process", "label": "Tăng biến đếm\nk = k + 1", "rank": 5, "col": 1.8},
        {"id": "dec_k_lt_3", "type": "decision", "label": "Kiểm tra\nk < 3?", "rank": 6, "col": 1.8},
        {"id": "wait_5s", "type": "delay", "label": "Chờ 5 giây", "rank": 7, "col": 1.8},
        {"id": "show_error", "type": "display", "label": "Hiển thị thông báo lỗi\nlên màn hình", "rank": 7, "col": 0.85},
        {"id": "conn_a_in", "type": "on_page_connector", "label": "A", "rank": 8, "col": 0.85},
        {"id": "conn_a_out", "type": "on_page_connector", "label": "A", "rank": 8, "col": -0.55},
        {"id": "end", "type": "terminator", "label": "Kết thúc", "rank": 9, "col": 0},
        {"id": "note_sla", "type": "annotation", "attach_to": "call_gateway", "label": "SLA cổng thanh toán <= 3 giây"},
    ]
    if not with_hints:
        nodes = [{k: v for k, v in n.items() if k not in ("rank", "col")} for n in nodes]
    return {
        "kind": "iso5807-flowchart",
        "direction": "TB",
        "title": "Lưu đồ Xử lý Thanh toán & Xuất Hóa đơn Điện tử",
        "subtitle": "Chuẩn ISO 5807:1985 · Cơ chế thử lại (k < 3, SLA <= 3 giây)",
        "nodes": nodes,
        "edges": [
            {"id": "e_start_input", "from": "start", "to": "input_order"},
            {"id": "e_input_init", "from": "input_order", "to": "init_k"},
            {"id": "e_init_call", "from": "init_k", "to": "call_gateway"},
            {"id": "e_call_dec", "from": "call_gateway", "to": "dec_tx_ok"},
            {"id": "e_tx_yes", "from": "dec_tx_ok", "to": "save_db", "label": "Có"},
            {"id": "e_tx_no", "from": "dec_tx_ok", "to": "inc_k", "label": "Không", "role": "error"},
            {"id": "e_db_inv", "from": "save_db", "to": "issue_invoice"},
            {"id": "e_inv_end", "from": "issue_invoice", "to": "end"},
            {"id": "e_inc_check", "from": "inc_k", "to": "dec_k_lt_3"},
            {"id": "e_retry_yes", "from": "dec_k_lt_3", "to": "wait_5s", "label": "Có"},
            {"id": "e_wait_loop", "from": "wait_5s", "to": "call_gateway", "label": "Thử lại"},
            {"id": "e_retry_no", "from": "dec_k_lt_3", "to": "show_error", "label": "Không", "role": "error"},
            {"id": "e_err_conna", "from": "show_error", "to": "conn_a_in", "role": "error"},
            {"id": "e_conna_end", "from": "conn_a_out", "to": "end"},
        ],
    }


def _eval2_rd_procurement_swimlane_spec(direction="TB"):
    return {
        "kind": "swimlane",
        "direction": direction,
        "pool_title": "QUY TRÌNH ĐỀ XUẤT VÀ PHÊ DUYỆT MUA SẮM THIẾT BỊ R&D",
        "title": "Sơ đồ Liên phòng ban: Mua sắm Thiết bị R&D",
        "subtitle": "SOP-RD-PROC-01 · Chuẩn ISO 5807:1985 · 4 phòng ban",
        "dash_back_edges": True,
        "lanes": [
            {"id": "rd", "title": "Bộ phận R&D"},
            {"id": "proc", "title": "Phòng Mua hàng"},
            {"id": "fin", "title": "Phòng Tài chính - Kế toán"},
            {"id": "dir", "title": "Ban Giám đốc"},
        ],
        "nodes": [
            {"id": "s_start", "lane": "rd", "type": "terminator", "label": "Bắt đầu nhu cầu R&D"},
            {"id": "n_pr_input", "lane": "rd", "type": "manual_input", "label": "Nhập phiếu đề xuất PR & thông số"},
            {"id": "n_quotes_doc", "lane": "proc", "type": "multi_document", "label": "Thu thập tối thiểu 3 báo giá NCC"},
            {"id": "n_vendor_eval", "lane": "proc", "type": "manual_operation", "label": "Chấm điểm và chọn nhà cung cấp"},
            {"id": "n_budget_sys", "lane": "fin", "type": "predefined_process", "label": "Kiểm tra hạn mức & khóa dự toán"},
            {"id": "d_budget", "lane": "fin", "type": "decision", "label": "Ngân sách <= 100 triệu?"},
            {"id": "n_dir_review", "lane": "dir", "type": "manual_operation", "label": "Thẩm định hiệu quả đầu tư R&D"},
            {"id": "d_dir_approve", "lane": "dir", "type": "decision", "label": "Phê duyệt chủ trương?"},
            {"id": "e_reject", "lane": "dir", "type": "terminator", "label": "Từ chối đầu tư & đóng PR"},
            {"id": "n_contract_po", "lane": "proc", "type": "document", "label": "Xuất hợp đồng & đơn đặt hàng PO"},
            {"id": "n_tech_test", "lane": "rd", "type": "manual_operation", "label": "Lắp đặt chạy thử & kiểm định"},
            {"id": "d_tech_accept", "lane": "rd", "type": "decision", "label": "Nghiệm thu đạt yêu cầu?"},
            {"id": "n_vendor_fix", "lane": "proc", "type": "manual_operation", "label": "Yêu cầu NCC hiệu chỉnh thiết bị"},
            {"id": "n_accept_doc", "lane": "rd", "type": "document", "label": "Lập biên bản nghiệm thu bàn giao"},
            {"id": "n_erp_db", "lane": "fin", "type": "database", "label": "Ghi nhận tài sản & công nợ ERP"},
            {"id": "n_payment_sys", "lane": "fin", "type": "process", "label": "Đối chiếu ba bên và giải ngân"},
            {"id": "e_end", "lane": "fin", "type": "terminator", "label": "Hoàn tất mua sắm R&D"},
        ],
        "edges": [
            {"from": "s_start", "to": "n_pr_input"},
            {"from": "n_pr_input", "to": "n_quotes_doc"},
            {"from": "n_quotes_doc", "to": "n_vendor_eval"},
            {"from": "n_vendor_eval", "to": "n_budget_sys"},
            {"from": "n_budget_sys", "to": "d_budget"},
            {"from": "d_budget", "to": "n_contract_po", "label": "Có (<= 100tr)"},
            {"from": "d_budget", "to": "n_dir_review", "label": "Không (> 100tr)"},
            {"from": "n_dir_review", "to": "d_dir_approve"},
            {"from": "d_dir_approve", "to": "n_contract_po", "label": "Đồng ý duyệt"},
            {"from": "d_dir_approve", "to": "e_reject", "label": "Từ chối duyệt", "role": "error"},
            {"from": "n_contract_po", "to": "n_tech_test"},
            {"from": "n_tech_test", "to": "d_tech_accept"},
            {"from": "d_tech_accept", "to": "n_accept_doc", "label": "Đạt yêu cầu"},
            {"from": "d_tech_accept", "to": "n_vendor_fix", "label": "Không đạt", "role": "error"},
            {"from": "n_vendor_fix", "to": "n_tech_test", "label": "Kiểm định lại", "role": "error"},
            {"from": "n_accept_doc", "to": "n_erp_db"},
            {"from": "n_erp_db", "to": "n_payment_sys"},
            {"from": "n_payment_sys", "to": "e_end"},
        ],
    }


def _eval3_cpm_spec():
    return {
        "kind": "cpm",
        "direction": "LR",
        "title": "Đồ thị Mạng Phụ thuộc & Đường găng (CPM) — Nâng cấp Nền tảng Dữ liệu",
        "nodes": [
            {"id": "A", "label": "A — Khảo sát", "duration": 3},
            {"id": "B", "label": "B — Thiết kế kiến trúc", "duration": 4},
            {"id": "C", "label": "C — Chuẩn bị hạ tầng", "duration": 2},
            {"id": "D", "label": "D — Xây dựng pipeline lõi", "duration": 6},
            {"id": "E", "label": "E — Thiết lập bảo mật", "duration": 4},
            {"id": "F", "label": "F — Kiểm thử tích hợp", "duration": 3},
            {"id": "G", "label": "G — Chuyển giao vận hành", "duration": 2},
        ],
        "edges": [
            {"from": "A", "to": "B"},
            {"from": "A", "to": "C"},
            {"from": "B", "to": "D"},
            {"from": "C", "to": "E"},
            {"from": "D", "to": "F"},
            {"from": "E", "to": "F"},
            {"from": "F", "to": "G"},
        ],
    }


class TestTrackAISO5807SwimlaneCPM(unittest.TestCase):
    """Track A core builder & strict validator tests (iso5807_builder, validate_iso5807, validate)."""

    def test_verbatim_reference_swimlane_tb_lr_and_duplicate_id_rejection(self):
        ref_path = os.path.join(SKILL_DIR, "references", "swimlane-and-sop.md")
        ref_spec = _extract_first_json_fence(ref_path)
        self.assertTrue(any(n.get("id") == "e1" for n in ref_spec["nodes"]), "Expected node id='e1' in reference JSON")

        with tempfile.TemporaryDirectory() as tmp:
            for direction in ("TB", "LR"):
                spec = dict(ref_spec, direction=direction)
                spec_path = os.path.join(tmp, f"ref_swim_{direction}.json")
                out_drawio = os.path.join(tmp, f"ref_swim_{direction}.drawio")
                with open(spec_path, "w", encoding="utf-8") as fh:
                    json.dump(spec, fh, ensure_ascii=False)

                r_build = _run_script("iso5807_builder.py", [spec_path, "-o", out_drawio], cwd=tmp)
                self.assertEqual(r_build.returncode, 0, f"{direction} build failed: {r_build.stderr}")

                r_val = _run_script("validate_iso5807.py", [out_drawio, "--strict", "--score", "--json"], cwd=tmp)
                self.assertEqual(r_val.returncode, 0, f"{direction} strict validate failed: {r_val.stdout}\n{r_val.stderr}")
                rep = json.loads(r_val.stdout)
                self.assertTrue(rep["iso_compliant"])
                self.assertEqual(rep["errors"], 0, rep["diagnostics"])
                self.assertEqual(rep["warnings"], 0, rep["diagnostics"])
                self.assertEqual(rep["readability_score"], 0, rep)

                # Verify terminator height >= 60px
                root = ET.parse(out_drawio).getroot()
                term_heights = []
                for cell in root.iter("mxCell"):
                    if "mxgraph.flowchart.terminator" in (cell.get("style") or ""):
                        geom = cell.find("mxGeometry")
                        self.assertIsNotNone(geom)
                        term_heights.append(float(geom.get("height", "0")))
                self.assertGreaterEqual(len(term_heights), 2)
                for h in term_heights:
                    self.assertGreaterEqual(h, 60.0, f"Terminator height {h} < 60px")

            # Explicit duplicate node ID rejected cleanly without traceback
            dup_spec = {
                "kind": "iso5807-flowchart",
                "nodes": [
                    {"id": "dup1", "type": "terminator", "label": "Bắt đầu"},
                    {"id": "dup1", "type": "terminator", "label": "Kết thúc"},
                ],
                "edges": [],
            }
            dup_path = os.path.join(tmp, "dup.json")
            with open(dup_path, "w", encoding="utf-8") as fh:
                json.dump(dup_spec, fh)
            r_dup = _run_script("iso5807_builder.py", [dup_path, "-o", os.path.join(tmp, "dup.drawio")], cwd=tmp)
            self.assertNotEqual(r_dup.returncode, 0)
            self.assertNotIn("Traceback", r_dup.stderr + r_dup.stdout)

    def test_eval1_payment_retry_flowchart_strict_zero_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            for variant, with_hints in (("hints", True), ("auto", False)):
                spec_path = os.path.join(tmp, f"eval1_{variant}.json")
                out_drawio = os.path.join(tmp, f"eval1_{variant}.drawio")
                with open(spec_path, "w", encoding="utf-8") as fh:
                    json.dump(_eval1_payment_retry_spec(with_hints=with_hints), fh, ensure_ascii=False)

                r_build = _run_script("iso5807_builder.py", [spec_path, "-o", out_drawio], cwd=tmp)
                self.assertEqual(r_build.returncode, 0, r_build.stderr)

                r_val = _run_script("validate_iso5807.py", [out_drawio, "--strict", "--score", "--json"], cwd=tmp)
                self.assertEqual(r_val.returncode, 0, f"{variant} strict failed: {r_val.stdout}\n{r_val.stderr}")
                rep = json.loads(r_val.stdout)
                self.assertTrue(rep["iso_compliant"])
                self.assertEqual(rep["errors"], 0)
                self.assertEqual(rep["warnings"], 0)
                self.assertEqual(rep["readability_score"], 0)

    def test_eval2_four_lane_procurement_swimlane_tb_lr_and_runbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            for direction in ("TB", "LR"):
                spec_path = os.path.join(tmp, f"eval2_{direction}.json")
                out_drawio = os.path.join(tmp, f"eval2_{direction}.drawio")
                out_svg = os.path.join(tmp, f"eval2_{direction}.svg")
                out_html = os.path.join(tmp, f"eval2_{direction}.html")
                out_rb = os.path.join(tmp, f"eval2_{direction}_runbook.html")
                with open(spec_path, "w", encoding="utf-8") as fh:
                    json.dump(_eval2_rd_procurement_swimlane_spec(direction=direction), fh, ensure_ascii=False)

                r_build = _run_script(
                    "iso5807_builder.py",
                    [spec_path, "-o", out_drawio, "--render-svg", out_svg, "--render-html", out_html, "--render-runbook", out_rb],
                    cwd=tmp,
                )
                self.assertEqual(r_build.returncode, 0, f"{direction}: {r_build.stderr}")

                r_val = _run_script("validate_iso5807.py", [out_drawio, "--strict", "--score", "--json"], cwd=tmp)
                self.assertEqual(r_val.returncode, 0, f"{direction} strict failed: {r_val.stdout}\n{r_val.stderr}")
                rep = json.loads(r_val.stdout)
                self.assertEqual(rep["errors"], 0)
                self.assertEqual(rep["warnings"], 0)
                self.assertEqual(rep["readability_score"], 0)

                ET.parse(out_svg)
                self.assertTrue(os.path.isfile(out_html))
                with open(out_rb, encoding="utf-8") as fh:
                    rb_html = fh.read()
                m = re.search(r"const DATA=(\{.*?\});", rb_html)
                self.assertIsNotNone(m, "Runbook missing embedded DATA JSON")
                rb_data = json.loads(m.group(1))
                self.assertEqual(rb_data["start"], "s_start")
                self.assertEqual(rb_data["nodes"]["s_start"].get("lane"), "Bộ phận R&D")
                self.assertIn("Quay lại", rb_html)

    def test_eval3_cpm_network_light_and_dark_themes(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "cpm.json")
            with open(spec_path, "w", encoding="utf-8") as fh:
                json.dump(_eval3_cpm_spec(), fh, ensure_ascii=False)

            for preset, expected_crit, forbidden_sub in (
                ("tech-warm-light", "#AD4333", None),
                ("tech-warm-dark", "#E07A68", "#AD4333"),
            ):
                out_drawio = os.path.join(tmp, f"cpm_{preset}.drawio")
                r_build = _run_script("iso5807_builder.py", [spec_path, "--preset", preset, "-o", out_drawio], cwd=tmp)
                self.assertEqual(r_build.returncode, 0, r_build.stderr)

                with open(out_drawio, encoding="utf-8") as fh:
                    xml_txt = fh.read()
                self.assertIn("18 ngày", xml_txt)
                self.assertIn("TF=0", xml_txt)
                self.assertIn("TF=4", xml_txt)
                self.assertIn("LS=7→LF=9", xml_txt)
                self.assertIn("LS=9→LF=13", xml_txt)
                self.assertIn(expected_crit, xml_txt)
                if forbidden_sub:
                    # Subtitle banner in dark mode must use #E07A68, never light #AD4333
                    root = ET.parse(out_drawio).getroot()
                    title_cell = next(c for c in root.iter("mxCell") if c.get("id") == "title_banner")
                    self.assertIn("#E07A68", title_cell.get("value", ""))
                    self.assertNotIn(forbidden_sub, title_cell.get("value", ""))

                r_val = _run_script("validate.py", [out_drawio, "--strict", "--score"], cwd=tmp)
                self.assertEqual(r_val.returncode, 0, f"{preset} validate failed: {r_val.stdout}\n{r_val.stderr}")
                self.assertIn("score: 0", r_val.stdout)

    def test_all_26_iso5807_symbols_strict_zero_score(self):
        with open(os.path.join(SKILL_DIR, "data", "iso5807-shapes.json"), encoding="utf-8") as fh:
            catalog = json.load(fh)
        symbols = catalog["symbols"]
        self.assertEqual(len(symbols), 26, "Expected exactly 26 ISO 5807 + extended symbols in catalog")
        self.assertEqual(symbols["card"]["iso_section"], "ISO 5807:1985 §9.1.2.6")
        self.assertEqual(symbols["paper_tape"]["iso_section"], "ISO 5807:1985 §9.1.2.7")
        self.assertEqual(symbols["ellipsis"]["iso_section"], "ISO 5807:1985 §9.4.4")

        # Build a valid ISO 5807 flowchart exercising all 26 symbol types
        seq_types = [
            "data", "preparation", "predefined_process", "process", "document",
            "multi_document", "database", "direct_data", "stored_data",
            "sequential_data", "internal_storage", "card", "paper_tape",
            "manual_operation", "manual_input", "loop_limit_start", "delay",
            "display", "parallel_mode", "ellipsis", "loop_limit_end",
            "off_page_connector",
        ]
        nodes = [{"id": "n_start", "type": "terminator", "label": "Bắt đầu 26 ký hiệu"}]
        edges = []
        prev = "n_start"
        for idx, stype in enumerate(seq_types):
            nid = f"sym_{idx}_{stype}"
            if stype in ("loop_limit_start", "loop_limit_end"):
                nodes.append({"id": nid, "type": stype, "label": "Lặp kiểm tra", "loop_id": "L_ALL"})
            elif stype == "ellipsis":
                nodes.append({"id": nid, "type": stype, "label": "..."})
            else:
                nodes.append({"id": nid, "type": stype, "label": f"Bước {stype}"})
            edges.append({"from": prev, "to": nid})
            prev = nid
        nodes.extend([
            {"id": "dec_final", "type": "decision", "label": "Hoàn tất hợp lệ?"},
            {"id": "conn_in", "type": "on_page_connector", "label": "A"},
            {"id": "conn_out", "type": "on_page_connector", "label": "A"},
            {"id": "n_end", "type": "terminator", "label": "Kết thúc"},
            {"id": "note_all", "type": "annotation", "attach_to": "sym_3_process", "label": "Đầy đủ 26 ký hiệu ISO 5807"},
        ])
        edges.extend([
            {"from": prev, "to": "dec_final"},
            {"from": "dec_final", "to": "n_end", "label": "Có"},
            {"from": "dec_final", "to": "conn_in", "label": "Không", "role": "error"},
            {"from": "conn_out", "to": "n_end"},
        ])
        used_types = {n["type"] for n in nodes}
        self.assertEqual(used_types, set(symbols.keys()))

        spec = {"kind": "iso5807-flowchart", "direction": "TB", "title": "Kiểm thử Đủ 26 Ký hiệu ISO 5807", "nodes": nodes, "edges": edges}
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "all26.json")
            out_drawio = os.path.join(tmp, "all26.drawio")
            out_svg = os.path.join(tmp, "all26.svg")
            with open(spec_path, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)
            r_build = _run_script("iso5807_builder.py", [spec_path, "-o", out_drawio, "--render-svg", out_svg], cwd=tmp)
            self.assertEqual(r_build.returncode, 0, r_build.stderr)

            r_val = _run_script("validate_iso5807.py", [out_drawio, "--strict", "--score", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 0, f"all26 strict failed: {r_val.stdout}\n{r_val.stderr}")
            rep = json.loads(r_val.stdout)
            self.assertTrue(rep["iso_compliant"])
            self.assertEqual(rep["errors"], 0)
            self.assertEqual(rep["warnings"], 0)
            self.assertEqual(rep["readability_score"], 0)

            with open(out_svg, encoding="utf-8") as sf:
                svg_txt = sf.read()
            for expected_shape in ('data-shape="card"', 'data-shape="paper_tape"', 'data-shape="ellipsis"'):
                self.assertIn(expected_shape, svg_txt)

    def test_custom_preset_path_and_unknown_preset_rejection(self):
        spec = {
            "kind": "iso5807-flowchart",
            "nodes": [
                {"id": "s", "type": "terminator", "label": "Bắt đầu"},
                {"id": "p", "type": "process", "label": "Xử lý"},
                {"id": "e", "type": "terminator", "label": "Kết thúc"},
            ],
            "edges": [{"from": "s", "to": "p"}, {"from": "p", "to": "e"}],
        }
        dark_preset_path = os.path.join(SKILL_DIR, "styles", "built-in", "tech-warm-dark.json")
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "mini.json")
            out_dark = os.path.join(tmp, "mini_dark.drawio")
            with open(spec_path, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)

            r_ok = _run_script("iso5807_builder.py", [spec_path, "--preset", dark_preset_path, "-o", out_dark], cwd=tmp)
            self.assertEqual(r_ok.returncode, 0, r_ok.stderr)
            with open(out_dark, encoding="utf-8") as fh:
                self.assertIn('background="#161C20"', fh.read())

            r_bad = _run_script("iso5807_builder.py", [spec_path, "--preset", "nonexistent-preset", "-o", os.path.join(tmp, "bad.drawio")], cwd=tmp)
            self.assertNotEqual(r_bad.returncode, 0)
            self.assertNotIn("Traceback", r_bad.stderr + r_bad.stdout)

    def test_adversarial_iso5807_and_distinct_supported_fixes(self):
        bad_spec = {
            "kind": "iso5807-flowchart",
            "nodes": [
                {"id": "p1", "type": "process", "label": "Không có Start"},
                {"id": "d1", "type": "decision", "label": "Thiếu 2 nhãn nhánh?"},
                {"id": "d2", "type": "decision", "label": "Thiếu 1 nhánh ra?"},
                {"id": "c1", "type": "on_page_connector", "label": "X"},
                {"id": "orphan", "type": "process", "label": "Nút mồ côi"},
            ],
            "edges": [
                {"id": "e0", "from": "p1", "to": "d1"},
                {"id": "ed1", "from": "d1", "to": "d2", "label": ""},
                {"id": "ed2", "from": "d1", "to": "c1", "label": ""},
                {"id": "ed3", "from": "d2", "to": "c1", "label": "Có"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = os.path.join(tmp, "bad.drawio")
            iso5807_builder.compile_spec_to_drawio(bad_spec).write(bad_path, encoding="utf-8")
            rep = validate_iso5807.build_structured_report(bad_path, strict=False)
            codes = {d["code"] for d in rep["diagnostics"]}
            self.assertFalse(rep["iso_compliant"])
            self.assertIn("E-ISO-START", codes)
            self.assertIn("E-ISO-END", codes)
            self.assertIn("E-ISO-DECISION-LABEL", codes)
            self.assertIn("E-ISO-CONNECTOR-PAIR", codes)
            self.assertIn("W-ISO-ORPHAN", codes)
            self.assertIn("W-DECISION-EXIT", codes)

            # Distinct supportedFixes entries for both unlabeled decision edges ed1 & ed2
            label_fixes = [f for f in rep["supportedFixes"] if f["code"] == "E-ISO-DECISION-LABEL"]
            targets = [f["target"] for f in label_fixes]
            self.assertIn("ed1", targets)
            self.assertIn("ed2", targets)
            self.assertEqual(len(targets), len(set(targets)))

    def test_malformed_spec_rejections_type_edge_lane_attach_slot_kind_direction(self):
        base_nodes = [
            {"id": "s", "type": "terminator", "label": "Bắt đầu"},
            {"id": "p", "type": "process", "label": "Xử lý"},
            {"id": "e", "type": "terminator", "label": "Kết thúc"},
        ]
        base_edges = [{"from": "s", "to": "p"}, {"from": "p", "to": "e"}]

        cases = [
            (
                "typo_node_type",
                {
                    "kind": "iso5807-flowchart",
                    "nodes": [
                        {"id": "s", "type": "terminator", "label": "Bắt đầu"},
                        {"id": "d", "type": "decison", "label": "Hợp lệ?"},
                        {"id": "e", "type": "terminator", "label": "Kết thúc"},
                    ],
                    "edges": [{"from": "s", "to": "d"}, {"from": "d", "to": "e", "label": "Có"}],
                },
                ("decison", "decision"),
            ),
            (
                "dangling_edge_to",
                {"kind": "iso5807-flowchart", "nodes": base_nodes, "edges": base_edges + [{"from": "p", "to": "ghost_node"}]},
                ("to", "ghost_node"),
            ),
            (
                "dangling_edge_from",
                {"kind": "iso5807-flowchart", "nodes": base_nodes, "edges": [{"from": "missing_src", "to": "p"}]},
                ("from", "missing_src"),
            ),
            (
                "edge_to_annotation",
                {
                    "kind": "iso5807-flowchart",
                    "nodes": base_nodes + [{"id": "n_note", "type": "annotation", "attach_to": "p", "label": "Ghi chú"}],
                    "edges": base_edges + [{"from": "p", "to": "n_note"}],
                },
                ("annotation", "attach_to"),
            ),
            (
                "unknown_attach_to",
                {
                    "kind": "iso5807-flowchart",
                    "nodes": base_nodes + [{"id": "n_note", "type": "annotation", "attach_to": "nope", "label": "Ghi chú"}],
                    "edges": base_edges,
                },
                ("attach_to", "nope"),
            ),
            (
                "unknown_swimlane_id",
                {
                    "kind": "swimlane",
                    "lanes": [{"id": "rd", "title": "R&D"}, {"id": "fin", "title": "Tài chính"}],
                    "nodes": [
                        {"id": "s", "lane": "rd", "type": "terminator", "label": "Bắt đầu"},
                        {"id": "p", "lane": "fin_typo", "type": "process", "label": "Duyệt"},
                        {"id": "e", "lane": "fin", "type": "terminator", "label": "Kết thúc"},
                    ],
                    "edges": base_edges,
                },
                ("lane", "fin_typo"),
            ),
            (
                "missing_swimlane_field",
                {
                    "kind": "swimlane",
                    "lanes": [{"id": "rd", "title": "R&D"}],
                    "nodes": [
                        {"id": "s", "lane": "rd", "type": "terminator", "label": "Bắt đầu"},
                        {"id": "p", "type": "process", "label": "Quên khai báo lane"},
                        {"id": "e", "lane": "rd", "type": "terminator", "label": "Kết thúc"},
                    ],
                    "edges": base_edges,
                },
                ("lane", "p"),
            ),
            (
                "empty_swimlane_lanes",
                {"kind": "swimlane", "lanes": [], "nodes": base_nodes, "edges": base_edges},
                ("lanes",),
            ),
            (
                "unknown_slot",
                {
                    "kind": "iso5807-flowchart",
                    "nodes": [
                        {"id": "s", "type": "terminator", "label": "Bắt đầu"},
                        {"id": "p", "type": "process", "slot": "neon_pink", "label": "Xử lý"},
                        {"id": "e", "type": "terminator", "label": "Kết thúc"},
                    ],
                    "edges": base_edges,
                },
                ("slot", "neon_pink"),
            ),
            (
                "invalid_kind",
                {"kind": "bpmn-magic", "nodes": base_nodes, "edges": base_edges},
                ("kind", "bpmn-magic"),
            ),
            (
                "invalid_direction",
                {"kind": "iso5807-flowchart", "direction": "BT", "nodes": base_nodes, "edges": base_edges},
                ("direction", "BT"),
            ),
            (
                "invalid_edge_role",
                {
                    "kind": "iso5807-flowchart",
                    "nodes": base_nodes,
                    "edges": [{"from": "s", "to": "p", "role": "eror"}, {"from": "p", "to": "e"}],
                },
                ("role", "eror"),
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            for name, bad_spec, expected_tokens in cases:
                sp = os.path.join(tmp, f"{name}.json")
                out_p = os.path.join(tmp, f"{name}.drawio")
                with open(sp, "w", encoding="utf-8") as fh:
                    json.dump(bad_spec, fh, ensure_ascii=False)
                r = _run_script("iso5807_builder.py", [sp, "-o", out_p], cwd=tmp)
                combined = r.stdout + r.stderr
                self.assertNotEqual(r.returncode, 0, f"{name} unexpectedly succeeded")
                self.assertFalse(os.path.exists(out_p), f"{name} should not emit {out_p}")
                self.assertNotIn("Traceback", combined, f"{name} leaked traceback:\n{combined}")
                for tok in expected_tokens:
                    self.assertIn(tok, combined, f"{name} error message missing {tok!r}: {combined}")

    def test_iso5807_decision_single_entry_and_verified_clause_citations(self):
        # ISO 5807:1985 §9.2.2.4 requires a single entrance into a Decision diamond
        two_entry_spec = {
            "kind": "iso5807-flowchart",
            "direction": "TB",
            "title": "Kiểm thử Quyết định 2 lối vào (vi phạm §9.2.2.4)",
            "nodes": [
                {"id": "start", "type": "terminator", "label": "Bắt đầu"},
                {"id": "d0", "type": "decision", "label": "Kênh trực tuyến?"},
                {"id": "p1", "type": "process", "label": "Xử lý kênh Online"},
                {"id": "p2", "type": "process", "label": "Xử lý kênh Quầy"},
                {"id": "d_bad", "type": "decision", "label": "Đủ điều kiện duyệt?"},
                {"id": "ok", "type": "process", "label": "Phê duyệt"},
                {"id": "rej", "type": "process", "label": "Từ chối"},
                {"id": "end", "type": "terminator", "label": "Kết thúc"},
            ],
            "edges": [
                {"from": "start", "to": "d0"},
                {"from": "d0", "to": "p1", "label": "Có"},
                {"from": "d0", "to": "p2", "label": "Không"},
                {"from": "p1", "to": "d_bad"},
                {"from": "p2", "to": "d_bad"},
                {"from": "d_bad", "to": "ok", "label": "Có"},
                {"from": "d_bad", "to": "rej", "label": "Không", "role": "error"},
                {"from": "ok", "to": "end"},
                {"from": "rej", "to": "end"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "two_entry.json")
            dp = os.path.join(tmp, "two_entry.drawio")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(two_entry_spec, fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            r_val = _run_script("validate_iso5807.py", [dp, "--strict", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 1, f"Expected FAIL on 2-entry Decision: {r_val.stdout}")
            rep = json.loads(r_val.stdout)
            self.assertFalse(rep["iso_compliant"])
            entry_diags = [d for d in rep["diagnostics"] if d["code"] == "E-ISO-DECISION-ENTRY"]
            self.assertEqual(len(entry_diags), 1, rep["diagnostics"])
            self.assertEqual(entry_diags[0]["subject"], "d_bad")
            self.assertEqual(entry_diags[0]["clause"], "ISO 5807:1985 §9.2.2.4")
            entry_fixes = [f for f in rep["supportedFixes"] if f["code"] == "E-ISO-DECISION-ENTRY"]
            self.assertEqual(len(entry_fixes), 1)
            self.assertEqual(entry_fixes[0]["clause"], "ISO 5807:1985 §9.2.2.4")

        # Verify authoritative ISO 5807:1985 §9.x / §10.x sections in data/iso5807-shapes.json
        with open(os.path.join(SKILL_DIR, "data", "iso5807-shapes.json"), encoding="utf-8") as fh:
            symbols = json.load(fh)["symbols"]
        expected_clauses = {
            "data": "ISO 5807:1985 §9.1.1.1",
            "stored_data": "ISO 5807:1985 §9.1.1.2",
            "internal_storage": "ISO 5807:1985 §9.1.2.1",
            "sequential_data": "ISO 5807:1985 §9.1.2.2",
            "database": "ISO 5807:1985 §9.1.2.3",
            "direct_data": "ISO 5807:1985 §9.1.2.3",
            "document": "ISO 5807:1985 §9.1.2.4",
            "manual_input": "ISO 5807:1985 §9.1.2.5",
            "display": "ISO 5807:1985 §9.1.2.8",
            "process": "ISO 5807:1985 §9.2.1",
            "predefined_process": "ISO 5807:1985 §9.2.2.1",
            "manual_operation": "ISO 5807:1985 §9.2.2.2",
            "preparation": "ISO 5807:1985 §9.2.2.3",
            "decision": "ISO 5807:1985 §9.2.2.4",
            "parallel_mode": "ISO 5807:1985 §9.2.2.5",
            "loop_limit_start": "ISO 5807:1985 §9.2.2.6",
            "loop_limit_end": "ISO 5807:1985 §9.2.2.6",
            "terminator": "ISO 5807:1985 §9.4.2",
            "annotation": "ISO 5807:1985 §9.4.3",
        }
        for sym_key, clause in expected_clauses.items():
            self.assertEqual(symbols[sym_key]["iso_section"], clause, f"{sym_key} clause mismatch")
        self.assertIn("§9.4.1", symbols["on_page_connector"]["iso_section"])
        self.assertEqual(symbols["delay"]["origin"], "extension")
        self.assertEqual(symbols["off_page_connector"]["origin"], "extension")

    def test_cpm_dependency_cycle_rejection_while_flowchart_loops_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. Exact 2-node cycle A(3d) <-> B(5d) must abort and never report 8 days
            cyc2 = {
                "kind": "cpm",
                "title": "CPM có vòng phụ thuộc A <-> B",
                "nodes": [
                    {"id": "A", "label": "Việc A", "duration": 3},
                    {"id": "B", "label": "Việc B", "duration": 5},
                ],
                "edges": [{"from": "A", "to": "B"}, {"from": "B", "to": "A"}],
            }
            sp2 = os.path.join(tmp, "cpm_cyc2.json")
            out2 = os.path.join(tmp, "cpm_cyc2.drawio")
            with open(sp2, "w", encoding="utf-8") as fh:
                json.dump(cyc2, fh, ensure_ascii=False)
            r2 = _run_script("iso5807_builder.py", [sp2, "-o", out2], cwd=tmp)
            self.assertNotEqual(r2.returncode, 0, "Cyclic CPM A<->B must fail")
            self.assertFalse(os.path.exists(out2))
            self.assertNotIn("Traceback", r2.stderr + r2.stdout)
            self.assertIn("cycle", (r2.stderr + r2.stdout).lower())
            self.assertIn("A", r2.stderr)
            self.assertIn("B", r2.stderr)

            # 2. 3-node cycle A -> B -> C -> A with downstream D: must isolate A, B, C (not D)
            cyc3 = {
                "kind": "cpm",
                "nodes": [
                    {"id": "A", "label": "A", "duration": 2},
                    {"id": "B", "label": "B", "duration": 3},
                    {"id": "C", "label": "C", "duration": 4},
                    {"id": "D", "label": "D", "duration": 1},
                ],
                "edges": [
                    {"from": "A", "to": "B"},
                    {"from": "B", "to": "C"},
                    {"from": "C", "to": "A"},
                    {"from": "C", "to": "D"},
                ],
            }
            sp3 = os.path.join(tmp, "cpm_cyc3.json")
            out3 = os.path.join(tmp, "cpm_cyc3.drawio")
            with open(sp3, "w", encoding="utf-8") as fh:
                json.dump(cyc3, fh, ensure_ascii=False)
            r3 = _run_script("iso5807_builder.py", [sp3, "-o", out3], cwd=tmp)
            self.assertNotEqual(r3.returncode, 0)
            self.assertFalse(os.path.exists(out3))
            self.assertIn("tasks involved: A, B, C", r3.stderr)
            self.assertNotIn("D)", r3.stderr)

            # 3. Self-loop A -> A on CPM rejected
            cyc1 = {
                "kind": "cpm",
                "nodes": [{"id": "A", "label": "A", "duration": 2}],
                "edges": [{"from": "A", "to": "A"}],
            }
            with self.assertRaises(ValueError) as ctx:
                iso5807_builder.compile_spec_to_drawio(cyc1)
            self.assertIn("A -> A", str(ctx.exception))

            # 4. Negative / missing CPM duration rejected
            bad_dur = {
                "kind": "cpm",
                "nodes": [{"id": "A", "label": "A", "duration": -1}],
                "edges": [],
            }
            with self.assertRaises(ValueError):
                iso5807_builder.compile_spec_to_drawio(bad_dur)

            missing_dur = {
                "kind": "cpm",
                "nodes": [{"id": "A", "label": "A"}],
                "edges": [],
            }
            with self.assertRaises(ValueError):
                iso5807_builder.compile_spec_to_drawio(missing_dur)

            # 5. Flowchart retry loop remains fully supported & passes strict validation
            retry_sp = os.path.join(tmp, "retry.json")
            retry_out = os.path.join(tmp, "retry.drawio")
            with open(retry_sp, "w", encoding="utf-8") as fh:
                json.dump(_eval1_payment_retry_spec(with_hints=True), fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [retry_sp, "-o", retry_out], cwd=tmp).returncode, 0)
            r_retry_val = _run_script("validate_iso5807.py", [retry_out, "--strict", "--score", "--json"], cwd=tmp)
            self.assertEqual(r_retry_val.returncode, 0, r_retry_val.stdout)
            self.assertEqual(json.loads(r_retry_val.stdout)["readability_score"], 0)

    def test_v101_empty_drawio_page_rejected_by_strict_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            blank_page = os.path.join(tmp, "blank.drawio")
            with open(blank_page, "w", encoding="utf-8") as fh:
                fh.write(
                    '<mxfile host="pro-diagrams"><diagram id="p1" name="Trang trống">'
                    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                    '</root></mxGraphModel></diagram></mxfile>'
                )
            r_val = _run_script("validate_iso5807.py", [blank_page, "--strict", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 1, f"Empty page must fail --strict: {r_val.stdout}")
            rep = json.loads(r_val.stdout)
            self.assertFalse(rep["iso_compliant"])
            self.assertFalse(rep["passed"])
            codes = {d["code"] for d in rep["diagnostics"]}
            self.assertIn("E-ISO-EMPTY", codes)

            # Chrome-only page (only title banner, 0 flow nodes) must also fail E-ISO-EMPTY
            chrome_only = os.path.join(tmp, "chrome_only.drawio")
            with open(chrome_only, "w", encoding="utf-8") as fh:
                fh.write(
                    '<mxfile host="pro-diagrams"><diagram id="p1" name="Chỉ tiêu đề">'
                    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                    '<mxCell id="title_banner" value="Tiêu đề" style="text;html=1;fillColor=none;strokeColor=none;" '
                    'vertex="1" parent="1"><mxGeometry x="40" y="20" width="300" height="40" as="geometry"/></mxCell>'
                    '</root></mxGraphModel></diagram></mxfile>'
                )
            r_ch = _run_script("validate_iso5807.py", [chrome_only, "--strict", "--json"], cwd=tmp)
            self.assertEqual(r_ch.returncode, 1)
            self.assertIn("E-ISO-EMPTY", {d["code"] for d in json.loads(r_ch.stdout)["diagnostics"]})

    def test_v101_sop_duration_does_not_trigger_cpm_while_explicit_cpm_cycle_rejected(self):
        pay_spec = _eval1_payment_retry_spec(with_hints=True)
        for node in pay_spec["nodes"]:
            if node["type"] == "delay":
                node["duration"] = 5
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "pay_dur5.json")
            dp = os.path.join(tmp, "pay_dur5.drawio")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(pay_spec, fh, ensure_ascii=False)
            r_build = _run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp)
            self.assertEqual(r_build.returncode, 0, f"SOP with duration:5 falsely triggered CPM: {r_build.stderr}")
            with open(dp, encoding="utf-8") as fh:
                xml_txt = fh.read()
            self.assertNotIn("ES=", xml_txt, "SOP node label should not be overwritten with CPM ES/EF metrics")
            r_val = _run_script("validate_iso5807.py", [dp, "--strict", "--score", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 0, r_val.stdout)
            self.assertTrue(json.loads(r_val.stdout)["iso_compliant"])

            # Explicit compute_cpm: True on a cyclic graph MUST still fail
            explicit_cyc = {
                "kind": "iso5807-flowchart",
                "compute_cpm": True,
                "nodes": [
                    {"id": "A", "type": "process", "label": "A", "duration": 3},
                    {"id": "B", "type": "process", "label": "B", "duration": 5},
                ],
                "edges": [{"from": "A", "to": "B"}, {"from": "B", "to": "A"}],
            }
            with self.assertRaisesRegex(ValueError, "cycle"):
                iso5807_builder.compile_spec_to_drawio(explicit_cyc)

    def test_v101_swimlane_whitespace_lane_id_normalization_and_duplicate_rejection(self):
        spec = {
            "kind": "swimlane",
            "title": "Chuẩn hóa khoảng trắng ID làn",
            "lanes": [
                {"id": " rd ", "title": "Nghiên cứu & Phát triển"},
                {"id": "  qa\t", "title": "Kiểm thử chất lượng"},
            ],
            "nodes": [
                {"id": "s", "type": "terminator", "label": "Bắt đầu", "lane": "rd"},
                {"id": "p", "type": "process", "label": "Kiểm thử tích hợp", "lane": "qa"},
                {"id": "e", "type": "terminator", "label": "Kết thúc", "lane": "qa"},
            ],
            "edges": [{"from": "s", "to": "p"}, {"from": "p", "to": "e"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "ws_lane.json")
            dp = os.path.join(tmp, "ws_lane.drawio")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)
            r_build = _run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp)
            self.assertEqual(r_build.returncode, 0, r_build.stderr)
            r_val = _run_script("validate_iso5807.py", [dp, "--strict", "--score", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 0, r_val.stdout)
            rep = json.loads(r_val.stdout)
            self.assertTrue(rep["iso_compliant"])
            self.assertEqual(rep["readability_score"], 0)

            # Duplicate lane ID after trimming (" rd " vs "rd") MUST raise a clear ValueError
            dup_spec = dict(spec, lanes=[{"id": " rd ", "title": "R&D 1"}, {"id": "rd", "title": "R&D 2"}])
            with self.assertRaisesRegex(ValueError, "duplicate.*lane id 'rd'"):
                iso5807_builder.compile_spec_to_drawio(dup_spec)

    def test_v101_five_branch_decision_single_stem_passes_iso_and_separates_contrast(self):
        spec = {
            "kind": "program-flowchart",
            "title": "§10.3.1 · Decision 5 nhánh có nhãn",
            "direction": "TB",
            "nodes": [
                {"id": "start", "type": "terminator", "label": "Bắt đầu"},
                {"id": "choose", "type": "decision", "label": "Giá trị điều kiện"},
                {"id": "e1", "type": "terminator", "label": "Chọn 1"},
                {"id": "e2", "type": "terminator", "label": "Chọn 2"},
                {"id": "e3", "type": "terminator", "label": "Chọn 3"},
                {"id": "e4", "type": "terminator", "label": "Chọn 4"},
                {"id": "e5", "type": "terminator", "label": "Chọn 5"},
            ],
            "edges": [
                {"from": "start", "to": "choose"},
                {"from": "choose", "to": "e1", "label": "1"},
                {"from": "choose", "to": "e2", "label": "2"},
                {"from": "choose", "to": "e3", "label": "3"},
                {"from": "choose", "to": "e4", "label": "4"},
                {"from": "choose", "to": "e5", "label": "5"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "five_exits.json")
            dp = os.path.join(tmp, "five_exits.drawio")
            svgp = os.path.join(tmp, "five_exits.svg")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp, "--render-svg", svgp], cwd=tmp).returncode, 0)

            with open(dp, encoding="utf-8") as fh:
                xml_txt = fh.read()
            self.assertIn("isoStemBranch=1;", xml_txt, "5-exit Decision should auto-use ISO §10.3.1(b) single-stem fan-out")

            r_val = _run_script("validate_iso5807.py", [dp, "--strict", "--score", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 0, f"5-exit Decision must pass --strict: {r_val.stdout}")
            rep = json.loads(r_val.stdout)
            self.assertTrue(rep["iso_compliant"])
            self.assertTrue(rep["passed"])
            self.assertEqual(rep["errors"], 0)
            self.assertEqual(rep["warnings"], 0)
            self.assertEqual(rep["hints"], 1)
            self.assertEqual(rep["readability_score"], 0)
            self.assertEqual(rep["diagnostics"][0]["code"], "I-LAYOUT-DECISION-FANOUT")
            self.assertEqual(rep["diagnostics"][0]["severity"], "info")
            self.assertEqual(rep["diagnostics"][0]["category"], "layout")

            # Inject a low-contrast fillColor on one node: ISO compliance must remain True while contrast warning fails --strict
            low_c_dp = os.path.join(tmp, "low_contrast.drawio")
            with open(low_c_dp, "w", encoding="utf-8") as fh:
                fh.write(xml_txt.replace("fillColor=#EEF2F5;", "fillColor=#3A4248;", 1))
            r_strict = _run_script("validate_iso5807.py", [low_c_dp, "--strict", "--json"], cwd=tmp)
            self.assertEqual(r_strict.returncode, 1)
            rep_lc = json.loads(r_strict.stdout)
            self.assertTrue(rep_lc["iso_compliant"], "ISO compliance must stay decoupled from WCAG contrast warnings")
            self.assertFalse(rep_lc["contrast_clean"])
            self.assertGreaterEqual(rep_lc["summary"]["contrast_warnings"], 1)
            r_iso_only = _run_script("validate_iso5807.py", [low_c_dp, "--strict", "--iso-only", "--json"], cwd=tmp)
            self.assertEqual(r_iso_only.returncode, 0)

    def test_v101_loop_limit_id_pairing_mismatch_rejected_and_nested_loops_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. Balanced count but mismatched IDs (L vs M) MUST fail E-ISO-LOOP-PAIR
            mismatch_spec = {
                "kind": "program-flowchart",
                "nodes": [
                    {"id": "s", "type": "terminator", "label": "Bắt đầu"},
                    {"id": "lo", "type": "loop_limit_start", "label": "L\nDừng khi hết chỉ số"},
                    {"id": "w", "type": "process", "label": "Xử lý"},
                    {"id": "lc", "type": "loop_limit_end", "label": "M"},
                    {"id": "e", "type": "terminator", "label": "Kết thúc"},
                ],
                "edges": [
                    {"from": "s", "to": "lo"}, {"from": "lo", "to": "w"},
                    {"from": "w", "to": "lc"}, {"from": "lc", "to": "e"},
                ],
            }
            mp = os.path.join(tmp, "loop_mismatch.drawio")
            iso5807_builder.compile_spec_to_drawio(mismatch_spec).write(mp, encoding="utf-8")
            rep_m = validate_iso5807.build_structured_report(mp, strict=True)
            self.assertFalse(rep_m["iso_compliant"])
            self.assertIn("E-ISO-LOOP-PAIR", {d["code"] for d in rep_m["diagnostics"]})

            # 2. Test-after loop (ID on last line of loop_limit_end per §9.2.2.6) MUST pass
            after_spec = {
                "kind": "program-flowchart",
                "nodes": [
                    {"id": "s", "type": "terminator", "label": "Bắt đầu"},
                    {"id": "lo", "type": "loop_limit_start", "label": "L"},
                    {"id": "w", "type": "process", "label": "Xử lý"},
                    {"id": "lc", "type": "loop_limit_end", "label": "Dừng khi hết chỉ số\nL"},
                    {"id": "e", "type": "terminator", "label": "Kết thúc"},
                ],
                "edges": [
                    {"from": "s", "to": "lo"}, {"from": "lo", "to": "w"},
                    {"from": "w", "to": "lc"}, {"from": "lc", "to": "e"},
                ],
            }
            ap = os.path.join(tmp, "loop_after.drawio")
            iso5807_builder.compile_spec_to_drawio(after_spec).write(ap, encoding="utf-8")
            rep_a = validate_iso5807.build_structured_report(ap, strict=True)
            self.assertTrue(rep_a["iso_compliant"] and rep_a["passed"], rep_a["diagnostics"])

            # 3. Two nested loops with explicit loop_id metadata MUST pass
            nested_spec = {
                "kind": "program-flowchart",
                "nodes": [
                    {"id": "s", "type": "terminator", "label": "Bắt đầu"},
                    {"id": "o1", "type": "loop_limit_start", "loop_id": "OUTER", "label": "Vòng ngoài i=1..N"},
                    {"id": "i1", "type": "loop_limit_start", "loop_id": "INNER", "label": "Vòng trong j=1..M"},
                    {"id": "w", "type": "process", "label": "Tính tổng phần tử"},
                    {"id": "i2", "type": "loop_limit_end", "loop_id": "INNER", "label": "Kết thúc vòng j"},
                    {"id": "o2", "type": "loop_limit_end", "loop_id": "OUTER", "label": "Kết thúc vòng i"},
                    {"id": "e", "type": "terminator", "label": "Kết thúc"},
                ],
                "edges": [
                    {"from": "s", "to": "o1"}, {"from": "o1", "to": "i1"},
                    {"from": "i1", "to": "w"}, {"from": "w", "to": "i2"},
                    {"from": "i2", "to": "o2"}, {"from": "o2", "to": "e"},
                ],
            }
            np = os.path.join(tmp, "loop_nested.drawio")
            iso5807_builder.compile_spec_to_drawio(nested_spec).write(np, encoding="utf-8")
            with open(np, encoding="utf-8") as fh:
                self.assertIn("isoLoopId=OUTER;", fh.read())
            rep_n = validate_iso5807.build_structured_report(np, strict=True)
            self.assertTrue(rep_n["iso_compliant"] and rep_n["passed"], rep_n["diagnostics"])

    def test_v110_cross_page_connectors_multipage_spec_and_missing_counterpart(self):
        multipage_spec = {
            "kind": "program-flowchart",
            "pages": [
                {
                    "page_name": "1.4",
                    "title": "Trang 1.4",
                    "nodes": [
                        {"id": "start", "type": "terminator", "label": "Bắt đầu"},
                        {"id": "p1", "type": "process", "label": "Xử lý ở trang 1.4"},
                        {"id": "c_out", "type": "on_page_connector", "label": "λ1", "ref_page": "3.2"},
                        {"id": "n1", "type": "annotation", "attach_to": "c_out", "label": "Đến trang 3.2"},
                    ],
                    "edges": [
                        {"from": "start", "to": "p1"},
                        {"from": "p1", "to": "c_out"},
                    ],
                },
                {
                    "page_name": "3.2",
                    "title": "Trang 3.2",
                    "nodes": [
                        {"id": "c_in", "type": "on_page_connector", "label": "λ1", "ref_page": "1.4"},
                        {"id": "p2", "type": "process", "label": "Xử lý tiếp ở trang 3.2"},
                        {"id": "finish", "type": "terminator", "label": "Kết thúc"},
                        {"id": "n2", "type": "annotation", "attach_to": "c_in", "label": "Từ trang 1.4"},
                    ],
                    "edges": [
                        {"from": "c_in", "to": "p2"},
                        {"from": "p2", "to": "finish"},
                    ],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "multipage.json")
            dp = os.path.join(tmp, "multipage.drawio")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(multipage_spec, fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            r_val = _run_script("validate_iso5807.py", [dp, "--strict", "--score", "--json"], cwd=tmp)
            self.assertEqual(r_val.returncode, 0, f"Valid cross-page connector λ1 must pass: {r_val.stdout}")
            rep = json.loads(r_val.stdout)
            self.assertTrue(rep["iso_compliant"] and rep["passed"])
            self.assertEqual(rep["errors"], 0)
            self.assertEqual(rep["warnings"], 0)

            # Missing counterpart: change λ1 on page 3.2 to λ2 -> MUST fail naming code & page
            broken_spec = json.loads(json.dumps(multipage_spec))
            broken_spec["pages"][1]["nodes"][0]["label"] = "λ2"
            bp = os.path.join(tmp, "multipage_broken.drawio")
            iso5807_builder.compile_spec_to_drawio(broken_spec).write(bp, encoding="utf-8")
            rep_b = validate_iso5807.build_structured_report(bp, strict=True)
            self.assertFalse(rep_b["iso_compliant"])
            conn_msgs = [d["message"] for d in rep_b["diagnostics"] if d["code"] == "E-ISO-CONNECTOR-PAIR"]
            self.assertTrue(any("λ1" in m and "1.4" in m for m in conn_msgs), conn_msgs)
            self.assertTrue(any("λ2" in m and "3.2" in m for m in conn_msgs), conn_msgs)

            # Wrong ref_page: page 1.4 points to "9.9" instead of "3.2" -> MUST fail E-ISO-CONNECTOR-PAIR
            badref_spec = json.loads(json.dumps(multipage_spec))
            badref_spec["pages"][0]["nodes"][2]["ref_page"] = "9.9"
            rp = os.path.join(tmp, "multipage_badref.drawio")
            iso5807_builder.compile_spec_to_drawio(badref_spec).write(rp, encoding="utf-8")
            rep_r = validate_iso5807.build_structured_report(rp, strict=True)
            self.assertFalse(rep_r["iso_compliant"])
            self.assertTrue(
                any(d["code"] == "E-ISO-CONNECTOR-PAIR" and "9.9" in d["message"] and "3.2" in d["message"]
                    for d in rep_r["diagnostics"]),
                rep_r["diagnostics"],
            )

    def test_v110_iso5807_annex_a_through_e_regression_and_drawio_svg_parity(self):
        fixtures_dir = os.path.join(SKILL_DIR, "tests", "fixtures", "iso5807_annex")
        cases = [
            ("annex_a_data_flowchart.json", "data-flowchart", True, 0, 0, 1),
            ("annex_b_a_program_retry.json", "program-flowchart", True, 0, 0, 0),
            ("annex_b_b_nested_loops.json", "program-flowchart", True, 0, 0, 0),
            ("annex_c_system_flowchart.json", "system-flowchart", True, 1, 0, 0),
            ("annex_d_program_network.json", "program-network", False, 5, 5, 0),
            ("annex_e_system_resources.json", "system-resources", True, 2, 0, 1),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for fname, expected_dtype, require_zero_score, exp_bidir, exp_ct, exp_overlays in cases:
                fpath = os.path.join(fixtures_dir, fname)
                self.assertTrue(os.path.exists(fpath), f"Missing Annex fixture: {fpath}")
                out_drawio = os.path.join(tmp, fname.replace(".json", ".drawio"))
                out_svg = os.path.join(tmp, fname.replace(".json", ".svg"))

                r_build = _run_script("iso5807_builder.py", [fpath, "-o", out_drawio, "--render-svg", out_svg], cwd=tmp)
                self.assertEqual(r_build.returncode, 0, f"{fname} compile failed: {r_build.stderr}")

                # Validate ISO 5807 compliance via --strict --iso-only
                r_iso = _run_script("validate_iso5807.py", [out_drawio, "--strict", "--iso-only", "--json"], cwd=tmp)
                self.assertEqual(r_iso.returncode, 0, f"{fname} ISO validation failed: {r_iso.stdout}")
                rep = json.loads(r_iso.stdout)
                self.assertEqual(rep["diagram_type"], expected_dtype, fname)
                self.assertTrue(rep["iso_compliant"], f"{fname}: {rep['diagnostics']}")
                self.assertEqual(rep["summary"]["iso_errors"], 0, fname)
                self.assertEqual(rep["summary"]["iso_warnings"], 0, fname)
                self.assertEqual(rep["summary"]["contrast_warnings"], 0, fname)

                if require_zero_score:
                    r_full = _run_script("validate_iso5807.py", [out_drawio, "--strict", "--score", "--json"], cwd=tmp)
                    self.assertEqual(r_full.returncode, 0, f"{fname} full --strict failed: {r_full.stdout}")
                    self.assertEqual(json.loads(r_full.stdout)["readability_score"], 0, fname)

                # Strict .drawio <-> .svg parity verification (no lost symbols, arrowheads, or markers)
                drawio_root = ET.parse(out_drawio).getroot()
                svg_root = ET.parse(out_svg).getroot()
                svg_by_cell = {
                    el.get("data-cell-id"): el
                    for el in svg_root.iter()
                    if el.get("data-cell-id")
                }

                bidir_seen = 0
                ct_seen = 0
                overlay_seen = 0
                for cell in drawio_root.findall(".//mxCell"):
                    cid = cell.get("id")
                    if cid in ("0", "1", None) or cell.get("parent") is None:
                        continue
                    st = cell.get("style") or ""
                    self.assertIn(cid, svg_by_cell, f"{fname}: cell {cid!r} missing from rendered SVG")
                    g_el = svg_by_cell[cid]
                    if cell.get("vertex") == "1" and cid != "title_banner":
                        self.assertTrue(g_el.get("data-shape"), f"{fname}: vertex {cid!r} missing data-shape in SVG")
                        if "isoOverlayItems=" in st:
                            overlay_seen += 1
                            self.assertTrue(g_el.get("data-overlay-items"), f"{fname}: overlay items lost on {cid!r}")
                    elif cell.get("edge") == "1":
                        has_start = "startArrow=block" in st
                        has_end = "endArrow=none" not in st
                        if has_start:
                            self.assertEqual(g_el.get("data-start-arrow"), "block", f"{fname}: lost startArrow on {cid!r}")
                            self.assertTrue(
                                any(ch.get("class") == "arrow-start" for ch in g_el.iter()),
                                f"{fname}: missing <polygon class='arrow-start'> on {cid!r}",
                            )
                        if has_end:
                            self.assertTrue(
                                any(ch.get("class") == "arrow-end" for ch in g_el.iter()),
                                f"{fname}: missing <polygon class='arrow-end'> on {cid!r}",
                            )
                        if has_start and has_end:
                            bidir_seen += 1
                        if "isoLine=control_transfer" in st:
                            ct_seen += 1
                            self.assertEqual(g_el.get("data-iso-line"), "control_transfer", f"{fname}: lost control_transfer on {cid!r}")
                            markers = [ch for ch in g_el.iter() if ch.get("class") == "control-transfer-marker"]
                            self.assertEqual(len(markers), 1, f"{fname}: missing control-transfer triangle on {cid!r}")
                            self.assertEqual(markers[0].get("data-code"), (cell.get("value") or "").strip())

                self.assertEqual(bidir_seen, exp_bidir, f"{fname}: bidirectional edge parity mismatch")
                self.assertEqual(ct_seen, exp_ct, f"{fname}: control_transfer triangle parity mismatch")
                self.assertEqual(overlay_seen, exp_overlays, f"{fname}: overlay multi_document parity mismatch")

    def test_v110_communication_link_and_control_transfer_validation(self):
        spec = {
            "kind": "program-network",
            "title": "Kiểm thử Communication Link & Control Transfer",
            "nodes": [
                {"id": "p1", "type": "process", "label": "Trạm trung tâm"},
                {"id": "c1", "type": "card", "label": "Thẻ tham số"},
                {"id": "t1", "type": "paper_tape", "label": "Băng dữ liệu"},
                {"id": "el", "type": "ellipsis", "label": "Bỏ lược trạm trung gian"},
                {"id": "p2", "type": "process", "label": "Trạm biên"},
            ],
            "edges": [
                {"from": "c1", "to": "p1"},
                {"from": "p1", "to": "t1", "bidirectional": True},
                {"from": "p1", "to": "el", "role": "communication_link", "label": "TLS 1.3"},
                {"from": "el", "to": "p2", "role": "control_transfer", "label": "P"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "comm.json")
            dp = os.path.join(tmp, "comm.drawio")
            svgp = os.path.join(tmp, "comm.svg")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp, "--render-svg", svgp], cwd=tmp).returncode, 0)

            rep = validate_iso5807.build_structured_report(dp, strict=True)
            self.assertTrue(rep["iso_compliant"] and rep["passed"], rep["diagnostics"])

            with open(svgp, encoding="utf-8") as sf:
                svg_txt = sf.read()
            self.assertIn('data-iso-line="communication_link"', svg_txt)
            self.assertIn('data-iso-line="control_transfer"', svg_txt)
            self.assertIn('data-code="P"', svg_txt)
            self.assertIn('data-shape="card"', svg_txt)
            self.assertIn('data-shape="paper_tape"', svg_txt)
            self.assertIn('data-shape="ellipsis"', svg_txt)

            # Control transfer without label MUST emit W-ISO-CONTROL-TRANSFER warning
            bad_ct = json.loads(json.dumps(spec))
            bad_ct["edges"][3]["label"] = ""
            bdp = os.path.join(tmp, "bad_ct.drawio")
            iso5807_builder.compile_spec_to_drawio(bad_ct).write(bdp, encoding="utf-8")
            rep_bad = validate_iso5807.build_structured_report(bdp, strict=True)
            self.assertFalse(rep_bad["iso_compliant"])
            self.assertIn("W-ISO-CONTROL-TRANSFER", {d["code"] for d in rep_bad["diagnostics"]})


class TestTrackARepurposeViewerRunbookAndRender(unittest.TestCase):
    """Covers all remaining Track A scripts: relabel, restyle, runbook, drawiohtml,
    drawio_render_svg, autolayout, drawio_cli, edgeports, shapesearch,
    encode_drawio_url, drawio2mermaid, explain, diagram_ir, repair_png."""

    def test_relabel_extract_map_and_apply_alias_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = os.path.join(tmp, "flow.json")
            src_drawio = os.path.join(tmp, "flow_vi.drawio")
            labels_json = os.path.join(tmp, "labels.json")
            out_map = os.path.join(tmp, "flow_en_map.drawio")
            out_apply = os.path.join(tmp, "flow_en_apply.drawio")

            spec = _eval1_payment_retry_spec(with_hints=True)
            with open(spec_path, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [spec_path, "-o", src_drawio], cwd=tmp).returncode, 0)

            r_ext = _run_script("relabel.py", [src_drawio, "--extract", "-o", labels_json], cwd=tmp)
            self.assertEqual(r_ext.returncode, 0, r_ext.stderr)
            with open(labels_json, encoding="utf-8") as fh:
                lbls = json.load(fh)
            self.assertIn("Bắt đầu", lbls)
            lbls["Bắt đầu"] = "Start"
            lbls["Kết thúc"] = "End"
            with open(labels_json, "w", encoding="utf-8") as fh:
                json.dump(lbls, fh, ensure_ascii=False, indent=2)

            r_map = _run_script("relabel.py", [src_drawio, "--map", labels_json, "-o", out_map], cwd=tmp)
            r_apply = _run_script("relabel.py", [src_drawio, "--apply", labels_json, "-o", out_apply], cwd=tmp)
            self.assertEqual(r_map.returncode, 0, r_map.stderr)
            self.assertEqual(r_apply.returncode, 0, r_apply.stderr)

            with open(out_map, "rb") as f1, open(out_apply, "rb") as f2:
                b_map, b_apply = f1.read(), f2.read()
            self.assertEqual(b_map, b_apply, "--map and --apply must produce byte-identical output")
            self.assertIn(b"Start", b_map)
            self.assertIn(b"End", b_map)

    def test_restyle_light_dark_light_roundtrip_preserves_all_7_slots_and_swimlanes(self):
        # Swimlane containing all 7 semantic slots: primary, neutral, accent, secondary, warning, danger, success
        spec = {
            "kind": "swimlane",
            "direction": "TB",
            "pool_title": "QUY TRÌNH KIỂM THỬ 7 NHÓM MÀU",
            "title": "Kiểm thử Restyle 7 Slot & Swimlane",
            "subtitle": "Light -> Dark -> Light Round-Trip",
            "lanes": [
                {"id": "l1", "title": "Làn 1"},
                {"id": "l2", "title": "Làn 2"},
            ],
            "nodes": [
                {"id": "n_primary", "lane": "l1", "type": "terminator", "label": "Bắt đầu", "slot": "primary"},
                {"id": "n_neutral", "lane": "l1", "type": "process", "label": "Xử lý chuẩn", "slot": "neutral"},
                {"id": "n_secondary", "lane": "l1", "type": "database", "label": "Kho dữ liệu", "slot": "secondary"},
                {"id": "n_warning", "lane": "l2", "type": "document", "label": "Chứng từ kiểm tra", "slot": "warning"},
                {"id": "n_accent", "lane": "l2", "type": "decision", "label": "Đạt kiểm tra?", "slot": "accent"},
                {"id": "n_danger", "lane": "l2", "type": "display", "label": "Cảnh báo lỗi", "slot": "danger"},
                {"id": "n_success", "lane": "l1", "type": "terminator", "label": "Hoàn tất", "slot": "success"},
            ],
            "edges": [
                {"from": "n_primary", "to": "n_neutral"},
                {"from": "n_neutral", "to": "n_secondary"},
                {"from": "n_secondary", "to": "n_warning"},
                {"from": "n_warning", "to": "n_accent"},
                {"from": "n_accent", "to": "n_success", "label": "Đạt"},
                {"from": "n_accent", "to": "n_danger", "label": "Lỗi", "role": "error"},
                {"from": "n_danger", "to": "n_success"},
            ],
        }
        slot_ids = ["n_primary", "n_neutral", "n_secondary", "n_warning", "n_accent", "n_danger", "n_success"]
        with tempfile.TemporaryDirectory() as tmp:
            spec_p = os.path.join(tmp, "s7.json")
            light_1 = os.path.join(tmp, "s7_light1.drawio")
            dark_1 = os.path.join(tmp, "s7_dark.drawio")
            light_2 = os.path.join(tmp, "s7_light2.drawio")
            with open(spec_p, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)

            self.assertEqual(_run_script("iso5807_builder.py", [spec_p, "-o", light_1], cwd=tmp).returncode, 0)
            self.assertEqual(_run_script("restyle.py", [light_1, "--preset", "tech-warm-dark", "-o", dark_1], cwd=tmp).returncode, 0)
            self.assertEqual(_run_script("restyle.py", [dark_1, "--preset", "tech-warm-light", "-o", light_2], cwd=tmp).returncode, 0)

            def _slot_colors(path):
                root = ET.parse(path).getroot()
                out = {}
                for c in root.iter("mxCell"):
                    cid = c.get("id")
                    if cid in slot_ids:
                        st = c.get("style") or ""
                        out[cid] = ((_extract_style_key(st, "fillColor") or "").upper(), (_extract_style_key(st, "strokeColor") or "").upper())
                return out

            # Verify dark swimlaneFillColor remapped (zero #FFFFFF / #FAF8F5) and opaque labelBackgroundColor
            dark_root = ET.parse(dark_1).getroot()
            lane_bodies = []
            for c in dark_root.iter("mxCell"):
                st = c.get("style") or ""
                if c.get("vertex") == "1" and "swimlane" in st:
                    sfc = (_extract_style_key(st, "swimlaneFillColor") or "").upper()
                    if sfc:
                        lane_bodies.append(sfc)
                        self.assertNotIn(sfc, ("#FFFFFF", "#FAF8F5"), f"Light swimlaneFillColor leaked into dark mode: {sfc}")
                if c.get("edge") == "1":
                    lbg = _extract_style_key(st, "labelBackgroundColor")
                    if lbg is not None:
                        self.assertNotEqual(lbg.lower(), "none")
                        self.assertEqual(lbg.upper(), "#161C20")
            self.assertTrue(any(b in ("#1B2328", "#182025") for b in lane_bodies), f"Expected dark lane body fill in {lane_bodies}")

            # Verify all 7/7 semantic slots survive Light -> Dark -> Light intact
            c_before = _slot_colors(light_1)
            c_after = _slot_colors(light_2)
            self.assertEqual(len(c_before), 7)
            self.assertEqual(c_before, c_after, f"Slot round-trip drift: {c_before} != {c_after}")

            # Both dark and round-tripped light pass validate_iso5807 --strict
            for path in (dark_1, light_2):
                r_val = _run_script("validate_iso5807.py", [path, "--strict"], cwd=tmp)
                self.assertEqual(r_val.returncode, 0, f"{path} failed strict validation: {r_val.stdout}\n{r_val.stderr}")

    def test_runbook_html_unescape_chrome_filter_connector_bridge_and_wcag_css(self):
        spec = {
            "kind": "iso5807-flowchart",
            "title": "SOP R&D & Kiểm duyệt",
            "nodes": [
                {"id": "start", "type": "terminator", "label": "Bắt đầu R&D"},
                {"id": "dec1", "type": "decision", "label": "Ngân sách <= 100tr & hợp lệ?"},
                {"id": "proc_ok", "type": "process", "label": "Phê duyệt\nCấp ngân sách"},
                {"id": "c_in", "type": "on_page_connector", "label": "A"},
                {"id": "c_out", "type": "on_page_connector", "label": "A"},
                {"id": "end", "type": "terminator", "label": "Kết thúc"},
                {"id": "note1", "type": "annotation", "attach_to": "proc_ok", "label": "Ghi chú nội bộ không đưa vào bước"},
            ],
            "edges": [
                {"from": "start", "to": "dec1"},
                {"from": "dec1", "to": "proc_ok", "label": "Có & Đạt"},
                {"from": "dec1", "to": "c_in", "label": "Không", "role": "error"},
                {"from": "proc_ok", "to": "end"},
                {"from": "c_out", "to": "end"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "rb_spec.json")
            dp = os.path.join(tmp, "rb.drawio")
            hp = os.path.join(tmp, "rb.html")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            # Inject genuine draw.io HTML-formatted label (<b>...</b><br/>...&amp;...) into proc_ok cell
            tree = ET.parse(dp)
            for cell in tree.getroot().iter("mxCell"):
                if cell.get("id") == "proc_ok":
                    cell.set("value", "<b>Phê duyệt</b><br/>Cấp ngân sách R&amp;D")
            tree.write(dp, encoding="utf-8", xml_declaration=False)

            r_rb = _run_script("runbook.py", [dp, "-o", hp], cwd=tmp)
            self.assertEqual(r_rb.returncode, 0, r_rb.stderr)
            with open(hp, encoding="utf-8") as fh:
                html_txt = fh.read()

            m = re.search(r"const DATA=(\{.*?\});", html_txt)
            self.assertIsNotNone(m)
            data = json.loads(m.group(1))

            # title_banner and annotation must be excluded
            self.assertNotIn("title_banner", data["nodes"])
            self.assertNotIn("note1", data["nodes"])
            # Paired on-page connector A -> A must be bridged directly to end
            self.assertNotIn("c_in", data["nodes"])
            self.assertNotIn("c_out", data["nodes"])
            dec_targets = {e["target"] for e in data["edges"]["dec1"]}
            self.assertIn("end", dec_targets, f"Expected bridged edge dec1 -> end, got {data['edges']['dec1']}")

            # Clean HTML unescaping (no literal <b>, <br/>, &amp;, &lt;)
            all_labels = [n["label"] for n in data["nodes"].values()] + [
                e["label"] for elist in data["edges"].values() for e in elist
            ]
            joined = "\n".join(all_labels)
            self.assertIn("R&D", joined)
            self.assertIn("<= 100tr", joined)
            self.assertIn("Phê duyệt\nCấp ngân sách R&D", data["nodes"]["proc_ok"]["label"])
            for forbidden in ("<b>", "<br/>", "&amp;", "&lt;"):
                self.assertNotIn(forbidden, joined)

            # Atelier Technical Warm WCAG CSS + Open Sans + Vietnamese UI, zero legacy colors
            self.assertIn("Open Sans", html_txt)
            self.assertIn("#F8F6F2", html_txt)
            self.assertIn("#AD4333", html_txt)
            self.assertIn("Quay lại", html_txt)
            self.assertIn("Bắt đầu lại", html_txt)
            self.assertIn("Tiếp tục →", html_txt)
            for legacy in ("#82b366", "#0d99ff", "#889", "#d79b00", "#9673a6"):
                self.assertNotIn(legacy, html_txt.lower())

    def test_drawiohtml_viewer_wcag_and_vietnamese_locale(self):
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "s.json")
            dp = os.path.join(tmp, "s.drawio")
            hp = os.path.join(tmp, "nested", "viewer.html")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(_eval1_payment_retry_spec(), fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            r = _run_script("drawiohtml.py", [dp, "-o", hp], cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(hp, encoding="utf-8") as fh:
                html_txt = fh.read()
            self.assertIn('<html lang="vi">', html_txt)
            self.assertIn("Open Sans", html_txt)
            self.assertIn("#F8F6F2", html_txt)
            self.assertIn("#2B373E", html_txt)
            self.assertIn("#AD4333", html_txt)
            for legacy in ("#0d99ff", "#889", "#f6f7f9"):
                self.assertNotIn(legacy, html_txt.lower())

    def test_drawio_render_svg_html_readonly_png_and_missing_chrome(self):
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "s.json")
            ro_dir = os.path.join(tmp, "ro_in")
            os.makedirs(ro_dir)
            dp = os.path.join(ro_dir, "s.drawio")
            svg_p = os.path.join(tmp, "s.svg")
            html_p = os.path.join(tmp, "s.html")
            png_p = os.path.join(tmp, "s.png")

            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(_eval1_payment_retry_spec(), fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            r_svg = _run_script("drawio_render_svg.py", [dp, "-o", svg_p, "--html", html_p], cwd=tmp)
            self.assertEqual(r_svg.returncode, 0, r_svg.stderr)
            ET.parse(svg_p)
            self.assertTrue(os.path.isfile(html_p))

            # Missing Chrome on PATH exits non-zero cleanly without traceback
            r_no_chrome = _run_script(
                "drawio_render_svg.py",
                [dp, "--png", os.path.join(tmp, "nochrome.png")],
                cwd=tmp,
                env_override={"PATH": "/nonexistent"},
            )
            self.assertNotEqual(r_no_chrome.returncode, 0)
            self.assertNotIn("Traceback", r_no_chrome.stderr + r_no_chrome.stdout)

            # Read-only input dir (chmod 500) PNG export when Chrome/Chromium is available
            has_chrome = any(shutil.which(b) for b in ("google-chrome", "chromium", "chromium-browser"))
            if has_chrome:
                os.chmod(ro_dir, 0o500)
                try:
                    r_png = _run_script("drawio_render_svg.py", [dp, "--png", png_p], cwd=tmp)
                    self.assertEqual(r_png.returncode, 0, r_png.stderr)
                    self.assertTrue(os.path.isfile(png_p))
                    with open(png_p, "rb") as fh:
                        self.assertEqual(fh.read(8), b"\x89PNG\r\n\x1a\n")
                    self.assertEqual(os.listdir(ro_dir), ["s.drawio"])
                finally:
                    os.chmod(ro_dir, 0o700)

    def test_autolayout_palette_and_xml_rejection(self):
        self.assertTrue(autolayout._PALETTE_FILE.endswith(os.path.join("styles", "built-in", "tech-warm-light.json")))
        self.assertEqual(autolayout.PALETTE[0], ("#EEF2F5", "#2B373E"))
        self.assertIn("Open Sans", autolayout.NODE_STYLE)

        with tempfile.TemporaryDirectory() as tmp:
            bad_xml = os.path.join(tmp, "diagram.drawio")
            with open(bad_xml, "w", encoding="utf-8") as fh:
                fh.write("<mxfile><diagram id='p1' name='P1'><mxGraphModel><root/></mxGraphModel></diagram></mxfile>")
            r = _run_script("autolayout.py", [bad_xml, "-o", os.path.join(tmp, "out.drawio")], cwd=tmp)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr + r.stdout)
            self.assertIn("JSON", r.stderr + r.stdout)

    def test_drawio_cli_help_and_direct_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            r_help = _run_script("drawio_cli.py", ["--help"], cwd=tmp)
            self.assertEqual(r_help.returncode, 0, r_help.stderr)

            r_run = _run_script("drawio_cli.py", [], cwd=tmp)
            self.assertIn(r_run.returncode, (0, 1))
            self.assertNotIn("Traceback", r_run.stderr + r_run.stdout)

    def test_edgeports_spread_and_demo(self):
        with tempfile.TemporaryDirectory() as tmp:
            r_demo = _run_script("edgeports.py", ["--demo"], cwd=tmp)
            self.assertEqual(r_demo.returncode, 0, r_demo.stderr)
            self.assertIn("ok", r_demo.stdout.lower())

            # Synthetic diagram with 2 unpinned edges leaving right side of node A
            xml_str = """<mxfile><diagram id="p1" name="P1"><mxGraphModel><root>
              <mxCell id="0"/><mxCell id="1" parent="0"/>
              <mxCell id="a" value="A" style="rounded=0;" vertex="1" parent="1"><mxGeometry x="40" y="100" width="120" height="60" as="geometry"/></mxCell>
              <mxCell id="b" value="B" style="rounded=0;" vertex="1" parent="1"><mxGeometry x="300" y="40" width="120" height="60" as="geometry"/></mxCell>
              <mxCell id="c" value="C" style="rounded=0;" vertex="1" parent="1"><mxGeometry x="300" y="180" width="120" height="60" as="geometry"/></mxCell>
              <mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="a" target="b" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
              <mxCell id="e2" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="a" target="c" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
            </root></mxGraphModel></diagram></mxfile>"""
            in_p = os.path.join(tmp, "ports_in.drawio")
            out_p1 = os.path.join(tmp, "ports_out1.drawio")
            out_p2 = os.path.join(tmp, "ports_out2.drawio")
            with open(in_p, "w", encoding="utf-8") as fh:
                fh.write(xml_str)

            r1 = _run_script("edgeports.py", [in_p, "-o", out_p1], cwd=tmp)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            root = ET.parse(out_p1).getroot()
            ey = {}
            for c in root.iter("mxCell"):
                if c.get("id") in ("e1", "e2"):
                    ey[c.get("id")] = _extract_style_key(c.get("style"), "exitY")
            self.assertIsNotNone(ey["e1"])
            self.assertIsNotNone(ey["e2"])
            self.assertNotEqual(ey["e1"], ey["e2"], "Shared side ports should spread to distinct exitY values")

            # Idempotent re-run
            r2 = _run_script("edgeports.py", [out_p1, "-o", out_p2], cwd=tmp)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            with open(out_p1, "rb") as f1, open(out_p2, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())

    def test_shapesearch_external_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run_script("shapesearch.py", ["flowchart decision", "--limit", "5"], cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("mxgraph.flowchart.decision", r.stdout)

    def test_encode_drawio_url_viewer_and_edit_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, "s.json")
            dp = os.path.join(tmp, "s.drawio")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(_eval1_payment_retry_spec(), fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            r_view = _run_script("encode_drawio_url.py", [dp], cwd=tmp)
            self.assertEqual(r_view.returncode, 0, r_view.stderr)
            url_view = r_view.stdout.strip()
            self.assertIn("#R", url_view)
            # Round-trip inflate UTF-8 Vietnamese payload
            b64_part = urllib.parse.unquote(url_view.split("#R", 1)[1])
            inflated = zlib.decompress(base64.b64decode(b64_part), -zlib.MAX_WBITS).decode("utf-8")
            decoded_xml = urllib.parse.unquote(inflated)
            self.assertIn("Bắt đầu", decoded_xml)

            r_edit = _run_script("encode_drawio_url.py", ["--edit", dp], cwd=tmp)
            self.assertEqual(r_edit.returncode, 0, r_edit.stderr)
            url_edit = r_edit.stdout.strip()
            self.assertIn("#create=", url_edit)
            payload = json.loads(urllib.parse.unquote(url_edit.split("#create=", 1)[1]))
            self.assertEqual(payload["type"], "xml")
            self.assertTrue(payload["compressed"])

    def test_drawio2mermaid_explain_and_diagram_ir(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. Flowchart with title_banner, annotation, and preparation hexagon
            sp = os.path.join(tmp, "eval1.json")
            dp = os.path.join(tmp, "eval1.drawio")
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump(_eval1_payment_retry_spec(), fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [sp, "-o", dp], cwd=tmp).returncode, 0)

            r_mmd = _run_script("drawio2mermaid.py", [dp], cwd=tmp)
            self.assertEqual(r_mmd.returncode, 0, r_mmd.stderr)
            self.assertIn('(["Bắt đầu"])', r_mmd.stdout)
            self.assertNotIn("Lưu đồ Xử lý Thanh toán", r_mmd.stdout)
            self.assertNotIn("SLA cổng thanh toán", r_mmd.stdout)

            r_exp = _run_script("explain.py", [dp], cwd=tmp)
            self.assertEqual(r_exp.returncode, 0, r_exp.stderr)
            self.assertNotIn("Lưu đồ Xử lý Thanh toán", r_exp.stdout)
            self.assertNotIn("SLA cổng thanh toán", r_exp.stdout)
            self.assertIn("Khởi tạo biến đếm thử lại k = 0 _preparation_", r_exp.stdout)
            self.assertNotIn("Khởi tạo biến đếm thử lại k = 0 _queue_", r_exp.stdout)

            ir_flow = diagram_ir.load_ir(dp)
            node_map = {n["id"]: n for n in ir_flow["nodes"]}
            self.assertNotIn("title_banner", node_map)
            self.assertNotIn("note_sla", node_map)
            self.assertEqual(node_map["init_k"]["kind"], "preparation")

            # 2. 7-task CPM IR: 7 nodes, shortest_path & impact_analysis
            cpm_sp = os.path.join(tmp, "cpm.json")
            cpm_dp = os.path.join(tmp, "cpm.drawio")
            with open(cpm_sp, "w", encoding="utf-8") as fh:
                json.dump(_eval3_cpm_spec(), fh, ensure_ascii=False)
            self.assertEqual(_run_script("iso5807_builder.py", [cpm_sp, "-o", cpm_dp], cwd=tmp).returncode, 0)

            ir_cpm = diagram_ir.load_ir(cpm_dp)
            self.assertEqual(len(ir_cpm["nodes"]), 7)
            path = diagram_ir.shortest_path(ir_cpm, "A", "G")
            self.assertIsNotNone(path)
            self.assertEqual(path[0], "A")
            self.assertEqual(path[-1], "G")
            imp = diagram_ir.impact_analysis(ir_cpm, "B")
            impacted = set(imp.get("impacted", []))
            self.assertEqual(impacted, {"D", "F", "G"}, f"Unexpected impact_analysis result: {imp}")

    def test_repair_png_truncated_iend_and_idempotency(self):
        iend = b"\x00\x00\x00\x00IEND\xaeB`\x82"
        truncated = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (b"\x00" * 17) + b"\x00\x00\x00\x00"
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "broken.drawio.png")
            with open(p, "wb") as fh:
                fh.write(truncated)

            r1 = _run_script("repair_png.py", [p], cwd=tmp)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            with open(p, "rb") as fh:
                fixed = fh.read()
            self.assertTrue(fixed.endswith(iend))
            self.assertEqual(fixed, truncated[:-4] + iend)

            r2 = _run_script("repair_png.py", [p], cwd=tmp)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            with open(p, "rb") as fh:
                self.assertEqual(fh.read(), fixed)


class TestTrackBChartsAndMathPlotter(unittest.TestCase):
    """Covers Track B scripts: chart_builder, chart_verify (normal + adversarial), plot_math_svg."""

    def test_all_6_chart_types_in_both_themes_with_kpis_and_dark_deltas(self):
        kpis = [
            {"label": "Tăng trưởng", "value": "+18.4%", "delta": "+4.2pp YoY"},
            {"label": "Biến động chi phí", "value": "-12.0 tỷ", "delta": "-3.5% vs kế hoạch"},
        ]
        specs = {
            "bar": {
                "chart_type": "bar",
                "title": "Doanh thu theo Quý",
                "unit": " tỷ",
                "kpis": kpis,
                "data": [
                    {"label": "Q1", "value": 120},
                    {"label": "Q2", "value": 145},
                    {"label": "Q3", "value": 182, "focal": True},
                    {"label": "Q4", "value": 168},
                ],
            },
            "grouped_bar": {
                "chart_type": "grouped_bar",
                "title": "So sánh Kế hoạch & Thực tế",
                "unit": " tỷ",
                "kpis": kpis,
                "categories": ["Q1", "Q2", "Q3"],
                "series": [
                    {"name": "Kế hoạch", "values": [100, 120, 140]},
                    {"name": "Thực tế", "values": [108, 126, 152]},
                ],
            },
            "horizontal_bar": {
                "chart_type": "horizontal_bar",
                "title": "Biến động Hiệu suất (Phân kỳ Dương/Âm)",
                "unit": "%",
                "kpis": kpis,
                "data": [
                    {"label": "Tự động hóa SOP", "value": 24.5, "focal": True},
                    {"label": "Chi phí lưu trữ", "value": -14.2},
                    {"label": "Độ trễ xử lý", "value": -8.5},
                    {"label": "Năng suất R&D", "value": 16.0},
                ],
            },
            "line": {
                "chart_type": "line",
                "title": "Xu hướng Thông lượng Hệ thống",
                "unit": "k",
                "kpis": kpis,
                "categories": ["T1", "T2", "T3", "T4"],
                "series": [
                    {"name": "Cụm A", "values": [10, 18, 25, 34]},
                    {"name": "Cụm B", "values": [12, 15, 22, 29]},
                ],
            },
            "waterfall": {
                "chart_type": "waterfall",
                "title": "Biến động Chi phí Vận hành 2026",
                "unit": " tr",
                "kpis": kpis,
                "steps": [
                    {"label": "2025", "kind": "start", "value": 850},
                    {"label": "Quy mô", "kind": "delta", "value": 210},
                    {"label": "Lưu trữ lạnh", "kind": "delta", "value": -145},
                    {"label": "Tự động hóa", "kind": "delta", "value": -95},
                    {"label": "Bản quyền", "kind": "delta", "value": 40},
                    {"label": "2026", "kind": "total"},
                ],
            },
            "sankey": {
                "chart_type": "sankey",
                "title": "Dòng phân bổ Ngân sách CNTT",
                "unit": " tỷ",
                "kpis": kpis,
                "links": [
                    {"source": "Ngân sách", "target": "Hạ tầng", "value": 60},
                    {"source": "Ngân sách", "target": "R&D", "value": 40},
                    {"source": "Hạ tầng", "target": "Cloud", "value": 35},
                    {"source": "Hạ tầng", "target": "Bảo mật", "value": 25},
                    {"source": "R&D", "target": "Nền tảng dữ liệu", "value": 40},
                ],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            for theme in ("tech-warm-light", "tech-warm-dark"):
                for ctype, spec in specs.items():
                    sp = os.path.join(tmp, f"{ctype}_{theme}.json")
                    hp = os.path.join(tmp, f"{ctype}_{theme}.html")
                    svgp = os.path.join(tmp, f"{ctype}_{theme}.svg")
                    with open(sp, "w", encoding="utf-8") as fh:
                        json.dump(spec, fh, ensure_ascii=False)

                    r_b = _run_script("chart_builder.py", [sp, "--theme", theme, "-o", hp, "--svg", svgp], cwd=tmp)
                    self.assertEqual(r_b.returncode, 0, f"{ctype}/{theme} build failed: {r_b.stderr}")
                    ET.parse(svgp)

                    for target in (hp, svgp):
                        r_v = _run_script("chart_verify.py", [target, "--json"], cwd=tmp)
                        self.assertEqual(r_v.returncode, 0, f"{target} verify failed: {r_v.stdout}\n{r_v.stderr}")
                        rep = json.loads(r_v.stdout)
                        self.assertTrue(rep["passed"], rep["errors"])
                        self.assertEqual(rep["errors"], [])

                    if theme == "tech-warm-dark":
                        with open(hp, encoding="utf-8") as fh:
                            html_txt = fh.read()
                        self.assertIn("#E07A68", html_txt)
                        self.assertIn("#6EB5A3", html_txt)
                        self.assertNotIn("color:#AD4333", html_txt)
                        self.assertNotIn("color:#2D6A5B", html_txt)

    def test_adversarial_chart_verify_catches_all_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. HTML with no <svg> -> exit 1 cleanly, marks_verified == 0, no KeyError
            no_svg = os.path.join(tmp, "nosvg.html")
            with open(no_svg, "w", encoding="utf-8") as fh:
                fh.write("<!doctype html><html><body><p>Empty</p></body></html>")
            r0 = _run_script("chart_verify.py", [no_svg, "--json"], cwd=tmp)
            self.assertEqual(r0.returncode, 1)
            self.assertNotIn("Traceback", r0.stderr + r0.stdout)
            d0 = json.loads(r0.stdout)
            self.assertFalse(d0["passed"])
            self.assertEqual(d0["marks_verified"], 0)
            self.assertTrue(any("E-NO-SVG" in e for e in d0["errors"]))

            # 2. Distorted waterfall -> E-WATERFALL-PROPORTION
            bad_wf = os.path.join(tmp, "bad_wf.svg")
            with open(bad_wf, "w", encoding="utf-8") as fh:
                fh.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 300">'
                    '<rect x="0" y="0" width="600" height="300" fill="#F8F6F2"/>'
                    '<rect class="waterfall-step" data-label="S0" data-kind="start" data-start="0" data-end="100" data-value="100" x="50" y="200" width="40" height="5" fill="#2B373E"/>'
                    '<rect class="waterfall-step" data-label="D1" data-kind="delta" data-start="100" data-end="101" data-value="1" x="120" y="10" width="40" height="190" fill="#2D6A5B"/>'
                    '<rect class="waterfall-step" data-label="T1" data-kind="total" data-start="0" data-end="101" data-value="101" x="190" y="10" width="40" height="195" fill="#2B373E"/>'
                    '</svg>'
                )
            r_wf = chart_verify.verify_chart_file(bad_wf)
            self.assertFalse(r_wf["passed"])
            self.assertTrue(any("E-WATERFALL-PROPORTION" in e for e in r_wf["errors"]), r_wf["errors"])

            # 3. Non-linear monotonic line -> E-LINE-HONESTY
            bad_line = os.path.join(tmp, "bad_line.svg")
            with open(bad_line, "w", encoding="utf-8") as fh:
                fh.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 400">'
                    '<rect x="0" y="0" width="500" height="400" fill="#F8F6F2"/>'
                    '<circle class="chart-point" data-label="P1" data-value="0" cx="60" cy="350" r="4" fill="#2B373E"/>'
                    '<circle class="chart-point" data-label="P2" data-value="50" cx="200" cy="300" r="4" fill="#2B373E"/>'
                    '<circle class="chart-point" data-label="P3" data-value="100" cx="340" cy="50" r="4" fill="#2B373E"/>'
                    '</svg>'
                )
            r_ln = chart_verify.verify_chart_file(bad_line)
            self.assertFalse(r_ln["passed"])
            self.assertTrue(any("E-LINE-HONESTY" in e for e in r_ln["errors"]), r_ln["errors"])

            # 4. Non-conserved Sankey internal node -> E-SANKEY-CONSERVATION
            bad_sk = os.path.join(tmp, "bad_sk.svg")
            with open(bad_sk, "w", encoding="utf-8") as fh:
                fh.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 300">'
                    '<rect x="0" y="0" width="600" height="300" fill="#F8F6F2"/>'
                    '<path class="sankey-link" data-source="A" data-target="B" data-value="100" d="M10,10 L100,10" stroke="#2B373E"/>'
                    '<path class="sankey-link" data-source="B" data-target="C" data-value="60" d="M100,10 L200,10" stroke="#2B373E"/>'
                    '</svg>'
                )
            r_sk = chart_verify.verify_chart_file(bad_sk)
            self.assertFalse(r_sk["passed"])
            self.assertTrue(any("E-SANKEY-CONSERVATION" in e for e in r_sk["errors"]), r_sk["errors"])

            # 5. Wrong-direction negative horizontal bar -> E-HBAR-HONESTY
            bad_hb = os.path.join(tmp, "bad_hb.svg")
            with open(bad_hb, "w", encoding="utf-8") as fh:
                fh.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 300">'
                    '<rect x="0" y="0" width="600" height="300" fill="#F8F6F2"/>'
                    '<rect class="chart-hbar" data-label="Pos" data-value="20" data-zero-x="250" x="250" y="60" width="100" height="24" fill="#2B373E"/>'
                    '<rect class="chart-hbar" data-label="Neg" data-value="-10" data-zero-x="250" x="250" y="100" width="50" height="24" fill="#AD4333"/>'
                    '</svg>'
                )
            r_hb = chart_verify.verify_chart_file(bad_hb)
            self.assertFalse(r_hb["passed"])
            self.assertTrue(any("E-HBAR-HONESTY" in e for e in r_hb["errors"]), r_hb["errors"])

            # 6. Low-contrast SVG text -> E-WCAG-CONTRAST
            bad_svg_txt = os.path.join(tmp, "bad_contrast.svg")
            with open(bad_svg_txt, "w", encoding="utf-8") as fh:
                fh.write(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
                    '<rect x="0" y="0" width="400" height="200" fill="#EEEEEE"/>'
                    '<rect class="chart-bar" data-label="A" data-value="10" x="40" y="100" width="30" height="60" fill="#2B373E"/>'
                    '<text x="40" y="80" font-size="12" fill="#FFFFFF">Unreadable text</text>'
                    '</svg>'
                )
            r_ct1 = chart_verify.verify_chart_file(bad_svg_txt)
            self.assertFalse(r_ct1["passed"])
            self.assertTrue(any("E-WCAG-CONTRAST" in e for e in r_ct1["errors"]), r_ct1["errors"])

            # 7. Low-contrast dark KPI HTML -> E-WCAG-CONTRAST
            bad_kpi_html = os.path.join(tmp, "bad_dark_kpi.html")
            with open(bad_kpi_html, "w", encoding="utf-8") as fh:
                fh.write(
                    '<!doctype html><html><head><style>'
                    'body{background:#161C20;color:#F4F2EE}.kpi-card{background:#212A30}.kpi-delta{font-size:12px;color:#AD4333}'
                    '</style></head><body>'
                    '<div class="kpi-card"><div class="kpi-delta">-5%</div></div>'
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
                    '<rect x="0" y="0" width="400" height="200" fill="#161C20"/>'
                    '<rect class="chart-bar" data-label="A" data-value="10" x="40" y="50" width="30" height="100" fill="#B8C7D1"/>'
                    '</svg></body></html>'
                )
            r_ct2 = chart_verify.verify_chart_file(bad_kpi_html)
            self.assertFalse(r_ct2["passed"])
            self.assertTrue(any("E-WCAG-CONTRAST" in e for e in r_ct2["errors"]), r_ct2["errors"])

    def test_math_plotter_dark_html_singularities_security_and_wrapping_legend(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. Singularity 1/x with shade_area [-1, 1] + oblique asymptote + dark HTML wrapper
            sing_spec = {
                "title": "Khảo sát 1/x và Tiệm cận Xiên",
                "x_range": [-3, 3],
                "y_range": [-5, 5],
                "shade_area": {"expr": "1/x", "from": -1, "to": 1},
                "asymptotes": [{"x": 0}, {"expr": "1/(x - 0.5)"}],
                "functions": [{"expr": "1/x", "label": "y = 1/x"}],
            }
            sp1 = os.path.join(tmp, "sing.json")
            svg1 = os.path.join(tmp, "sing.svg")
            html1 = os.path.join(tmp, "sing.html")
            with open(sp1, "w", encoding="utf-8") as fh:
                json.dump(sing_spec, fh, ensure_ascii=False)
            r1 = _run_script("plot_math_svg.py", [sp1, "--theme", "tech-warm-dark", "-o", svg1, "--html", html1], cwd=tmp)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            root1 = ET.parse(svg1).getroot()
            shades = [el for el in root1.iter() if el.attrib.get("class") == "math-shade"]
            self.assertGreaterEqual(len(shades), 2, "1/x over [-1, 1] should emit split shade polygons across pole x=0")
            with open(html1, encoding="utf-8") as fh:
                htxt = fh.read()
            self.assertIn("</head>", htxt)
            self.assertIn("background:#161C20", htxt.replace(" ", ""))

            # 2. Caret '^' rejected cleanly advising '**'
            caret_sp = os.path.join(tmp, "caret.json")
            with open(caret_sp, "w", encoding="utf-8") as fh:
                json.dump({"title": "Caret", "functions": [{"expr": "x^2 + 1"}]}, fh)
            r_caret = _run_script("plot_math_svg.py", [caret_sp, "-o", os.path.join(tmp, "c.svg")], cwd=tmp)
            self.assertEqual(r_caret.returncode, 1)
            self.assertIn("**", r_caret.stderr)
            self.assertNotIn("Traceback", r_caret.stderr + r_caret.stdout)

            # 3. Malicious expression blocked with exit 1
            evil_sp = os.path.join(tmp, "evil.json")
            with open(evil_sp, "w", encoding="utf-8") as fh:
                json.dump({"title": "Evil", "functions": [{"expr": '__import__("os").system("id")'}]}, fh)
            r_evil = _run_script("plot_math_svg.py", [evil_sp, "-o", os.path.join(tmp, "e.svg")], cwd=tmp)
            self.assertEqual(r_evil.returncode, 1)
            self.assertNotIn("Traceback", r_evil.stderr + r_evil.stdout)

            # 4. 3 curves with long Vietnamese labels -> non-overlapping wrapping top legend
            leg_spec = {
                "title": "So sánh 3 Hàm số Kinh tế Lượng",
                "x_range": [-3, 3],
                "y_range": [-4, 4],
                "functions": [
                    {"expr": "sin(x)", "label": "Đường cung điều chỉnh theo mùa vụ quý I–IV"},
                    {"expr": "cos(x)", "label": "Đường cầu biên độ chuẩn hóa dài hạn"},
                    {"expr": "0.5*x", "label": "Xu hướng tuyến tính cơ sở cho năm kế hoạch 2026"},
                ],
            }
            svg_leg = plot_math_svg.render_math_plot_svg(leg_spec)
            leg_root = ET.fromstring(svg_leg)
            vb_parts = [float(x) for x in leg_root.attrib["viewBox"].split()]
            vb_w = vb_parts[2]
            clip_rect = next(
                el for el in leg_root.iter()
                if el.tag.endswith("clipPath") and el.attrib.get("id") == "math-plot-clip"
            )[0]
            plot_top = float(clip_rect.attrib["y"])
            legend_texts = [
                el for el in leg_root.iter()
                if el.tag.endswith("text") and el.text and any(k in el.text for k in ("Đường cung", "Đường cầu", "Xu hướng"))
            ]
            self.assertEqual(len(legend_texts), 3)
            for lt in legend_texts:
                self.assertLess(float(lt.attrib["y"]), plot_top, "Legend row overlaps plot frame")
                self.assertLess(float(lt.attrib["x"]), vb_w)

            # 5. Verbatim math snippet from references/quantitative-and-math-charts.md compiles cleanly
            ref_math_md = os.path.join(SKILL_DIR, "references", "quantitative-and-math-charts.md")
            with open(ref_math_md, encoding="utf-8") as fh:
                blocks = re.findall(r"```json\s*\n(.*?)\n```", fh.read(), flags=re.DOTALL)
            self.assertGreaterEqual(len(blocks), 2)
            math_ref_spec = json.loads(blocks[1])
            ref_svg = plot_math_svg.render_math_plot_svg(math_ref_spec)
            ET.fromstring(ref_svg)


class TestDesignSystemHygieneAndErrorHandling(unittest.TestCase):
    """Covers WCAG 2.1 tokens & secondary presets, clean CLI errors, stdlib-only AST & path hygiene."""

    def test_all_theme_tokens_and_builtin_presets_wcag_and_opensans(self):
        with open(os.path.join(SKILL_DIR, "data", "theme-tokens.json"), encoding="utf-8") as fh:
            tok = json.load(fh)
        for tname in ("tech-warm-light", "tech-warm-dark"):
            theme = tok["themes"][tname]
            self.assertEqual(len(theme["slots"]), 7)
            for sname, slot in theme["slots"].items():
                t_ratio = validate_iso5807._contrast_ratio(slot["fill"], slot["text"])
                self.assertGreaterEqual(t_ratio, 7.0, f"{tname}.{sname} text contrast {t_ratio:.2f} < 7.0")
                s_ratio = validate_iso5807._contrast_ratio(theme["canvas"], slot["stroke"])
                self.assertGreaterEqual(s_ratio, 4.5, f"{tname}.{sname} stroke contrast {s_ratio:.2f} < 4.5")

        # Verify all 4 built-in presets (tech-warm-{light,dark}, colorblind-safe, handdrawn)
        builtin_dir = os.path.join(SKILL_DIR, "styles", "built-in")
        remediated_aa_strokes = {
            ("colorblind-safe.json", "accent"),
            ("colorblind-safe.json", "secondary"),
            ("handdrawn.json", "warning"),
        }
        for fname in ("tech-warm-light.json", "tech-warm-dark.json", "colorblind-safe.json", "handdrawn.json"):
            with open(os.path.join(builtin_dir, fname), encoding="utf-8") as fh:
                preset = json.load(fh)
            self.assertEqual(preset["font"]["fontFamily"], "Open Sans", f"{fname} must use Open Sans")
            bg = preset["extras"]["background"]
            fg = preset["extras"]["fontColor"]
            is_atelier = fname.startswith("tech-warm-")
            min_text = 7.0 if is_atelier else 4.5
            for sname, pair in preset["palette"].items():
                if not pair:
                    continue
                r_txt = validate_iso5807._contrast_ratio(pair["fillColor"], fg)
                r_sc_bg = validate_iso5807._contrast_ratio(bg, pair["strokeColor"])
                r_sc_fill = validate_iso5807._contrast_ratio(pair["fillColor"], pair["strokeColor"])
                min_stroke = 4.5 if (is_atelier or (fname, sname) in remediated_aa_strokes) else 3.0
                self.assertGreaterEqual(r_txt, min_text, f"{fname}.{sname} text contrast {r_txt:.2f} < {min_text}")
                self.assertGreaterEqual(r_sc_bg, min_stroke, f"{fname}.{sname} stroke-vs-bg {r_sc_bg:.2f} < {min_stroke}")
                self.assertGreaterEqual(r_sc_fill, min_stroke, f"{fname}.{sname} stroke-vs-fill {r_sc_fill:.2f} < {min_stroke}")

    def test_clean_cli_errors_no_tracebacks_on_bad_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "does_not_exist.json")
            empty_json = os.path.join(tmp, "empty.json")
            bad_json = os.path.join(tmp, "bad.json")
            bad_xml = os.path.join(tmp, "bad.drawio")
            with open(empty_json, "w", encoding="utf-8") as fh:
                fh.write("{}")
            with open(bad_json, "w", encoding="utf-8") as fh:
                fh.write("{not valid json")
            with open(bad_xml, "w", encoding="utf-8") as fh:
                fh.write("<mxfile><broken")

            probes = [
                ("iso5807_builder.py", [missing, "-o", os.path.join(tmp, "o.drawio")]),
                ("iso5807_builder.py", [empty_json, "-o", os.path.join(tmp, "o.drawio")]),
                ("iso5807_builder.py", [bad_json, "-o", os.path.join(tmp, "o.drawio")]),
                ("validate_iso5807.py", [missing]),
                ("validate_iso5807.py", [bad_xml]),
                ("validate.py", [missing]),
                ("validate.py", [bad_xml]),
                ("relabel.py", [missing, "--extract"]),
                ("relabel.py", [bad_xml, "--extract"]),
                ("restyle.py", [missing, "--preset", "tech-warm-dark"]),
                ("restyle.py", [bad_xml, "--preset", "tech-warm-dark"]),
                ("runbook.py", [missing]),
                ("runbook.py", [bad_xml]),
                ("drawiohtml.py", [missing]),
                ("drawiohtml.py", [bad_xml]),
                ("drawio_render_svg.py", [missing]),
                ("drawio_render_svg.py", [bad_xml]),
                ("autolayout.py", [missing]),
                ("autolayout.py", [empty_json]),
                ("autolayout.py", [bad_json]),
                ("drawio2mermaid.py", [missing]),
                ("drawio2mermaid.py", [bad_xml]),
                ("explain.py", [missing]),
                ("explain.py", [bad_xml]),
                ("edgeports.py", [missing]),
                ("edgeports.py", [bad_xml]),
                ("encode_drawio_url.py", [missing]),
                ("repair_png.py", [missing]),
                ("chart_builder.py", [missing, "-o", os.path.join(tmp, "c.html")]),
                ("chart_builder.py", [empty_json, "-o", os.path.join(tmp, "c.html")]),
                ("chart_builder.py", [bad_json, "-o", os.path.join(tmp, "c.html")]),
                ("chart_verify.py", [missing]),
                ("plot_math_svg.py", [missing, "-o", os.path.join(tmp, "m.svg")]),
                ("plot_math_svg.py", [empty_json, "-o", os.path.join(tmp, "m.svg")]),
                ("plot_math_svg.py", [bad_json, "-o", os.path.join(tmp, "m.svg")]),
            ]
            for script_name, args in probes:
                r = _run_script(script_name, args, cwd=tmp)
                self.assertNotEqual(r.returncode, 0, f"{script_name} {args} unexpectedly exited 0")
                combined = r.stdout + r.stderr
                self.assertNotIn("Traceback", combined, f"{script_name} {args} leaked Traceback:\n{combined}")

    def test_all_20_scripts_stdlib_only_and_no_hardcoded_user_paths(self):
        actual_scripts = {f for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py")}
        self.assertEqual(actual_scripts, EXPECTED_SCRIPTS, f"Unexpected script set: {actual_scripts ^ EXPECTED_SCRIPTS}")

        sibling_modules = {os.path.splitext(f)[0] for f in EXPECTED_SCRIPTS}
        stdlib_names = set(sys.stdlib_module_names)
        py_files = [os.path.join(SCRIPTS_DIR, f) for f in sorted(EXPECTED_SCRIPTS)] + [os.path.abspath(__file__)]
        for path in py_files:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertIn(top, stdlib_names | sibling_modules, f"Non-stdlib import '{top}' in {path}")
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    top = node.module.split(".")[0]
                    self.assertIn(top, stdlib_names | sibling_modules, f"Non-stdlib import '{top}' in {path}")

        # Scan all non-binary skill files for hardcoded user/machine paths
        forbidden_tokens = [
            "/home/" + "antigravity",
            "/Users" + "/",
            "C:" + "\\",
            "/root" + "/",
            "devbox" + "://",
        ]
        for root_dir, dirs, files in os.walk(SKILL_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fn in files:
                if fn.endswith((".gz", ".pyc", ".png")):
                    continue
                fp = os.path.join(root_dir, fn)
                with open(fp, encoding="utf-8") as fh:
                    text = fh.read()
                for tok in forbidden_tokens:
                    self.assertNotIn(tok, text, f"Forbidden hardcoded path '{tok}' found in {fp}")

    def test_skill_docs_and_discovery_elicitation_links(self):
        """Verify all relative reference links in SKILL.md resolve and discovery guide covers all 5 tracks."""
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        with open(skill_md, encoding="utf-8") as fh:
            skill_txt = fh.read()
        ref_links = sorted(set(re.findall(r"references/[a-z0-9_-]+\.md", skill_txt)))
        self.assertIn("references/discovery-and-elicitation.md", ref_links)
        for rel in ref_links:
            target = os.path.join(SKILL_DIR, rel)
            self.assertTrue(os.path.isfile(target), f"Broken reference link in SKILL.md: {rel}")

        disc_path = os.path.join(SKILL_DIR, "references", "discovery-and-elicitation.md")
        with open(disc_path, encoding="utf-8") as fh:
            disc_txt = fh.read()
        for needle in (
            "Readiness Triage",
            "iso5807-flowchart",
            "swimlane-sop",
            "topological-graph",
            "quantitative-chart",
            "math-plot",
            "waterfall",
            "sankey",
            "ask_question",
        ):
            self.assertIn(needle, disc_txt, f"Missing discovery section/keyword: {needle}")

    def test_apache2_license_bundle_and_scope_naming_accuracy(self):
        """Verify full Apache-2.0 license text is bundled for shape-index.json.gz and BPMN is not oversold."""
        apache_path = os.path.join(SKILL_DIR, "data", "APACHE-2.0.txt")
        self.assertTrue(os.path.isfile(apache_path), "Missing bundled data/APACHE-2.0.txt per Apache-2.0 §4(a)")
        with open(apache_path, encoding="utf-8") as fh:
            apache_txt = fh.read()
        self.assertIn("Apache License", apache_txt)
        self.assertIn("Version 2.0, January 2004", apache_txt)
        self.assertIn("TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION", apache_txt)
        self.assertGreaterEqual(len(apache_txt.splitlines()), 190)

        for ref_file in (os.path.join(SKILL_DIR, "LICENSE"), os.path.join(SKILL_DIR, "data", "SHAPE-INDEX-NOTICE.md")):
            with open(ref_file, encoding="utf-8") as fh:
                self.assertIn("APACHE-2.0.txt", fh.read(), f"{ref_file} must reference APACHE-2.0.txt")

        for doc_file in (os.path.join(SKILL_DIR, "SKILL.md"), os.path.join(SKILL_DIR, "INSTALL_GUIDE.md")):
            with open(doc_file, encoding="utf-8") as fh:
                doc_txt = fh.read()
            self.assertNotIn("BPMN workflows", doc_txt)
            self.assertNotIn("Swimlane / BPMN", doc_txt)


if __name__ == "__main__":
    unittest.main()
