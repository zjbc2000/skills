# 拆书成 Skill（Book Distiller）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个 `book-distiller` 元技能——给一本编程书（PDF / Markdown / 微信读书链接），产出"一书多 skill"（或按判别树产出 plugin）。

**Architecture:** `book-distiller/` 是一个 Claude Code skill 目录。核心是 `SKILL.md`（主工作流，指导 Claude 走"输入检测→结构分析→主题划分(检查点)→判别树→逐主题生成(检查点)→自检"六个阶段），配合 4 个 Python 脚本（提取/拉取/校验）和 4 个 reference 文档。脚本均可单元测试，SKILL.md 用 validate_skill.py 做 L0 校验，最后用一本样书走通全流程做端到端验证。

**Tech Stack:** Python 3.9、PyMuPDF 1.23.8（已装）、pytest 8.4.2（已装）、Playwright（微信读书导出器依赖，可选）、无 Node 依赖。

## Global Constraints

- 产出 skill **全中文**（frontmatter 的 name 除外，name 必须小写 kebab-case）。description 用中文写清 what + when + 触发词。
- **非 git 仓库**：`/Users/edy/Z-github/skills/` 不是 git 仓库。各任务末尾的 commit 步骤是**检查点**；若用户后续 `git init`，按步骤提交，否则跳过并记录进度即可。
- Python 3.9：注释用 `from __future__ import annotations`；不用 `match` 语句；不用 `X | None` 运行时语法。
- PyMuPDF 1.23.8 可用；**Docling 未安装**——v1 提取只用 PyMuPDF，Docling 作为可选 `--engine` 参数（未装则报错提示）。
- 所有脚本放在 `book-distiller/scripts/`，测试放 `book-distiller/tests/`，可被 `from validate_skill import ...` 方式导入（测试里 `sys.path` 指向 scripts/）。
- 微信读书导出器 `lbq110/weread-exporter` **不是本项目的代码**——`weread_fetch.py` 只是薄封装（解析 bookId → 调导出器 → 读产物），不实现 Canvas Hook。
- 不用超出设计文档的额外功能（YAGNI）。

---
## 文件结构

```
/Users/edy/Z-github/skills/book-distiller/
├── SKILL.md                       # 主工作流（Task 6 产出）
├── scripts/
│   ├── extract_text.py            # PDF → Markdown（PyMuPDF，Task 2）
│   ├── weread_fetch.py            # 微信读书：解析 bookId + 调导出器（Task 3）
│   ├── validate_skill.py          # L0 结构校验（Task 1）
│   └── validate_plugin.py         # plugin.json/marketplace.json 校验（Task 4）
├── references/
│   ├── skill-template.md          # 子 SKILL.md 模板（Task 5）
│   ├── discrimination-tree.md     # skill vs plugin 判别树（Task 5）
│   ├── book-types.md              # 书型→提取工具映射（Task 2）
│   └── weread-api.md              # 微信读书导出器用法 + 扫码机制 + 坑（Task 3）
├── tests/
│   ├── test_validate_skill.py
│   ├── test_extract_text.py
│   ├── test_weread_fetch.py
│   └── test_validate_plugin.py
└── outputs/                       # 拆书产出物（含 .gitkeep）
```

任务顺序依赖：validate_skill.py（Task 1）先于 SKILL.md（Task 6），因为它给 SKILL.md 做 L0 校验；extract_text（Task 2）、weread_fetch（Task 3）、validate_plugin（Task 4）彼此独立；SKILL.md 引用全部 scripts + references。

---

### Task 1: `scripts/validate_skill.py` — L0 结构校验器（TDD）

**Files:**
- Create: `book-distiller/scripts/validate_skill.py`
- Test: `book-distiller/tests/test_validate_skill.py`
- Create: `book-distiller/outputs/.gitkeep`（空目录占位）

**Interfaces:**
- Produces:
  - `validate_skill(path: Path) -> list[str]` — 返回错误信息列表，空列表 = 通过。`path` 指向一个 `SKILL.md`。
  - `main(argv=None) -> int` — CLI 入口，任一文件失败返回 1。
  - 校验规则：frontmatter 存在且合法；`name` 为小写 kebab-case（`^[a-z0-9]+(-[a-z0-9]+)*$`）；`name` 与父目录名一致；`description` 非空且 ≤1024 且无尖括号；正文里相对路径引用必须存在。
- Consumes: 无（本任务是地基，后续所有脚本与 SKILL.md 的校验都依赖它）。

