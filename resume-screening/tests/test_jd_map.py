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


def test_jd_text_skips_non_string_skills(tmp_path):
    """防脏数据崩溃：skills 里混入映射/数字时跳过而非 TypeError。"""
    f = tmp_path / "jd_map.yml"
    f.write_text(
        "roles:\n"
        "  R:\n"
        "    position: P\n"
        '    skills: [{"岗位职责": null}, "react", 123]\n'
        '    red_lines: ["红线x"]\n',
        encoding="utf-8",
    )
    text = jd_text(load_jd_map(f)["R"])
    assert "react" in text
    assert "123" not in text
    assert "{" not in text
