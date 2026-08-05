# book-distiller/tests/test_validate_skill.py
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate_skill import validate_skill

VALID = """---
name: "test-skill"
description: "对测试技能做X。当用户提到测试时使用。"
---

# 测试技能

正文内容。
"""


def write_skill(tmp_path, body: str) -> Path:
    p = tmp_path / "test-skill" / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def test_valid_skill_passes(tmp_path):
    p = write_skill(tmp_path, VALID)
    assert validate_skill(p) == []


def test_missing_frontmatter(tmp_path):
    p = write_skill(tmp_path, "# 没有 frontmatter\n")
    assert validate_skill(p) != []


def test_bad_name(tmp_path):
    p = write_skill(tmp_path, VALID.replace('"test-skill"', '"Test_Skill"'))
    assert validate_skill(p) != []


def test_name_mismatch_dir(tmp_path):
    p = write_skill(tmp_path, VALID.replace('"test-skill"', '"other-name"'))
    assert validate_skill(p) != []


def test_description_too_long(tmp_path):
    p = write_skill(tmp_path, VALID.replace("对测试技能做X。当用户提到测试时使用。", "长" * 1100))
    assert validate_skill(p) != []


def test_description_empty(tmp_path):
    p = write_skill(tmp_path, VALID.replace("对测试技能做X。当用户提到测试时使用。", ""))
    assert validate_skill(p) != []


def test_description_has_angle_bracket(tmp_path):
    p = write_skill(tmp_path, VALID.replace("对测试技能做X。当用户提到测试时使用。", "含有<尖括号>的描述"))
    assert validate_skill(p) != []


def test_reference_to_missing_file(tmp_path):
    body = VALID + "\n见 [缺失文件](references/nope.md)\n"
    p = write_skill(tmp_path, body)
    assert validate_skill(p) != []


def test_bare_filename_matches_cwd_dir(tmp_path, monkeypatch):
    # 以相对文件名调用（如 scripts/validate_skill.py SKILL.md）时，
    # name 应与文件所在目录一致，而不是与空串比较。
    p = write_skill(tmp_path, VALID)
    monkeypatch.chdir(p.parent)
    assert validate_skill(Path("SKILL.md")) == []