- [ ] **Step 1: 创建 tests 目录与测试**

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_validate_skill.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'validate_skill'`

- [ ] **Step 3: 实现 validate_skill.py**

```python
# book-distiller/scripts/validate_skill.py
#!/usr/bin/env python3
"""L0 结构校验：frontmatter 合法性 + name/目录一致 + 引用可解析。

用法: python3 validate_skill.py <SKILL.md> [<SKILL.md> ...]
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    end = None
    for i, ln in enumerate(lines[1:], start=1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm: dict = {}
    for ln in lines[1:end]:
        if ":" in ln:
            k, _, v = ln.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def validate_skill(path: Path) -> list[str]:
    """返回错误列表；空列表 = 通过。path 指向 SKILL.md。"""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    if fm is None:
        return ["缺少合法 frontmatter（--- 包裹的 YAML）"]
    name = fm.get("name", "")
    if not NAME_RE.match(name):
        errors.append(f"name '{name}' 不合法：需小写 kebab-case")
    if name and name != path.parent.name:
        errors.append(f"name '{name}' 与目录名 '{path.parent.name}' 不一致")
    desc = fm.get("description", "")
    if not desc:
        errors.append("description 为空")
    elif len(desc) > 1024:
        errors.append(f"description 超长：{len(desc)}>1024")
    if "<" in desc or ">" in desc:
        errors.append("description 含尖括号")
    for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        ref = m.group(1)
        if ref.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / ref).resolve().exists():
            errors.append(f"引用不存在: {ref}")
    return errors


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="校验 SKILL.md 的 L0 结构")
    ap.add_argument("paths", nargs="+", metavar="SKILL.md")
    args = ap.parse_args(argv)
    all_ok = True
    for p in args.paths:
        errs = validate_skill(Path(p))
        if errs:
            all_ok = False
            print(f"{p}: {len(errs)} 个错误")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"{p}: OK")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_validate_skill.py -v`
Expected: 8 passed

- [ ] **Step 5: 创建 outputs/.gitkeep 并做检查点**

```bash
mkdir -p /Users/edy/Z-github/skills/book-distiller/outputs
touch /Users/edy/Z-github/skills/book-distiller/outputs/.gitkeep
```
Checkpoint（无 git 仓库，记录进度即可；若已 `git init` 则 `git add -A && git commit -m "feat: add L0 skill validator"`）。

---

### Task 2: `scripts/extract_text.py` — PDF → Markdown（TDD）+ `references/book-types.md`

**Files:**
- Create: `book-distiller/scripts/extract_text.py`
- Test: `book-distiller/tests/test_extract_text.py`
- Create: `book-distiller/references/book-types.md`

**Interfaces:**
- Produces:
  - `extract_toc(pdf_path: Path) -> list[dict]` — 每项 `{"level": int, "title": str, "page": int}`（读 PDF 内嵌书签）。
  - `extract_text(pdf_path: Path) -> str` — 每页文本按换行连接。
  - `pdf_is_scanned(pdf_path: Path, min_chars_per_page: int = 20) -> bool` — 平均每页字符数 < 阈值判为扫描版。
  - `extract_to_markdown(pdf_path: Path, out_md: Path) -> None` — 有书签则按章切分（`## 章名` 前缀），无书签则全文连成一段；写入 out_md。
- Consumes: 无（独立）。被 Task 6 的 SKILL.md 通过 `python3 scripts/extract_text.py <pdf> -o <out.md>` 调用。

- [ ] **Step 1: 写测试（用 PyMuPDF 生成迷你 PDF）**

```python
# book-distiller/tests/test_extract_text.py
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import fitz
from extract_text import extract_toc, extract_text, pdf_is_scanned, extract_to_markdown


def _gen_text_pdf(path: Path, with_toc: bool = True) -> None:
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 100), f"Chapter {i} content line one.")
        page.insert_text((72, 120), f"Some body text for page {i}.")
    if with_toc:
        doc.set_toc([[1, "Chapter 0", 1], [1, "Chapter 1", 2], [1, "Chapter 2", 3]])
    doc.save(str(path))
    doc.close()


def test_extract_toc(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    toc = extract_toc(p)
    assert len(toc) == 3
    assert toc[0] == {"level": 1, "title": "Chapter 0", "page": 1}


def test_extract_text(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    assert "Chapter 0 content" in extract_text(p)


def test_text_pdf_not_scanned(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    assert pdf_is_scanned(p) is False


def test_blank_pdf_is_scanned(tmp_path):
    p = tmp_path / "scanned.pdf"
    doc = fitz.open()
    doc.new_page()  # 无文字
    doc.save(str(p))
    doc.close()
    assert pdf_is_scanned(p) is True


def test_extract_to_markdown_with_toc(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    out = tmp_path / "book.md"
    extract_to_markdown(p, out)
    md = out.read_text(encoding="utf-8")
    assert "## Chapter 0" in md
    assert "## Chapter 2" in md


def test_extract_to_markdown_no_toc(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p, with_toc=False)
    out = tmp_path / "book.md"
    extract_to_markdown(p, out)
    assert "Chapter 0 content" in out.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_extract_text.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'extract_text'`

- [ ] **Step 3: 实现 extract_text.py**

```python
# book-distiller/scripts/extract_text.py
#!/usr/bin/env python3
"""PDF → Markdown：读内嵌书签做章节切分；检测扫描版提示换 MinerU。

