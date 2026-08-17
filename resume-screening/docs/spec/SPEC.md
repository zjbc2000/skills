# 筛简历 Skill — 规格说明书（SPEC）

> **Agent 维护规则**：本文件由 agent 维护。
> 版本：V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> 规则：HISTORY.md 只增不减；文档/代码变更须同步 HISTORY.md 并 bump 版本号。
> 本项目版本规则以本文件为准，**不使用** `update` skill 的 SemVer 语义。

---

## 0. 项目定位

个人简历筛选工具，v0 单人使用（无多用户/账号体系）。两个交付形态：

1. **筛简历 skill**（Claude Code 入口）：编排后端管线——输入数据集+指标类型 → 调用后端 → 输出用户侧/数据侧结果。
2. **react + python 应用**：AE 工作台（Web UI）+ 飞书 bot（群聊入口）。

配套：**评估 pipeline**（skill + python CLI），用个人标注数据回测 skill 自身，产出迭代依据。**无 react 前端**（评估输出自包含 HTML 报告）。

## 1. 核心概念

| 术语 | 含义 |
|---|---|
| `G` | 通用分：项目 + 技术栈 + 亮眼经历 的加分之和 |
| `S` | 特定分：岗位匹配 + 技能要求命中 的加分之和（由 jd_map 派生） |
| `T` | 总分 = `G + S` |
| 红线 | 命中即一票否决（fail），不进入评分 |
| 三模式 | ①通用 ②特定 ③通用+特定 |
| `score_snapshot` | 一次筛选实际应用的指标 + 命中项快照（评估的基准） |
| `manifest.jsonl` | 筛选事件流（事实表，append-only） |
| `jd_map.yml` | 岗位→JD 映射（维度表，唯一真源） |

## 2. 数据层

### 2.1 目录结构

```
datasets/
├── pass/          # 筛选成功的简历文件
├── fail/          # 筛选失败的简历文件
└── manifest.jsonl # 事件流，append-only
```

### 2.2 manifest.jsonl（事实表）

一行一条筛选记录，**只存 jd_ref 外键，不内嵌 JD**：

```json
{
  "resume": "datasets/pass/xxx.pdf",
  "decision": "pass",
  "jd_ref": "西安AE",
  "score_snapshot": { "...": "见 §5" },
  "time": "2026-08-17T10:00:00+08:00",
  "doc_loader": "layout_parsing"
}
```

### 2.3 jd_map.yml（维度表）

```yaml
roles:
  西安AE:
    position: 高级AE工程师
    skills:
      - paddleocr
      - react
    red_lines: []
```

**key 规则**：`jd_ref` 一旦出现在 manifest 中，key 永久不可改名/删除，只允许新增。JD 变更不需版本化——评估以 score_snapshot 为准。

### 2.4 评估基准

评估时以 **score_snapshot**（当时实际应用了什么）为准，不以 jd_map 当前值。

## 3. 判定规则

### 3.1 三模式三口径

| 模式 | 计分 | 判定 |
|---|---|---|
| ① 通用 | 只算 `G` | `G ≥ 通用阈值` |
| ② 特定 | 只算 `S` | `S ≥ 特定阈值` |
| ③ 通用+特定 | 算 `G`、`S`，`T = G + S` | `G ≥ 通用阈值` **且** `T ≥ 总分阈值` |

### 3.2 红线

- 任一红线命中 → **直接 fail**（一票否决），不进入评分。
- 红线独立于评分输出（LLM 输出红线命中列表）。

### 3.3 阈值

阈值是 config 项（初始值用真实数据集 + 阈值扫描校准，不拍脑袋）。

## 4. 分数生成契约（LLM ↔ 引擎）

### 4.1 量纲

每项 `bonus ∈ {0,1,2,3}`（0=无/未命中，1=弱，2=中，3=强）。引擎求和得 `G`/`S`/`T`。

### 4.2 LLM 输出 schema（JSON）

```json
{
  "general": {
    "projects":   [{"name": "...", "bonus": 2, "evidence": "为什么", "quotation": "简历原文片段"}],
    "tech_stack": [{"tech": "...", "bonus": 1, "evidence": "...", "quotation": "..."}],
    "highlights": [{"item": "...", "bonus": 3, "evidence": "...", "quotation": "..."}],
    "red_lines":  [{"rule": "...", "hit": true, "evidence": "...", "quotation": "..."}]
  },
  "specific": {
    "position_match": {"bonus": 2, "evidence": "...", "quotation": "..."},
    "skills": [{"skill": "react", "hit": true, "bonus": 1, "evidence": "...", "quotation": "..."}]
  }
}
```

- **quotation 必填**：引用简历原文片段（对抗幻觉）。
- 任一 `red_lines[].hit == true` → fail。

