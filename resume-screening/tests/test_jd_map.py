"""jd_map 维度表加载（T04）。"""
from __future__ import annotations

from backend.persistence.jd_map import jd_text, load_jd_map

JD_YML = """roles:
  西安AE:
    position: 高级AE工程师
    skills: [react, paddleocr]
    red_lines: []
  后端:
    position: 后端开发
    skills: [python]
"""


def test_load_roles(tmp_path):
    f = tmp_path / "jd_map.yml"
    f.write_text(JD_YML, encoding="utf-8")
    m = load_jd_map(f)
    assert "西安AE" in m
    assert m["西安AE"]["position"] == "高级AE工程师"


def test_jd_text_renders_requirements(tmp_path):
    f = tmp_path / "jd_map.yml"
    f.write_text(JD_YML, encoding="utf-8")
    m = load_jd_map(f)
    text = jd_text(m["西安AE"])
    assert "高级AE工程师" in text
    assert "react" in text
    assert "paddleocr" in text