用法: python3 extract_text.py <book.pdf> -o <out.md>
"""
from __future__ import annotations
import sys
from pathlib import Path

import fitz  # PyMuPDF


def extract_toc(pdf_path: Path) -> list[dict]:
    doc = fitz.open(str(pdf_path))
    toc = [{"level": level, "title": title, "page": page}
           for level, title, page in doc.get_toc()]
    doc.close()
    return toc


def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(parts)


def pdf_is_scanned(pdf_path: Path, min_chars_per_page: int = 20) -> bool:
    doc = fitz.open(str(pdf_path))
    total = sum(len(page.get_text()) for page in doc)
    n = len(doc)
    doc.close()
    return n > 0 and total / n < min_chars_per_page


def extract_to_markdown(pdf_path: Path, out_md: Path) -> None:
    doc = fitz.open(str(pdf_path))
    text_pages = [page.get_text() for page in doc]
    toc = doc.get_toc()
    doc.close()
    if not toc:
        body = "\n\n".join(text_pages)
    else:
        body = ""
        toc_pages = [t[2] for t in toc]
        for idx, (_level, title, page) in enumerate(toc):
            end = toc_pages[idx + 1] if idx + 1 < len(toc_pages) else len(text_pages) + 1
            seg = text_pages[page - 1:end - 1]
            body += f"\n\n## {title}\n\n" + "\n\n".join(seg)
    out_md.write_text(body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="PDF → Markdown")
    ap.add_argument("pdf", help="输入 PDF 路径")
    ap.add_argument("-o", "--out", required=True, help="输出 Markdown 路径")
    args = ap.parse_args(argv)
    src = Path(args.pdf)
    if pdf_is_scanned(src):
        print("检测到扫描版 PDF（无可提取文字）。请改用 MinerU 做 OCR，或人工提供 Markdown。", file=sys.stderr)
        return 1
    extract_to_markdown(src, Path(args.out))
    print(f"已输出: {args.out} (章节数: {len(extract_toc(src))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_extract_text.py -v`
Expected: 6 passed

- [ ] **Step 5: 写 references/book-types.md**

```markdown
# 书型 → 提取工具映射

| 书型 | 工具 | 说明 |
|---|---|---|
| 文本版（多数现代编程书） | PyMuPDF（默认） | 极快，`get_toc()` 读内嵌书签 |
| 技术书（代码/表格/公式多） | Docling（可选 `--engine docling`） | 保留 Markdown 表格代码块；需 `pip install docling` |
| 中文扫描版 / 复杂版式 | MinerU（提示，不在本脚本内） | 中文 OCR 最强，需 GPU；无 GPU 用 Marker |

## 使用规则
- 默认走 PyMuPDF。只有明确是技术书且需要保留表格/代码块时才用 Docling（本 v1 脚本支持 `--engine` 参数但未安装时明确报错）。
- 扫描版 PDF（`pdf_is_scanned` 检测）直接提示换 MinerU，不硬跑。
- 中文文本版若内嵌 ToUnicode 正常，PyMuPDF 可直接提取；异常时提示提供 Markdown。
```

- [ ] **Step 6: 检查点**

Checkpoint（无 git 仓库；若已 init 则 `git add -A && git commit -m "feat: add PDF to markdown extraction"`）。

---

### Task 3: `scripts/weread_fetch.py` — 微信读书薄封装（TDD）+ `references/weread-api.md`

**Files:**
- Create: `book-distiller/scripts/weread_fetch.py`
- Test: `book-distiller/tests/test_weread_fetch.py`
- Create: `book-distiller/references/weread-api.md`

**Interfaces:**
- Produces:
  - `parse_book_id(raw: str) -> str` — reader URL 取末段；裸 bookId 原样返回。
  - `detect_export_failure(output: str) -> str | None` — 在导出器 stdout/stderr 里匹配失败标记，返回匹配到的标记或 None。
  - `class WereadExportError(Exception)` — 导出失败/超时/找不到产物时抛。
  - `export_book(book_id: str, workdir: Path, exporter_script: Path) -> Path` — 用子进程调导出器，成功返回 `output/` 下合并后的 `书名.md` 路径；失败抛 `WereadExportError`。
- Consumes: 无（独立）。被 Task 6 的 SKILL.md 通过 `python3 scripts/weread_fetch.py <link>` 调用。

- [ ] **Step 1: 写测试（用假导出器脚本测失败分支，不依赖真实网络/Playwright）**

```python
# book-distiller/tests/test_weread_fetch.py
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from weread_fetch import (
    parse_book_id, detect_export_failure, export_book, WereadExportError,
)


def test_parse_book_id_from_url():
    assert parse_book_id("https://weread.qq.com/web/reader/abc123def") == "abc123def"


def test_parse_book_id_raw():
    assert parse_book_id("abc123def") == "abc123def"


def test_parse_book_id_trailing_slash():
    assert parse_book_id("https://weread.qq.com/web/reader/abc123def/") == "abc123def"


def test_detect_publisher_restriction():
    assert detect_export_failure("该书显示去 App 阅读") is not None


def test_detect_exported_ok():
    assert detect_export_failure("导出完成") is None


def test_export_book_publisher_restriction(tmp_path):
    fake = tmp_path / "fake_exporter.py"
    fake.write_text("print('显示去 App 阅读')\n", encoding="utf-8")
    with pytest.raises(WereadExportError):
        export_book("abc123", tmp_path, fake)


def test_export_book_missing_output(tmp_path):
    fake = tmp_path / "fake_exporter.py"
    fake.write_text("print('导出完成')\n", encoding="utf-8")  # 但 output/ 无产物
    with pytest.raises(WereadExportError):
        export_book("abc123", tmp_path, fake)


def test_export_book_success(tmp_path):
    fake = tmp_path / "fake_exporter.py"
    fake.write_text("print('导出完成')\n", encoding="utf-8")
    out = tmp_path / "output"
    out.mkdir()
    (out / "书名.md").write_text("# 书名", encoding="utf-8")
    result = export_book("abc123", tmp_path, fake)
    assert result.name == "书名.md"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_weread_fetch.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'weread_fetch'`

- [ ] **Step 3: 实现 weread_fetch.py**

```python
# book-distiller/scripts/weread_fetch.py
#!/usr/bin/env python3
"""微信读书薄封装：解析 bookId → 调 lbq110/weread-exporter 导出全本 → 返回合并 Markdown。