### 4.3 quotation 校验（后置 grep，确定性）

评分后做校验 pass（**不让 LLM 内联调工具**）：

1. 规范化空白（OCR/解析噪声）
2. 每条 `quotation` 在解析后的简历文本上子串匹配
3. 失败则模糊匹配（token 重叠率）
4. 打标 `verify: exact | fuzzy | missing` 写回 snapshot

**missing 处理（v0）**：该条标记 `suspect`，分数保留；错误率在评估阶段沉淀，先不定惩罚规则。

**校验基准**：解析后的 Markdown（LLM 实际读到的文本），非原始 PDF。

## 5. 管线（模型/工具解耦）

### 5.1 模型注册表 config/models.yml

```yaml
providers:
  ark_coding:        # 主力：火山方舟 Coding Plan
    base_url: https://ark.cn-beijing.volces.com/api/coding/v3   # OpenAI 兼容
    api_key_env: ARK_API_KEY
    models: [deepseek-v4-flash, doubao-seed-2.0-lite]          # glm5.3 注释启用
  deepseek_official: # 降级：DeepSeek 官方
    base_url: https://api.deepseek.com
    api_key_env: DEEPSEEK_API_KEY
    models: [deepseek-v4-flash, deepseek-v4-pro]
```

> 注意：DeepSeek 官方旧名 `deepseek-chat`/`deepseek-reasoner` 已于 2026-07-24 停用，用 V4 ID。

### 5.2 重试 / 降级（config 可调）

- 瞬时错误（429/5xx/超时）：指数退避 + 抖动，重试 **3 次**
- 连续失败 **N=3** → 切换降级 provider
- JSON schema 校验失败：带错误信息重试 **1 次**，仍失败进 failed 队列
- 全部 provider 失败 → 进 `failed` 队列（不静默丢弃）

### 5.3 文档解析 tools.yml

```yaml
tools:
  doc_loader:
    primary: layout_parsing      # POST PDF → 结构化 Markdown
    fallback: [local_pymupdf, local_paddleocr]
```

- **输入格式（v0）**：PDF 为主；图片（png/jpg/webp）走 paddleocr；docx 延后
- **layout-parsing**：百度 AI Studio 部署服务，URL + key 放 `.env`
- **local_pymupdf**：数字 PDF 直读文本（扫描件判定：每页抽取文本过少 → 走 OCR）
- **local_paddleocr**：`lang='ch'`，CPU，模型首次运行自动下载
- **隐私**：v0 接受简历直传远程服务；manifest 记录 `doc_loader` 字段便于审计

### 5.4 统一接口（业务层只依赖抽象能力）

```
doc_to_text(resume) → Markdown     # 引擎不知道 layout-parsing 存在
llm_score(prompt) → JSON           # 引擎不知道 deepseek-v4-flash 存在
notify(chat_id, text) → None       # 触发层不知道飞书长连接存在
```

## 6. 飞书集成（长连接双向 bot）

- **模式**：企业自建应用 + **长连接**（WebSocket，出站 `wss://open.feishu.cn/event`），无需公网入站/内网穿透
- **事件**：订阅 `im.message.receive_v1`
- **触发**：群内 **@机器人 + 发简历**（支持单个 PDF / **压缩包**）
- **回复**：纯文本（v0），含逐份简历的判定摘要
- **权限**：`im:message`、`im:message:send_as_bot`、`im:message.group_at_msg:readonly`、`im:resource`（下载文件）
- **文件下载**：`im/v1/messages/{message_id}/resources/{file_key}?type=file`
- **安全**：chat 白名单（`.env` 配置允许的群 id）；压缩包解压需防 **zip-slip** 路径穿越
- **响应时限**：长连接事件 3 秒内处理，否则触发超时重推（慢操作异步化/先回执）

## 7. 注册表与目录结构

```
resume-screening/
├── SKILL.md            # skill 入口：筛简历 / 跑评估 两模式
├── AGENTS.md           # 维护规则 + 两模块总览
├── README.md           # 背景 / 当前版本 / 功能清单（精简）
├── HISTORY.md          # 版本迭代史（只增不减）
├── docs/
│   ├── spec/SPEC.md    # 本文
│   └── capabilities.md # 模型/工具能力列表（从注册表自动生成）
├── config/
│   ├── models.yml      # 模型注册表
│   ├── tools.yml       # 工具注册表
│   └── thresholds.yml  # 阈值（G/S/T）
├── datasets/           # pass/fail + manifest.jsonl
├── backend/            # python
│   ├── registry/       # models.py / tools.py / llm_client.py（重试+降级）
│   ├── doc_loader/     # base + layout_parsing + pymupdf_local + paddleocr_local
│   ├── scoring/        # engine.py（双闸门）+ prompts.py（系统提示词）
│   ├── verify/         # quotation.py（grep 校验）
│   ├── channels/       # base + feishu.py（长连接 + 压缩包）
│   ├── eval/           # run_eval.py（CLI）+ report.py（HTML）
│   └── api/            # FastAPI（AE 工作台后端）
├── web/                # react：AE 工作台（v0 本地）
├── scripts/            # gen_capabilities_doc.py 等
└── .env.example        # ARK_API_KEY / DEEPSEEK_API_KEY / layout-parsing / 飞书 / API token
```

