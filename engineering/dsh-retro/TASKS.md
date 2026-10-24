# dsh-retro 建设笔记

这份文件干两件事：把脚本的逻辑摊开（为了能改），列出接下来要做的（为了知道改什么）。

> 命名说明：现在叫 `dsh-retro`，只吃 DSH 的会话日志。P0 做完（接入 Codex / Claude Code）后应改名 `agent-retro`，届时一并改 README 与本文件。

## 一、整体逻辑：四层

```
~/.dsh/sessions/**/session.v4.jsonl.zstd
        │  ① collect()   按 mtime 筛时间窗 → 文件清单
        ▼
   scan_session()       ② 单文件流式解析 → 一条 record
        │
        ▼
    render()            ③ 纯函数：records → markdown 摘要
        │
        ▼
   模型读摘要（约 20 KB），要证据时 --topic 再钻原始会话
```

核心取舍：**模型永远不读原始日志**。本机日志 517 MB，摘要 20 KB，差四个数量级。这是它能跑起来的原因，也是所有精度问题的来源。

### ① collect()　`scripts/retro.py:229-257`

`os.walk` 找 `session.v4.jsonl.zstd`，用**文件 mtime** 当日期，按 `--days` / `--since --until` 过滤。

环比是**再跑一次** `collect(days*2)` 再筛出上一周期（`retro.py:495-498`），所以带环比的耗时是两倍。

### ② scan_session()　`retro.py:135-226`

一行一个事件。先用 **substring 预筛**再 `json.loads`——日志是紧凑 JSON，所以预筛必须写 `'"tool/call"'`；写成 `'"type": "tool/call"'`（带空格）会全漏，而且不报错。抽七样：

| 抽什么 | 事件 | 字段 |
|---|---|---|
| cwd | `"type":"session"` | `.cwd` |
| 标题 | `session/title` | `.data.title` |
| 模型 | `request/header` | `.data.header.config.{provider,model}` |
| 工具调用 | `tool/call` | `.data.name`；`skill` / `write` / `edit` 再解析 `arguments` |
| token | 含 `"inputTokens"` 的 `assistant/attempt` | `.data.stream[].chunk.usage.{inputTokens,outputTokens,cacheReadTokens}` |
| 模型错误 | 同上 | `.chunk.type=="finish"` 且 `.reason.kind=="error"` |
| 用户文本 | `user/message` | `.data.content[].text`，过 `looks_injected()` 丢掉注入块 |

### ③ render()　`retro.py:333-471`

十一个 section，全是计数。三个口径要记住：

- **域 / 活动**：`dim_hits()`（`retro.py:310-322`）把全部用户文本拼成一个小写大串，对每个词做 `str.count()` 求和。**是子串计数，不是分词**。
- **摩擦点**：同一套 `str.count()`，单独渲染。
- **反复提及的词**：`mine_terms()`（`retro.py:260-307`）。中文切 CJK 连续段 → 2~6 元 n-gram → 按**出现过该词的会话数**（文档频率）排序 → 支配过滤（更长的片段覆盖它、且会话数 ≥ 70% 就丢掉短的）。英文按词，带 stoplist。

### ④ 摘要的用途

它是索引，不是结论。模型按 `SKILL.md` 的四问切入，写复盘文档。

## 二、精度：现在哪里在丢信息（按影响排序）

### 2.1 只统计用户侧文本（最大偏差）

`all_user` 与 `mine_terms` 都只吃 `user_text`。助手说的话、工具输出、子代理回报一律不进统计。

后果：这份复盘回答的是「**你说了什么**」，不是「**你干了什么**」。你让 agent 连跑两小时、自己只打了一句「继续」，那两小时在统计里几乎不存在。

### 2.2 子串计数会双重计数

- 同组内 `报错` 与 `报错信息` 同时命中，同一句话算两次。
- 跨组重复：`设计` 同时在「前端」和「设计视觉」两个域里。
- 中文没有词边界：`文档` 会命中 `文档化`。

### 2.3 n-gram 的 120 字截断

`retro.py:276` 的 `run = run[:120]`：一段 500 字的长段只有前 120 字参与 n-gram。粘贴的长需求、长日志，尾部内容不进榜单。

### 2.4 事件名硬编码 = 格式漂移时静默归零

`'"tool/call"'`、`'"user/message"'` 这些字符串绑死了 DSH 的 v4 日志格式。上游改字段名或升版本，脚本不报错、只是所有计数变 0——第一版就是这么废掉的，排查了半天。

**这是接多源时最先要拆的地方。**