用法: python3 weread_fetch.py <reader链接或bookId>

依赖（可选）：Playwright + Chromium，首次运行弹出浏览器扫码登录。
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

EXPORT_TIMEOUT_SECONDS = 14400  # 4 小时，整本书导出可能很久
FAILURE_MARKERS = [
    "去 App 阅读",
    "需要有效的微信读书账号",
    "无法导出",
    "登录失败",
    "登录超时",
]


class WereadExportError(Exception):
    """导出失败/超时/找不到产物。"""


def parse_book_id(raw: str) -> str:
    """从 reader URL 或裸 bookId 解析。"""
    s = raw.strip().rstrip("/")
    if "weread.qq.com" in s:
        return s.rsplit("/", 1)[-1]
    return s


def detect_export_failure(output: str) -> str | None:
    """在导出器输出里匹配失败标记。"""
    for marker in FAILURE_MARKERS:
        if marker in output:
            return marker
    return None


def export_book(book_id: str, workdir: Path, exporter_script: Path) -> Path:
    """调导出器，返回 output/ 下合并后的 书名.md；失败抛 WereadExportError。"""
    try:
        proc = subprocess.run(
            [sys.executable, str(exporter_script), book_id],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=EXPORT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise WereadExportError("导出超时（超过 4 小时）")
    output = (proc.stdout or "") + (proc.stderr or "")
    marker = detect_export_failure(output)
    if marker:
        raise WereadExportError(f"导出失败：{marker}")
    merged = sorted((workdir / "output").glob("*.md"))
    if not merged:
        raise WereadExportError("导出完成但未找到合并后的 Markdown 产物")
    return merged[0]


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="微信读书全本导出（薄封装）")
    ap.add_argument("input", help="微信读书 reader 链接或 bookId")
    ap.add_argument("--exporter", default="export_precise.py",
                    help="lbq110/weread-exporter 的 export_precise.py 路径")
    ap.add_argument("--workdir", default=".",
                    help="导出工作目录（export_precise.py 所在目录）")
    args = ap.parse_args(argv)
    book_id = parse_book_id(args.input)
    print(f"Book ID: {book_id}")
    try:
        result = export_book(book_id, Path(args.workdir), Path(args.exporter))
    except WereadExportError as e:
        print(f"✗ {e}", file=sys.stderr)
        print("请提供 PDF/Markdown，或换正版 DRM-free 电子书路径。", file=sys.stderr)
        return 1
    print(f"✅ 导出完成: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_weread_fetch.py -v`
Expected: 8 passed

- [ ] **Step 5: 写 references/weread-api.md**

```markdown
# 微信读书导出（强制全文）

拆书 skill 的微信读书路径 = **强制全文导出**，拿不到全文就停下提示换源，不降级到划线骨架。

## 机制
- 导出器（`lbq110/weread-exporter` 的 `export_precise.py`）用 **Playwright 启动有头（headless=False）Chromium 真窗口**。
- **扫码登录**：打开 weread.qq.com/web/shelf，未登录则停在登录页等用户扫码（每 5 秒轮询 URL，最长 10 分钟）。会话持久化在 `cache/browser_profile/`，**扫码只需一次**。
- 翻页方式：原生点击目录首项跳全书开头 → `ArrowRight` 逐页翻 → 目录比对判断末尾 → 自动停止；中途卡住自动重开续传。

## 使用规则（SKILL.md 执行）
1. 首次使用**必须提示用户**"会有浏览器窗口弹出，请扫码登录微信读书"。
2. 前置：`pip install playwright && playwright install chromium`。
3. 导出是长任务（整本书 30 分钟至数小时），需耐心等待；`export_book` 超时 4 小时。
4. 失败场景（出版社限制"去 App 阅读"、无权限、无 Chromium）→ 停下提示换源：提供 PDF/Markdown 或换正版电子书。**绝不降级到官方 API 划线骨架**（官方 API 无正文，仅可用于把书名解析成 reader 链接）。

## 坑
- 导出器约 1-2 秒/页；Cookie 会过期需重新扫码；账号可能被风控，仅供个人自用。
- Canvas Hook 导出有断行拼接痕迹，蒸馏前需清理。
- 纯图廊章节图片密集时图注与图配对偶差一位。
```

- [ ] **Step 6: 检查点**

Checkpoint（无 git 仓库；若已 init 则 `git add -A && git commit -m "feat: add weread full-text export wrapper"`）。

---

### Task 4: `scripts/validate_plugin.py` — plugin 结构校验（TDD）

**Files:**
- Create: `book-distiller/scripts/validate_plugin.py`
- Test: `book-distiller/tests/test_validate_plugin.py`

**Interfaces:**
- Produces:
  - `validate_plugin_json(data: dict) -> list[str]` — 校验 name(kebab-case)/version(SemVer)/description/author.name。
  - `validate_marketplace_json(data: dict) -> list[str]` — 校验 name/owner/plugins 字段存在。
  - `validate_plugin(plugin_dir: Path) -> list[str]` — 读 `.claude-plugin/plugin.json`（必需）+ `marketplace.json`（可选），汇总错误；文件缺失/JSON 非法返回错误。
- Consumes: 无。被 Task 6 的 SKILL.md 在 plugin 形态时调用 `python3 scripts/validate_plugin.py <dir>`。

- [ ] **Step 1: 写测试**

```python
# book-distiller/tests/test_validate_plugin.py
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from validate_plugin import validate_plugin, validate_plugin_json, validate_marketplace_json

VALID_PLUGIN = {
    "name": "my-plugin",
    "version": "0.1.0",
    "description": "测试插件",
    "author": {"name": "edy"},
}


def _make_plugin_dir(tmp_path, plugin: dict | None = VALID_PLUGIN,
                     marketplace: dict | None = None) -> Path:
    d = tmp_path / "p"
    (d / ".claude-plugin").mkdir(parents=True)
    if plugin is not None:
        (d / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(plugin, ensure_ascii=False), encoding="utf-8")
    if marketplace is not None:
        (d / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps(marketplace, ensure_ascii=False), encoding="utf-8")
    return d


def test_valid_plugin_passes(tmp_path):
    assert validate_plugin(_make_plugin_dir(tmp_path)) == []


def test_missing_plugin_json(tmp_path):
    assert validate_plugin(_make_plugin_dir(tmp_path, plugin=None)) != []


def test_bad_plugin_name(tmp_path):
    d = _make_plugin_dir(tmp_path, {**VALID_PLUGIN, "name": "My_Plugin"})
    assert validate_plugin_json({"name": "My_Plugin"}) != []
    assert validate_plugin(d) != []


def test_missing_author(tmp_path):
    d = _make_plugin_dir(tmp_path, {"name": "my-plugin", "version": "0.1.0"})
    assert validate_plugin(d) != []


def test_bad_version(tmp_path):
    assert validate_plugin_json({**VALID_PLUGIN, "version": "0.1"}) != []


def test_marketplace_missing_fields(tmp_path):
    assert validate_marketplace_json({"name": "x"}) != []


def test_valid_marketplace_passes(tmp_path):
    mp = {"name": "mk", "owner": "edy", "plugins": [{"name": "my-plugin"}]}
    assert validate_marketplace_json(mp) == []
    assert validate_plugin(_make_plugin_dir(tmp_path, marketplace=mp)) == []


def test_invalid_json(tmp_path):
    d = tmp_path / "p"
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin" / "plugin.json").write_text("{not json", encoding="utf-8")
    assert validate_plugin(d) != []
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_validate_plugin.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'validate_plugin'`

- [ ] **Step 3: 实现 validate_plugin.py**

```python
# book-distiller/scripts/validate_plugin.py
#!/usr/bin/env python3
"""plugin 结构校验：plugin.json / marketplace.json 合法性。

用法: python3 validate_plugin.py <plugin_dir>
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

PLUGIN_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")


def validate_plugin_json(data: dict) -> list[str]:
    errors: list[str] = []
    name = data.get("name", "")
    if not PLUGIN_NAME_RE.match(name):
        errors.append(f"plugin name '{name}' 不合法：需小写 kebab-case")
    version = data.get("version", "")
    if version and not SEMVER_RE.match(version):
        errors.append(f"version '{version}' 非 SemVer")
    if not data.get("description"):
        errors.append("description 为空")
    author = data.get("author")
    if not isinstance(author, dict) or not author.get("name"):
        errors.append("author.name 缺失")
    return errors


def validate_marketplace_json(data: dict) -> list[str]:
    errors: list[str] = []
    for field in ("name", "owner", "plugins"):
        if not data.get(field):
            errors.append(f"marketplace 缺字段: {field}")
    return errors


def validate_plugin(plugin_dir: Path) -> list[str]:
    """读 .claude-plugin/plugin.json（必需）+ marketplace.json（可选）并校验。"""
    errors: list[str] = []
    plugin_file = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_file.exists():
        return [".claude-plugin/plugin.json 缺失"]
    try:
        data = json.loads(plugin_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"plugin.json 不是合法 JSON: {e}"]
    errors += validate_plugin_json(data)
    marketplace_file = plugin_dir / ".claude-plugin" / "marketplace.json"
    if marketplace_file.exists():
        try:
            mdata = json.loads(marketplace_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"marketplace.json 不是合法 JSON: {e}")
        else:
            errors += validate_marketplace_json(mdata)
    return errors


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="校验 plugin 结构")
    ap.add_argument("dirs", nargs="+", metavar="plugin_dir")
    args = ap.parse_args(argv)
    all_ok = True
    for d in args.dirs:
        errs = validate_plugin(Path(d))
        if errs:
            all_ok = False
            print(f"{d}: {len(errs)} 个错误")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"{d}: OK")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/test_validate_plugin.py -v`
Expected: 8 passed

- [ ] **Step 5: 检查点**

Checkpoint（无 git 仓库；若已 init 则 `git add -A && git commit -m "feat: add plugin structure validator"`）。

---

### Task 5: `references/skill-template.md` + `references/discrimination-tree.md`

**Files:**
- Create: `book-distiller/references/skill-template.md`
- Create: `book-distiller/references/discrimination-tree.md`

**Interfaces:**
- Produces: 两个 reference 文档，被 Task 6 的 SKILL.md 在 Stage 4（判别树）和 Stage 5（子 skill 模板）时引用。
- Consumes: 无（纯文档，但内容与设计文档 5.5 节完全一致，需与 Task 6 的 SKILL.md 措辞呼应）。

- [ ] **Step 1: 写 discrimination-tree.md**

```markdown
# skill vs plugin 判别树

判断一本书的产出该走 skill 形态还是 plugin 形态：

```
Q1 干货是程序性知识（方法论/清单/领域规则）吗？
├─ 否（靠外部工具/数据）→ 需要 MCP server → plugin 形态
└─ 是 → Q2

Q2 需要 hooks（事件自动执行）/ 子代理 / 多命令分发吗？
├─ 是 → plugin 形态
└─ 否 → Q3

Q3 要分发（团队/社区/版本化）吗？
├─ 是 → plugin 形态（+ marketplace.json）
└─ 否 → skill 形态（裸 skill）
```

## 要点
- **skill 优先，plugin 是升级路径**。纯方法论书（Clean Code 这类）默认 skill 形态。
- 判别树结果在检查点1 时展示给用户，用户可改判。
- plugin 形态时：`SKILL.md` 移入 `skills/`，新增 `.claude-plugin/plugin.json`（必需）+ 可选 `marketplace.json`/`agents/`/`hooks/`/`.mcp.json`，用 `validate_plugin.py` 校验。
```

- [ ] **Step 2: 写 skill-template.md**

```markdown
# 子 Skill 模板

拆书产出的每个主题子 skill 按此模板生成。**全中文**（除 name 外的 frontmatter 值）。

## frontmatter

```yaml
---
name: "<kebab-case，小写，与目录名一致>"
description: "<全中文。写清 what（做什么）+ when（何时用）+ 触发关键词，至少一句。>"
---
```

## 正文结构（三明治）

```markdown
# <主题名>

## 何时使用
- <触发场景，用户说什么时用这个 skill>

## 核心规则
- <从书中提取的可执行规则，每条标注 来源：第N章>

## 检查清单
- [ ] <可勾选的检查项，供执行时自查>
```

## 规则
1. **不抄原文**：规则用自己的话提炼，保留出处标注（`来源：第N章`）防幻觉。
2. **密度优先**：宁要 5 条真规则，不要 20 条泛泛而谈。
3. **实践者视角**：写成"When X use Y"，不是教材式定义。
4. 产出后用 `validate_skill.py` 校验每个 SKILL.md。
```

> 注意：上面正文结构示例里的内层 ``` 围栏仅作示意；实际生成文件时按"标题 + 分节"组织，不加多余的嵌套围栏。

- [ ] **Step 3: 检查点**

Checkpoint（无 git 仓库；若已 init 则 `git add -A && git commit -m "docs: add skill template and discrimination tree"`）。

---

### Task 6: `SKILL.md` — 主工作流

**Files:**
- Create: `book-distiller/SKILL.md`

**Interfaces:**
- Consumes: Task 1 `validate_skill.py`（CLI）、Task 2 `extract_text.py`（CLI）、Task 3 `weread_fetch.py`（CLI）、Task 4 `validate_plugin.py`（CLI）、Task 5 `references/skill-template.md` 和 `discrimination-tree.md`。
- Produces: 拆书 skill 的入口指令——Claude 加载它后按六阶段执行，产出 `outputs/<book-slug>/`。自身必须通过 `validate_skill.py`（name 为 `book-distiller` 与目录一致）。

- [ ] **Step 1: 写 SKILL.md**

```markdown
---
name: "book-distiller"
description: "把编程书籍（PDF / Markdown / 微信读书链接）拆解为可复用的 agent skill 或 plugin。当用户给一本书的 PDF、Markdown 文件或微信读书链接，并希望把书整理成 skill、拆书、转成技能、生成 plugin 时使用。"
---

# 拆书成 Skill（Book Distiller）

把一本软件 / AI-coding 相关书籍蒸馏成可复用的 agent 技能。简单书产出 skill 形态；复杂书（需要 hooks / MCP / 子代理 / 分发）产出 plugin 形态。

## 何时使用

- 用户给一本书（PDF、Markdown 或微信读书链接）并说"整理成 skill / 拆书 / 变成技能 / 生成 plugin"。
- 用户要给一本工具书写出 agent 可直接调用的方法论技能包。

## 输入三种路径

| 输入 | 处理 |
|---|---|
| PDF | `python3 scripts/extract_text.py <pdf> -o <out.md>`；扫描版会提示换 MinerU |
| Markdown | 直接用 |
| 微信读书链接/书名 | `python3 scripts/weread_fetch.py <链接>`（强制全文导出） |

微信读书路径**首次使用必须提示用户**"会有浏览器窗口弹出，请扫码登录微信读书"；导出是长任务（整本书 30 分钟至数小时）。导出失败（出版社限制等）→ **停下提示换源**，不降级到官方 API 划线骨架。

## 流程

### Stage 1: 输入检测
- 判断输入类型，按上表统一成干净 Markdown + 章节树。清理 Canvas 导出的断行拼接痕迹。

### Stage 2: 结构分析
- 用 Markdown 标题层级（或 PDF 书签 TOC）识别章节边界。
- 每章读原文，生成 800–1200 token 摘要（map）：**密度优先、实践者视角（When X use Y）、不抄原文**。

### Stage 3: 主题划分 ★检查点1
- LLM 基于全部章摘要提出 3–10 个主题清单，展示给用户。
- **强制停下**：用户确认/增删/合并后才继续。

### Stage 4: 判别树（检查点1 顺带确认）
- 按 `references/discrimination-tree.md` 判定 skill 还是 plugin 形态，把判定结果展示给用户，用户可改判。

### Stage 5: 逐主题生成子 skill ★检查点2
- 按 `references/skill-template.md` 逐主题生成子 `SKILL.md`。
- **强制停下**：生成首个样例后让用户确认格式，其余自动跑。

### Stage 6: 自检与交付
- 运行 `python3 scripts/validate_skill.py outputs/<book-slug>/*/SKILL.md` 校验所有子 skill。
- plugin 形态额外运行 `python3 scripts/validate_plugin.py outputs/<book-slug>`。
- 产出汇总报告：主题清单、各 skill 说明、覆盖范围、下一步建议。

## 产出物结构

```
outputs/<book-slug>/
├── SKILL.md          # 总入口：frontmatter + 全书心智模型 + 主题决策树（场景 → 调哪个子 skill）
├── <topic>/SKILL.md  # 各主题子 skill（每个独立可触发）
└── references/       # 章节精要，子 skill 深入时按需加载
```

plugin 形态时：上述内容移入 `skills/`，新增 `.claude-plugin/plugin.json`（+ 可选 `marketplace.json`/`agents/`/`hooks/`/`.mcp.json`）。

## 注意事项

- 产出全部**全中文**（除 name 外），description 写清 what + when + 触发词。
- 每条关键结论标注 `来源：第N章`，可回溯、防幻觉。
- 一书多 skill 的子 skill 边界由**主题**决定，不由章节顺序决定。
```

- [ ] **Step 2: 校验 SKILL.md 通过 L0**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 scripts/validate_skill.py SKILL.md`
Expected: `SKILL.md: OK`

- [ ] **Step 3: 跑全量测试确认无回归**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 -m pytest tests/ -v`
Expected: 30 passed（8+6+8+8）

- [ ] **Step 4: 检查点**

Checkpoint（无 git 仓库；若已 init 则 `git add -A && git commit -m "feat: add book-distiller main workflow skill"`）。

---

### Task 7: 端到端验证 — 样书走通全流程

**Files:**
- Create: `book-distiller/outputs/sample-book.md`（样书，仅作 E2E 验证，可删）
- Create（执行产出）: `book-distiller/outputs/sample-book/`（SKILL.md + 子 skill + references）

**Interfaces:**
- Consumes: Task 6 的完整 SKILL.md + 全部 scripts + references。
- Produces: 一个真实走通流程的 `outputs/sample-book/`，证明 skill 可用；其子 SKILL.md 通过 `validate_skill.py`。

- [ ] **Step 1: 准备样书 Markdown**

```bash
mkdir -p /Users/edy/Z-github/skills/book-distiller/outputs/sample-book
cat > /Users/edy/Z-github/skills/book-distiller/outputs/sample-book.md <<'EOF'
# 示例书：代码命名入门

**示例作者**

---

## 第一章 为什么要好好命名

好的命名是代码可读性的基础。变量名应该表达意图，而不是靠注释来补充。

## 第二章 命名规范

函数名用动词开头。布尔变量用 is/has 开头。避免无意义缩写。

## 第三章 常见错误

不要用 a、b、tmp 这种名字。不要缩写到没人看得懂。
EOF
```

- [ ] **Step 2: 按 SKILL.md 流程执行 Stage 1-2**

以 `outputs/sample-book.md` 为输入，走输入检测 + 结构分析：识别 3 章，每章生成 800–1200 token 摘要。

- [ ] **Step 3: 走 Stage 3 主题划分 + Stage 4 判别树（含两个检查点）**

预期：LLM 提出 1 个主题（命名规范）或经用户确认合并；判别树判定该纯方法论书为 **skill 形态**（无 hooks/MCP/子代理/分发需求）。

- [ ] **Step 4: 走 Stage 5 生成子 skill**

按 `references/skill-template.md` 生成 `outputs/sample-book/naming/SKILL.md`（全中文，含 `来源：第N章` 标注 + 检查清单）。

- [ ] **Step 5: 走 Stage 6 自检**

Run: `cd /Users/edy/Z-github/skills/book-distiller && python3 scripts/validate_skill.py outputs/sample-book/naming/SKILL.md`
Expected: `OK`（或修复后通过）

- [ ] **Step 6: 检查点 + 收尾**

- 确认 `outputs/sample-book/` 结构完整（总入口 SKILL.md + 子 skill + references）。
- 确认全部脚本测试仍通过（`python3 -m pytest tests/ -v` → 30 passed）。
- Checkpoint（无 git 仓库；若已 init 则 `git add -A && git commit -m "test: e2e sample book distillation"`）。

---

## Self-Review 记录

**Spec 覆盖检查：**
- 输入三路径（PDF/Markdown/微信读书）→ Task 2、Task 3 + SKILL.md Stage 1。✓
- 结构分析 map-reduce → SKILL.md Stage 2。✓
- 主题划分检查点1 → SKILL.md Stage 3。✓
- 判别树（skill vs plugin）→ Task 5 discrimination-tree.md + SKILL.md Stage 4。✓
- 逐主题生成检查点2 → Task 5 skill-template.md + SKILL.md Stage 5。✓
- 自检 + 交付 → Task 1/4 脚本 + SKILL.md Stage 6。✓
- 微信读书强制全文、失败停下换源、扫码登录机制 → Task 3 + references/weread-api.md。✓
- 三明治结构子 skill、来源可回溯、全中文 → Task 5 + SKILL.md 注意事项。✓
- TDD 验证栈 L0/L2/E2E → Task 1/4（结构校验）、Task 7（端到端）。✓
- plugin 形态产物（plugin.json/marketplace.json 骨架）→ Task 4 validate_plugin + SKILL.md 产出物结构。✓

**占位符扫描：** 无 TBD/TODO；所有代码步骤含完整代码。✓

**类型一致性：** `validate_skill(path: Path) -> list[str]`、`parse_book_id(raw: str) -> str`、`export_book(...) -> Path`、`validate_plugin(plugin_dir: Path) -> list[str]` 在各任务间签名一致。Task 3 测试用的 `export_book("abc123", tmp_path, fake)` 与实现签名 `(book_id: str, workdir: Path, exporter_script: Path) -> Path` 一致。✓
