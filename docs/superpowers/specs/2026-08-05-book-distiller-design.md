# 拆书成 Skill（Book Distiller）设计文档

日期：2026-08-05
状态：待评审

## 1. 背景与目标

用户是全栈方向的 agent 开发工程师，想做一个「把编程书籍转化为 agent skill」的 skill。书籍来源是软件 / AI-coding 相关的工具书（如《Clean Code》）。核心愿景：**给一本书的 PDF，产出可复用的 agent 能力包**——简单书产出 skill，复杂书产出含 mcp/skill/subagents/hooks 的 plugin。

### 三个原始难点（已通过调研解答）

| 难点 | 结论 | 依据 |
|---|---|---|
| 1. 长书如何提取关键信息 | 目录树 map-reduce 蒸馏，不整本喂、不默认 RAG | book-to-skill(16.8K★) 已验证；PyMuPDF `get_toc()` 做 TOC 锚点，Docling/MinerU 按书型提取 |
| 2. skill 还是 plugin | 判别树：需要 hooks/子代理/MCP/分发 → plugin；纯方法论书 → skill | 官方规范 + wondelai/skills(62 书实证) |
| 3. 复杂 plugin 能否 TDD 验证 | 能。四层验证栈：结构(plugin validate --strict) → 加载 → 行为(evals.json 对照) → 集成 | 官方 skill-creator 的 eval 闭环 |

### 调研发现的关键事实
- **微信读书 2026-05 发布官方 Skills API**：可拿书架/笔记/划线，但**不含正文全文**。全文需正版 DRM-free 电子书或 Canvas Hook 导出工具（个人自用有风控风险）。
- **拆书 skill 的输入应兼容三种来源转化的 Markdown**：官方 API 笔记、正版电子书、导出工具产物。

## 2. 已确认的设计决策（用户选定）

| 决策 | 选择 |
|---|---|
| 产出粒度 | 一书多 skill：总入口 `SKILL.md` + 各主题子 skill |
| 交互模式 | 自动 + 两个强制检查点（主题确认、首个样例确认） |
| 输出语言 | 全中文（description + 正文） |
| 输入 | 三通道：PDF（内建转换）、Markdown、微信读书（强制全文导出） |
| 主题划分 | LLM 自动提主题 + 用户确认 |
| 拆书器形态 | **B：skill 为主 + plugin 可选**（判别树决定） |

## 3. 架构

拆书 skill 是一个"元技能"（meta-skill）：它本身是一次性工作流，产出物是可复用的 skill/plugin。

```
用户提供书 (PDF / Markdown / 微信读书链接)
        │
        ▼
┌─────────────────────────────────────┐
│  Stage 1: 输入检测                   │
│  PDF → 内建转 Markdown               │
│  Markdown → 直接用                   │
│  微信读书链接 → weread_fetch.py      │
│     强制全文导出(失败则停下换源)      │
└──────────────┬──────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Stage 2: 结构分析           │
│  TOC 锚点切分章节            │
│  LLM 读章摘要(800-1200 tok)  │
└──────────────┬──────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Stage 3: 主题划分           │
│  LLM 自动提主题              │
│  ★检查点1: 用户确认/增删      │
└──────────────┬──────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Stage 4: 判别树             │
│  需要 hooks/MCP/子代理/分发? │
│   否 → skill 形态            │
│   是 → plugin 形态           │
└──────────────┬──────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Stage 5: 逐主题生成子 skill │
│  ★检查点2: 确认首个样例      │
│  剩余自动生成                │
└──────────────┬──────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Stage 6: 自检               │
│  frontmatter 合法 + 触发     │
│  引用可回溯 + 汇总报告        │
└─────────────────────────────┘
```

## 4. 组件

```
book-distiller/                    # 拆书 skill 本身
├── SKILL.md                       # 主指令：流程 + 判别树 + 检查点 + 产出模板
├── scripts/
│   ├── extract_text.py            # PDF → Markdown（按书型选 PyMuPDF/Docling/MinerU）
│   ├── weread_fetch.py            # 微信读书：解析链接→强制调导出工具拉全本 Markdown
│   ├── validate_skill.py          # frontmatter 合法性检查（name 与目录一致、description ≤1024 且含 what+when）
│   └── validate_plugin.py         # plugin 形态：plugin.json + marketplace.json 结构检查
├── references/
│   ├── skill-template.md          # 子 SKILL.md 模板（全中文、三明治结构）
│   ├── discrimination-tree.md     # skill vs plugin 判别树参考
│   ├── book-types.md              # 书型→提取工具映射（文本版/技术书/中文扫描版）
│   └── weread-api.md              # 微信读书：导出工具用法 + 官方API(仅解析书名) + 坑
└── outputs/                       # 拆书产出物放这里（默认，可配置）
    └── <book-slug>/
```