### 2.5 会话按 mtime 归到单日

跨三天的会话只算在最后修改那天；`--since/--until` 也会因为 mtime 落在窗外而整体漏掉。

### 2.6 `minutes` 字段名不对

`rec["minutes"] = len(rec["user_text"])`（`retro.py:254`）——是用户消息条数，不是分钟。目前只在 `--topic` 里用。

### 2.7 已修的小 bug

`retro.py:305` 的英文过滤条件 `not any(... for x, xd, _ in [(w, d, 0)])` 恒为真（列表里只有 `w` 自己，`x != w` 永远 False），已简化成 `d >= 3`。

## 三、待办

### P0 接入 Codex 与 Claude Code

目标：一份摘要覆盖本机所有 agent 的会话，不再只服务 DSH。

设计：把 `scan_session()` 抽成适配器，`render()` 只认统一后的 `Record`。

```python
# scripts/adapters/__init__.py
def discover(source, since, until) -> list[Path]
def scan(path) -> Record
```

`Record` 沿用现在的字段并加 `source`：`{source, day, cwd, project, title, model, user_text, assistant_text, tools, files, skills, usage{in,out,cached}, turns, errors}`。摘要加一行「来源分布」。CLI 加 `--source dsh,codex,claude`，默认自动探测存在的目录。

**实测过的格式**（2026-10-24 本机样本）：

#### Codex —— `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`（明文 JSONL）

| 要什么 | 位置 |
|---|---|
| cwd | `type=="session_meta"` → `payload.cwd`；`turn_context.payload.cwd` 里也有 |
| 模型 | `session_meta.payload.model_provider` |
| 用户消息 | `event_msg` → `payload.type=="item_completed"` → `item.type=="UserMessage"` → `item.content[].text` |
| 助手 / 工具 | `response_item` → `payload.type` ∈ {`message`, `function_call`, `custom_tool_call`, `reasoning`} |
| token | `event_msg` → `payload.type=="token_count"` → `payload.info.total_token_usage.{input_tokens, cached_input_tokens, output_tokens}` |

坑：`token_count` 是**累计值**不是增量，求和会爆掉，要取 `last_token_usage` 或最后一个 `total_token_usage`。`role=="developer"` 的 message 是注入的系统指令（permissions/sandbox 说明），必须过滤，否则和 DSH 的 `INJECTED` 一样污染榜单。

#### Claude Code —— `~/.claude/projects/<编码后的 cwd>/<session-uuid>.jsonl`（明文 JSONL）

| 要什么 | 位置 |
|---|---|
| cwd | 顶层 `cwd` |
| 模型 | `type=="assistant"` → `message.model` |
| 用户消息 | `type=="user"` → `message.content`（数组里的 `{type:"text"}`，或纯字符串） |
| 助手文本 | `type=="assistant"` → `message.content[]` 里 `type=="text"`（`thinking` / `tool_use` 另算） |
| token | `message.usage.{input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens}` |
| 标题 | `type=="custom-title"` 事件 |

坑：同一目录混着 `attachment`、`file-history-snapshot`、`queue-operation`、`api-request-*` 等非对话事件；`/private/var/folders/...` 这类临时目录的会话会污染项目分布，要能按 cwd 过滤。

**验收判据**：三个源的会话数之和 = 各自目录在时间窗内的文件数；同一时段同一任务在两个 agent 里各跑一遍，摘要的「来源分布」两行都有数。

### P1 精度

1. **把助手侧纳入统计**：至少让 `mine_terms` 能吃 `assistant_text`，用 `--include-assistant` 开关控制，先看榜单怎么变再决定默认值。
2. **计数改成带边界匹配**：中文用 n-gram 命中 + 组内去重叠（同一位置只算最长命中）。
3. **去掉 120 字截断**：改成按标点切句后再 n-gram。
4. **跨天会话按事件时间切分**，不按 mtime。
5. **格式漂移要吵**：解析到 0 条工具调用时打印警告，而不是安静输出 0。

### P2 体验

- 环比不要重跑 `collect`：一次遍历同时产出两个窗口。
- `minutes` 改名，或者真的算时长（首末事件时间戳之差）。
- 加 `--project` 过滤，省得每次 `--json` 后自己按 `project` 字段筛。

## 四、改的时候的判据

- **摘要只会变长不会变准**是常态。每加一个 section 先问：这条会不会改变我下周的行为？不会就别加。
- **任何计数都要能在原始会话里复核**。加指标的同时想好 `--topic` 怎么钻到证据。
- **精度优先于覆盖**：宁可少统计一个源，也不要统计错。
