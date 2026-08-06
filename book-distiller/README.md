# Book Distiller（拆书成 Skill）

把一本软件 / AI-coding 相关书籍**蒸馏成可复用的 agent 技能**。输入可以是 PDF、Markdown 或微信读书链接；简单书产出 skill 形态，复杂书（需要 hooks / MCP / 子代理 / 分发）产出 plugin 形态。

## 项目定位

书是"死"的——翻箱倒柜才找到一段方法论；skill 是"活"的——agent 按触发词直接调用。本工具把书里散落的知识重新组织成 agent 可直接执行的技能包，而不是照抄目录。

- **输入三种路径**：PDF（转 Markdown）、Markdown（直接用）、微信读书链接（强制全文导出）
- **产出两种形态**：裸 skill（方法论书默认）或 plugin（需要 hooks/MCP/子代理/分发时）
- **质量保证**：主题划分、子 skill 生成两处强制检查点 + 脚本自动校验
- **可追溯**：每条关键结论标注 `来源：第N章`，防幻觉

## 六阶段流程

| 阶段 | 做什么 | 检查点 |
|---|---|---|
| **1. 输入检测** | 判断输入类型，统一成干净 Markdown + 章节树 | |
| **1.5. 书型判定** | `detect_book_type.py` 判定 technical/text/mixed，选抽取引擎与章节预算 | （v1.0） |
| **2. 结构分析** | 识别章节边界，按预算矩阵生成摘要（map，密度优先、不抄原文）；>50k token 用 probe_book 按需读 | |
| **2.5. 成本预估** | `estimate_cost.py` 预估输入/输出 token、费用、时间，用户确认后再进 Stage 3 | （v2.0） |
| **3. 主题划分** | 基于全部章摘要提出 3–10 个主题清单 | ★ 强制停下，用户确认/增删/合并 |
| **4. 判别树** | 按判别树判定 skill / plugin 形态，展示给用户 | （检查点 1 顺带确认，可改判） |
| **5. 逐主题生成** | 按 skill-template 逐个生成子 SKILL.md | ★ 首样例确认格式，其余自动跑 |
| **6. 自检与交付** | 校验脚本 + 汇总报告（主题清单、覆盖范围、下一步建议） | |

判别树要点：**skill 优先，plugin 是升级路径**。程序性知识书（Clean Code 这类）默认 skill；需要 MCP server / hooks / 子代理 / 多命令分发 / 团队分发时走 plugin。

## 用法

### 输入处理

```bash
# PDF → Markdown（扫描版会提示换 MinerU）
python3 scripts/extract_text.py <pdf> -o <out.md>

# 微信读书链接 → 全文 Markdown（需先 clone 导出器）
git clone https://github.com/lbq110/weread-exporter ~/tools/weread-exporter/
python3 scripts/weread_fetch.py <链接> \
  --exporter=~/tools/weread-exporter/export_precise.py \
  --workdir=~/tools/weread-exporter/

# Markdown 输入：直接用
```

### 按需读大书（REPL 式，v3.0）

```bash
python3 scripts/probe_book.py size <合并md>                        # 是否超 50k token
python3 scripts/probe_book.py chapters <合并md>                    # 章节标题+起始行号
python3 scripts/probe_book.py slice <合并md> --chapter N           # 只读第N章
python3 scripts/probe_book.py slice <合并md> --start L --end L     # 按行切片
python3 scripts/probe_book.py grep <合并md> "<框架名>"             # 写摘要前验证书里真有
```

微信读书路径首次使用会弹出浏览器扫码登录；导出是长任务（整本书 30 分钟至数小时）。

### 校验产出

```bash
# skill 形态：校验总入口 + 所有子 skill
python3 scripts/validate_skill.py outputs/<book-slug>/SKILL.md outputs/<book-slug>/*/SKILL.md

# plugin 形态：额外校验 plugin 结构
python3 scripts/validate_plugin.py outputs/<book-slug>
```

## 产出物结构

```
outputs/<book-slug>/
├── SKILL.md          # 总入口：frontmatter + 全书心智模型 + 主题决策树（场景 → 调哪个子 skill）
├── <topic>/SKILL.md  # 各主题子 skill（每个独立可触发）
└── references/       # 章节精要，子 skill 深入时按需加载
```