## 5. 数据流

### 5.1 输入
- 用户给 PDF、Markdown 路径或微信读书链接。
- **PDF** 走 `scripts/extract_text.py`，按书型自动选择：
  - 文本版 → PyMuPDF（`get_toc()` 读书签目录）
  - 技术书（代码/表格多）→ Docling（保留 Markdown 表格代码块）
  - 中文扫描版 → MinerU（OCR），无 GPU 提示用 Marker 或人工提供 Markdown
- **Markdown** → 直接用。
- **微信读书** → 见 5.2。
- 输出统一为 Markdown + 章节树。

### 5.2 微信读书输入（第三条路径，强制全文）
- 用户给微信读书 reader 链接或书名。`scripts/weread_fetch.py` 解析 bookId（链接直接取 URL 段，书名先调 `/store/search`）。
- **强制全文模式**：调 `lbq110/weread-exporter`（扫码登录 + Canvas Hook）导出**全本** Markdown（`output/<bookId>/书名.md`，含图片）。首次运行扫码登录一次，会话持久化。
- **不降级**：若全文导出失败（出版社限制"去 App 阅读"、无 Chromium、账号无权限），**停下并提示用户换源**——提供 PDF/Markdown 或改用正版 DRM-free 电子书路径，绝不降级到划线骨架硬拆。
- **明确风险**：全文导出有账号风控与 ToS 违约风险，仅供个人自用、不传播。SKILL.md 需在进入此路径时提示。
- **前置**：需要 Playwright + Chromium（`pip install playwright && playwright install chromium`）。
- **官方 API（可选辅助，非主路径）**：仅当用户已有 `WEREAD_API_KEY` 时，可用于解析书名→bookId 或查看元数据；不作为拆书内容来源（官方 API 无正文）。

### 5.2.1 工程细节（详见 `references/weread-api.md`）
- reader 链接 `https://weread.qq.com/web/reader/<bookId>` → bookId 直接取 URL 段；书名先调 `/store/search`。
- 导出器约 1-2 秒/页、需 Chromium、Cookie 会过期、账号可能被风控；出版社限制网页阅读的书导不出全文。
- Canvas Hook 导出有断行拼接痕迹，蒸馏前需清理。
- **扫码登录机制**：导出器用 Playwright 启动**有头（headless=False）Chromium 真窗口**打开 weread.qq.com，检测未登录则停在登录页等用户扫码（每 5 秒轮询 URL，最长 10 分钟）。会话 cookie 持久化在 `cache/browser_profile/`，**扫码只需一次**，后续复用。`weread_fetch.py` 是薄封装：解析 bookId → 调 `export_precise.py` → 读 `output/<bookId>/书名.md`。**首次使用必须提示用户"会有浏览器窗口弹出请扫码"**；导出是长任务（整本书 30 分钟至数小时），中途卡住自动续传。需 `pip install playwright && playwright install chromium`。

### 5.3 结构分析
- TOC 锚点切章。优先 PDF 内嵌书签（`get_toc()`），无书签退化字体启发式，再退化人工指认。
- 每章喂 LLM 生成 800–1200 token 摘要（map），**不抄原文、实践者视角（When X use Y）、密度优先**。

### 5.4 主题划分（检查点1）
- LLM 基于全部章摘要提出 3–10 个主题清单。
- **强制停止**：用户确认/增删/合并主题后才继续。

### 5.5 判别树（检查点1 顺带确认）
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
- 判别树结果在检查点1 时展示给用户，用户可改判。

### 5.6 逐主题生成（检查点2）
- 按主题逐一生成子 skill，每个遵循 `references/skill-template.md`：
  - frontmatter（name 小写 kebab-case 与目录一致、description 全中文含 what+when+触发词）
  - 正文：三明治结构（何时用 → 具体规则/示例 → 检查清单）
  - 引用：每条关键结论标注 `来源：第N章`（防幻觉，可回溯）
- **强制停止**：生成首个样例后让用户确认格式，其余自动跑。

### 5.7 自检与交付
- 运行 `scripts/validate_skill.py`（L0 结构检查）。
- plugin 形态额外运行 `scripts/validate_plugin.py` + 建议 `claude plugin validate --strict`。
- 产出 `outputs/<book-slug>/` 目录 + 汇总报告（主题清单、各 skill 说明、下一步建议）。

## 6. 产出物结构
```
outputs/clean-code/
├── SKILL.md          # 总入口：索引 + 主题决策树
├── naming/SKILL.md   # 主题子 skill
├── functions/SKILL.md
├── comments/SKILL.md
├── refactoring/SKILL.md
└── references/       # 章节精要，按需加载
```

### 6.1 skill 形态（默认）

