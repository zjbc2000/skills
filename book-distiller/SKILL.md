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
| 微信读书链接（书名请自行转为链接） | `python3 scripts/weread_fetch.py <链接> --exporter=<导出器目录>/export_precise.py --workdir=<导出器目录>`（强制全文导出） |

**微信读书前置条件**：导出器需先 `git clone` 到固定目录（如 `~/tools/weread-exporter/`），`<导出器目录>` 填该绝对路径。因为 `weread_fetch.py` 的 `--workdir`/`--exporter` 默认是相对路径，若 cwd 不是导出器目录会 FileNotFoundError，所以必须显式传导出器绝对路径。

微信读书路径**首次使用必须提示用户**"会有浏览器窗口弹出，请扫码登录微信读书"；导出是长任务（整本书 30 分钟至数小时）。导出失败（出版社限制等）→ **停下提示换源**，不降级到官方 API 划线骨架。

## 流程

### Stage 1: 输入检测
- 判断输入类型，按上表统一成干净 Markdown + 章节树。清理 Canvas 导出的断行拼接痕迹。

### Stage 1.5: 书型判定 ★v1.0
- 运行 `python3 scripts/detect_book_type.py <合并md>`，按结果选择抽取引擎与章节预算（见 `references/book-types.md`）：
  - **technical** → 保留表格/代码块，章节预算取高值；PDF 优先 `--engine docling`
  - **text** → 最快路径，章节预算取低值
  - **mixed** → 按 text 处理，但含代码/表格的章节摘要用 technical 样式
- 书型同时决定后续章节摘要的 token 预算矩阵（浅读/深读 × text/technical）。若用户已明确"参考用/深读用"，直接套对应列。

### Stage 2: 结构分析
- 用 Markdown 标题层级（或 PDF 书签 TOC）识别章节边界；无书签 PDF 的提取产物是无标题纯文本，需人工指认章节边界。
- 每章读原文，按 Stage 1.5 的预算矩阵生成摘要（map）：**密度优先、实践者视角（When X use Y）、不抄原文**。
- **>50k token 的书不整读全文**（v3.0，REPL 按需读）：把全文当可查询语料，用 `scripts/probe_book.py` 只读需要的部分——
  ```bash
  python3 scripts/probe_book.py size <合并md>                          # 是否超阈值
  python3 scripts/probe_book.py chapters <合并md>                      # 章节标题+起始行号
  python3 scripts/probe_book.py slice <合并md> --chapter N             # 只读第N章
  python3 scripts/probe_book.py slice <合并md> --start L --end L       # 按行切片
  python3 scripts/probe_book.py grep <合并md> "<框架名>"               # 声称书里有X前先验证
  ```
  在摘要里写"书中有某个框架/概念"前，必须先用 grep 验证它真实存在，防幻觉。

### Stage 2.5: 生成前成本预估 ★v2.0
- 主题划分前，运行 `python3 scripts/estimate_cost.py <合并md> --book-type <书型> --depth <study|reference>`。
- 把输入/输出 token 数、预估费用、预估时间展示给用户，**让用户确认后再进 Stage 3**。大书（>50k token）尤其必要——避免跑完才发现成本。
- 价格参数 `--rate-in/--rate-out` 按用户当前模型报价覆盖；脚本默认值仅是示例，标注"估算"。

### Stage 3: 主题划分 ★检查点1
- LLM 基于全部章摘要提出 3–10 个主题清单，展示给用户。
- **强制停下**：用户确认/增删/合并后才继续。

### Stage 4: 判别树（检查点1 顺带确认）
- 按 `references/discrimination-tree.md` 判定 skill 还是 plugin 形态，把判定结果展示给用户，用户可改判。

### Stage 5: 逐主题生成子 skill ★检查点2
- 按 `references/skill-template.md` 逐主题生成子 `SKILL.md`，正文含"三明治 + 决策速查"（v4.0）：何时使用 / 核心规则 / **决策速查** / 检查清单。
- 决策速查写作者的**判断**而非概念：决策规则（When X do Y because Z）、权衡矩阵、阈值与默认值、tells & smells——让人不重读全书就能照作者行动。
- **强制停下**：生成首个样例后让用户确认格式，其余自动跑。

### Stage 6: 自检与交付
- 运行 `python3 scripts/validate_skill.py outputs/<book-slug>/SKILL.md outputs/<book-slug>/*/SKILL.md` 校验总入口与所有子 skill。
- plugin 形态额外运行 `python3 scripts/validate_plugin.py outputs/<book-slug>`。
- 产出汇总报告：主题清单、各 skill 说明、覆盖范围、下一步建议。

### Mode 4: Update / Fold-in（更新/折叠既有 skill）★v5.0
- **何时用**：新书是既有书的重版/修订版/同作者续作，主题明显重叠。此时**不重跑** Stage 1–5，而是把新内容增量折进既有输出。
- **1. 生成合并计划**：`python3 scripts/fold_in.py outputs/<既有slug> <新书合并md>`，得三分类：`new`（需新增 references 精要，可能开新主题）/ `revision`（标题变了，复审既有精要）/ `duplicate`（重合，内容可能更新）。
- **2. 新增**：为 `new` 章节写 references 精要；若主题超出既有决策树，新增一个子 skill（按 skill-template，含决策速查）。
- **3. 修订**：对 `revision` 与 `duplicate`，用 probe_book 读新章节，比对既有精要/子 skill 核心规则，改写或追加（新结论标注新 `来源：第N章`）。
- **4. 更新总入口**：`SKILL.md` 的心智模型与决策树若受新内容影响，同步修订。
- **5. 自检交付**：跑 validate_skill.py 校验全部受影响文件，产出"哪些章节新增/修订/重合"的合并报告。

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