plugin 形态时：上述内容移入 `skills/`，新增 `.claude-plugin/plugin.json`（+ 可选 `marketplace.json` / `agents/` / `hooks/` / `.mcp.json`）。

## 实战样例

`outputs/ai-programmer-fullstack/` 是《人人都是AI程序员》全书蒸馏出的 6 个全栈主题 skill（ai-backend-dev / ai-frontend-design / ai-product-engineering / ai-project-planning / lean-fullstack-tools / vibe-coding）。

## 测试

```bash
python3 -m pytest tests/
```

（41+ 个用例覆盖全部脚本的输入处理、校验逻辑）

## 版本记录

### v1.0 — 书型分档（2026-08-06）

借鉴 `virgiliojr94/book-to-skill` 的 Step 1.5：不同书型用不同抽取引擎和章节摘要预算。

- 新增 `scripts/detect_book_type.py`：按代码/表格/公式占比启发式判定 `technical` / `text` / `mixed`
- `references/book-types.md` 增加书型判定规则与章节摘要预算矩阵（浅读/深读 × text/technical）
- SKILL.md 新增 Stage 1.5：抽取引擎与章节预算由书型决定
- 新增 6 个测试用例（`tests/test_detect_book_type.py`）

### v2.0 — 生成前成本预估（2026-08-06）

借鉴 `virgiliojr94/book-to-skill` 的 Step 2.5：生成前先给用户报价。

- 新增 `scripts/estimate_cost.py`：CJK 加权 token 估算 + 输入（全书×1.3）/输出（章节×预算+固定产出）分项 + 费用/时间预估
- 章节预算矩阵与 book-types.md 对齐；`--rate-in/--rate-out` 覆盖价格，默认示例值标注"估算"
- SKILL.md 新增 Stage 2.5：用户确认成本后再进主题划分
- 新增 7 个测试用例（`tests/test_estimate_cost.py`）

### v3.0 — REPL 式按需读大书（2026-08-06）

借鉴 `virgiliojr94/book-to-skill` 的 Step 2.6（RLM 范式）：把整本书当可查询语料，不一次性读进上下文。

- 新增 `scripts/probe_book.py` 四子命令：`size`（字符/token/行数）、`chapters`（章节+起始行号）、`slice`（按行/按一级章节切片）、`grep`（写摘要前验证框架真实存在，防幻觉）
- SKILL.md Stage 2 增加 REPL 读法：>50k token 的书不再整读全文，成本与输出成正比而非与源书成正比
- 新增 8 个测试用例（`tests/test_probe_book.py`）

### v4.0 — 子 skill 决策速查层（2026-08-06）

借鉴 `virgiliojr94/book-to-skill` 的 cheatsheet（作者判断层），适配为本项目"一书多主题"形态：每个主题子 skill 加 `## 决策速查` 节，而非每本书一个文件。

- `references/skill-template.md` 正文结构扩展为"三明治 + 决策速查"：何时使用 / 核心规则 / **决策速查** / 检查清单
- 决策速查四要素：决策规则（When X do Y because Z）、权衡矩阵、阈值与默认值、tells & smells；禁止裸术语和散文
- SKILL.md Stage 5 生成该层；已给 `outputs/ai-programmer-fullstack/vibe-coding/` 补决策速查示例（校验通过）

### v5.0 — Update / Fold-in 增量合并（2026-08-06）

借鉴 `virgiliojr94/book-to-skill` 的 Mode 4：重版/修订/同作者续作不重跑全流程，增量折进既有输出。

- 新增 `scripts/fold_in.py`：对比新旧章节标题（主键=章节编号，无编号用归一化名），产出 `new` / `revision` / `duplicate` 三分类合并计划
- SKILL.md 新增 Mode 4 五步流程：合并计划 → 新增精要/子skill → 修订既有 → 更新总入口 → 自检交付
- 适配点：本项目合并发生在 references 精要 + 主题子 skill 核心规则上（而非 book-to-skill 的逐章文件），语义合并仍由 LLM 完成，脚本负责机械 diff
- 新增 6 个测试用例（`tests/test_fold_in.py`）
