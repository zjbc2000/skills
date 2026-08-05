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

### Stage 2: 结构分析
- 用 Markdown 标题层级（或 PDF 书签 TOC）识别章节边界；无书签 PDF 的提取产物是无标题纯文本，需人工指认章节边界。
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
- 运行 `python3 scripts/validate_skill.py outputs/<book-slug>/SKILL.md outputs/<book-slug>/*/SKILL.md` 校验总入口与所有子 skill。
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