### 6.1.1 skill 形态说明
- 总入口 `SKILL.md`：frontmatter + 全书心智模型 + 主题决策树（"用户在什么场景 → 调哪个子 skill"）。
- 主题子 skill：每个独立可触发，frontmatter 的 description 含主题专属触发词。
- `references/`：章节精要，子 skill 需要深入时按需加载。

### 6.2 plugin 形态（判别树判定需要时）
```
outputs/<book-slug>/
├── .claude-plugin/
│   └── plugin.json    # name/version/description/author
├── skills/            # 上述 skill 全部移入
├── agents/            # 如需要子代理
├── hooks/             # 如需要生命周期钩子
├── .mcp.json          # 如需要 MCP server
└── marketplace.json   # 如需要分发
```

## 7. 错误处理

| 场景 | 处理 |
|---|---|
| PDF 转换失败（扫描版无 OCR 环境） | 提示走 MinerU/人工提供 Markdown，不阻塞后续 |
| 全文导出被出版社限制（"去 App 阅读"） | **停下**，提示换源：提供 PDF/Markdown 或改用正版电子书路径，不降级到骨架 |
| 无 Playwright/Chromium | 提示安装（`pip install playwright && playwright install chromium`），装好后重跑 |
| 微信扫码登录过期 | 提示重新扫码登录一次 |
| 微信官方 API Key（若用户配置了用于解析书名）无效 | 提示重新配置，或让用户直接给 reader 链接 |
| 书无显式章节标题 | 降级字体启发式 → 再退化人工指认章节边界 |
| 主题聚类过少（<3）或过多（>10） | 提示用户，给合并/拆分建议 |
| 某主题提取不到足够内容 | 合并到相近主题，报告中注明 |
| plugin 形态校验失败 | 输出具体错误，指导修复后重跑 validate |

## 8. 测试（TDD）

### 8.1 对拆书 skill 本身的测试
- **结构**：`scripts/validate_skill.py` 对拆书 skill 自身的 SKILL.md 做 L0 检查。
- **行为**：用一本样书（如公开的 Pro Git 或一篇长技术文档）跑通全流程，断言：
  - 产出 3–10 个主题
  - 每个子 skill frontmatter 合法
  - 每条关键结论可回溯到章节
- **微信读书路径**：用一本公开书跑全文导出，断言产出全本 Markdown；无 Chromium 环境时跳过（标记为需环境配置）。**出版社限制的书**（如提示"去 App 阅读"）断言正确停下并提示换源，不降级到骨架

### 8.2 对拆书产出的 skill 的验证（内建质量门）
- 每个子 skill 的 description 写"应该触发/不应触发"查询，人工抽查。
- 参考 skill-creator 的 evals 模式（可选强化，非 v1 必需）。

### 8.3 plugin 分支的验证
- `scripts/validate_plugin.py`：plugin.json/marketplace.json 结构 + 路径解析。
- 建议用户跑 `claude plugin validate --strict`（进 CI 的门禁）。

## 9. 范围与非目标（v1）

**做**：
- 一书多 skill 的完整蒸馏流程（输入检测 → 结构分析 → 主题划分 → 逐主题生成 → 自检）
- 判别树 + plugin 可选分支（生成 plugin.json/marketplace.json 骨架）
- 三个脚本（extract_text / validate_skill / validate_plugin）
- 全中文输出

**不做（v1）**：
- 不做跨书 RAG 检索（serve 期零向量库）
- 不做完整 skill-creator eval 循环（description 触发自动化优化）——留作 v2
- 不做 MCP server 的自动编写——判别树判定需要时，plugin 骨架给出占位并指导编写
- 微信读书**只做强制全文导出**（调现成 `weread-exporter`），不做私有接口逆向（正文接口逆向脆弱且无维护良好的开源实现）；官方 API 仅用于解析书名/查元数据，不作为拆书内容来源

## 10. 验收标准

用一本书（用户任选，建议从《Clean Code》或一本 DRM-free 电子书开始）跑通拆书 skill：
- [ ] 产出 `outputs/<book-slug>/` 完整目录
- [ ] 总入口 SKILL.md + 3–10 个主题子 skill，全部全中文、frontmatter 合法
- [ ] 通过 `scripts/validate_skill.py` 检查
- [ ] 每个子 skill 的 description 能准确触发（人工抽查 2–3 个）
- [ ] 关键结论可回溯到章节
- [ ] 判别树正确判断"该书是否需要 plugin 形态"
- [ ] 三条输入路径均验证：PDF 转换、Markdown 直通、微信读书全文导出（若有 Chromium 环境）
- [ ] 微信读书全文导出产出全本 Markdown（含章节、图片引用），可正常进入蒸馏流程
- [ ] 微信读书遇到出版社限制的书正确停下提示换源，不降级到骨架
