# 书型 → 提取工具映射

| 书型 | 工具 | 说明 |
|---|---|---|
| 文本版（多数现代编程书） | PyMuPDF（默认） | 极快，`get_toc()` 读内嵌书签 |
| 技术书（代码/表格/公式多） | Docling（可选 `--engine docling`） | 保留 Markdown 表格代码块；需 `pip install docling` |
| 中文扫描版 / 复杂版式 | MinerU（提示，不在本脚本内） | 中文 OCR 最强，需 GPU；无 GPU 用 Marker |

## 书型判定（v1.0）

用 `scripts/detect_book_type.py <book.md>` 自动判定，输出 `technical` / `text` / `mixed`：

| 判定 | 启发式 |
|---|---|
| **technical** | 代码行占比 ≥5%，或表格行 ≥20，或公式块 ≥10 |
| **text** | 代码占比 ≤1% 且无表格、无公式 |
| **mixed** | 其余（有代码但未到 technical 阈值） |

`mixed` 默认按 `text` 处理（章节预算取低值，抽取走最快路径），但摘要时若章节里有代码/表格则按 technical 样式保留。

## 章节摘要预算矩阵（v1.0）

书型决定每章摘要的 token 预算（上限，密度优先时允许低于下限；不 pad）：

| | 浅读（reference） | 深读（study） |
|---|---|---|
| **text** | 600–900 token | 800–1200 token |
| **technical** | 900–1400 token | 1400–2200 token |

深读需额外内容支撑（Worked Example / 展开 How / 失败模式），不是把数字调大。无样例可复刻的薄章允许低于下限，并在 Core Idea 注明。

## 使用规则
- 默认走 PyMuPDF（`--engine pymupdf`）。只有明确是技术书且需要保留表格/代码块时才用 Docling（`--engine docling`，需 `pip install docling`；未安装时脚本明确报错并返回退出码 1）。
- 扫描版 PDF（`pdf_is_scanned` 检测）直接提示换 MinerU，不硬跑。
- 中文文本版若内嵌 ToUnicode 正常，PyMuPDF 可直接提取；异常时提示提供 Markdown。