**能力列表文档**：`docs/capabilities.md` 由 `scripts/gen_capabilities_doc.py` 从注册表元数据自动生成（防漂移）。

## 8. 评估 pipeline

- 形态：**skill + python CLI**（`backend/eval/run_eval.py`），复用同一打分引擎的 batch 模式（DRY）
- 输入：标注数据集（manifest.jsonl + 简历）
- 输出：
  - **用户侧**：自包含 HTML 报告（混淆矩阵、阈值扫描曲线、单指标区分度、引用准确率）
  - **数据侧**：结构化 JSON（供迭代，逐条 verdict 对比 ground truth）
- 关键指标：准确率、精确率/召回率、**引用准确率**（exact/total）、阈值最优操作点、单指标区分度
- 流程：跑批 → 对比 decision → 统计 → 报告

## 9. 部署

- **v0：本地跑**（fastapi + web 本地启动），保持服务器形态
- skill → 后端：HTTP + `X-API-Key`（`.env` 随机 token）
- 上线（v1+）：Docker Compose 到国内 VPS，web 产物由 FastAPI 托管

## 10. 文档体系与版本

### 10.1 文档分工

| 文件 | 读者 | 内容 |
|---|---|---|
| AGENTS.md | agent | 维护规则 + 模块A 开发者工具 / 模块B 项目维护工程 skill |
| README.md | 人 | 项目背景、当前版本、功能清单 |
| HISTORY.md | 人/agent | 版本迭代史，**只增不减** |
| docs/capabilities.md | 人/agent | 模型/工具能力列表（自动生成） |
| docs/spec/SPEC.md | 人/agent | 本文档 |

### 10.2 版本规则（以本项目为准）

- 版本号 **V0.x**，每次用户可见变更**末位 +1**（V0.1 → V0.2 → …）
- major 仅当**用户明确要求**时才 bump
- **推翻** `update` skill 的 SemVer 语义
- 所有文档开头带 **Agent 维护规则**块

## 11. v0 范围与 deferred

**v0 内**：
- 三模式评分 + 双闸门 + 红线否决
- layout-parsing 主力文档解析 + 本地降级
- 飞书长连接双向 bot（@ + 简历/压缩包 → 纯文本回复）
- 评估 CLI + HTML 报告
- AE 工作台（react）本地可跑

**deferred（v1+）**：
- docx 输入、飞书卡片回复、机器人监控群内所有 PDF（非 @ 触发）
- 阈值自动校准落地（v0 只做阈值扫描工具，不自动改配置）
- Docker Compose 上线国内 VPS
- 本地脱敏前置（隐私，若需）

## 12. 决策日志（关键决策与理由）

| # | 决策 | 理由 |
|---|---|---|
| 1 | 个人工具 v0，无账号体系 | YAGNI，数据高度个人化 |
| 2 | 评估走 skill+CLI+HTML，无 react 前端 | 评估是批处理/报告型，非交互型 |
| 3 | manifest 事实表 / jd_map 维度表分离 | DRY，防 JD 漂移，key 稳定 |
| 4 | T=G+S 直接加，双闸门 AND | 简单，可阈值扫描校准 |
| 5 | 红线一票否决 | 红线语义即硬拒，软扣分会掩盖误杀率 |
| 6 | LLM 输出逐项明细+quotation | 归因到具体指标，quotation 引用原文对抗幻觉 |
| 7 | 后置确定性 grep 校验 | 幻觉检测是匹配问题非推理问题，省钱确定性高 |
| 8 | ark coding 主力 + deepseek 官方降级 | 统一订阅省成本，V4 ID 替换已停用的 chat/reasoner |
| 9 | 飞书长连接双向 bot | 官方一等能力，无需公网入站，v0 即可上 |
| 10 | 注册表 config yml + 统一接口 | 方便加功能，业务与实现解耦 |
| 11 | 版本 V0.x 末位+1，推翻 SemVer | 个人工具，轻量；用户明确指定 |
| 12 | v0 本地跑，架构保持服务器形态 | 不为部署而部署，部署路径留好 |
