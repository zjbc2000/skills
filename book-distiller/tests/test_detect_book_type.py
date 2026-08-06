# book-distiller/tests/test_detect_book_type.py
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from detect_book_type import detect_book_type


def test_text_book():
    text = "\n".join(
        ["# 第一章", "这是一个纯文字段落，讲述方法论。", "另一个段落，没有代码。"],
    )
    assert detect_book_type(text)["book_type"] == "text"


def test_technical_code_dense():
    text = "\n".join(
        [
            "# 第一章",
            "```python",
            "def hello():",
            "    return 1",
            "```",
            "```sql",
            "SELECT * FROM t;",
            "```",
        ]
    )
    assert detect_book_type(text)["book_type"] == "technical"


def test_technical_many_tables():
    rows = ["| 名称 | 用途 |", "|---|---|"] + [f"| 工具{i} | 部署 |" for i in range(25)]
    text = "# 第3章\n" + "\n".join(rows)
    assert detect_book_type(text)["book_type"] == "technical"


def test_technical_math():
    text = "# 第1章\n" + "公式 $$E=mc^2$$。\n" * 12
    assert detect_book_type(text)["book_type"] == "technical"


def test_mixed_light_code():
    # 少量代码，未到 technical 阈值，也未纯 text：1 行代码 + 60 行正文 ≈ 0.016
    text = "\n".join(
        [
            "# 第2章",
            "```python",
            "x = 1",
            "```",
            *[f"这是正文段落 {i}，没有表格和公式。" for i in range(60)],
        ]
    )
    assert detect_book_type(text)["book_type"] == "mixed"


def test_fence_toggle_handles_multiple_blocks():
    text = "\n".join(
        [
            "```js",
            "const a = 1;",
            "const b = 2;",
            "```",
            "正文",
            "```py",
            "y = 3",
            "```",
        ]
    )
    # 2 个代码块共 3 行代码，占比足够
    assert detect_book_type(text)["book_type"] == "technical"
