# 书型 → 提取工具映射

| 书型 | 工具 | 说明 |
|---|---|---|
| 文本版（多数现代编程书） | PyMuPDF（默认） | 极快，`get_toc()` 读内嵌书签 |
| 技术书（代码/表格/公式多） | Docling（可选 `--engine docling`） | 保留 Markdown 表格代码块；需 `pip install docling` |
| 中文扫描版 / 复杂版式 | MinerU（提示，不在本脚本内） | 中文 OCR 最强，需 GPU；无 GPU 用 Marker |

## 使用规则
- 默认走 PyMuPDF（`--engine pymupdf`）。只有明确是技术书且需要保留表格/代码块时才用 Docling（`--engine docling`，需 `pip install docling`；未安装时脚本明确报错并返回退出码 1）。
- 扫描版 PDF（`pdf_is_scanned` 检测）直接提示换 MinerU，不硬跑。
- 中文文本版若内嵌 ToUnicode 正常，PyMuPDF 可直接提取；异常时提示提供 Markdown。
