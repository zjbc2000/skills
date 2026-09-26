---
name: feishu-bot
description: 开发与排障飞书（Feishu/Lark）长连接双向 bot。触发词："飞书 bot"、"飞书机器人"、"lark 长连接"、"飞书消息事件"、"@ 发送者"、"飞书事件回调"、"飞书权限 scopes"、"停 取消筛选"。核心认知在**事件层**：事件里 sender 在 data.event.sender（EventSender.sender_id.open_id），不在 message 内——取错层 @ 永远不生效（本项目 v0.55→v0.57 真实踩坑）。深材料在 references/，按需加载。
---

# 飞书长连接双向 bot（feishu-bot）

> 一句话认知（**事件层**）：事件对象的 sender 在 **`data.event.sender`**（`EventSender`，open_id 在 `sender_id.open_id`）；`data.event.message`（`EventMessage`）只有 message_id/chat_id/message_type/content，**没有 sender 字段**。任何"从 message 里找 sender / 找 open_id"都是取错层——结果是 @ 前缀静默不渲染（不报错，难排查）。

## 何时用

- 用户要开发或维护飞书 bot：长连接事件订阅、消息收发、@ 提及、交互工作流（设状态 → 发文件 → 异步任务 → 总结回复）
- 用户报飞书 bot 问题：@ 不生效、收不到消息、权限报错、任务中断
- 参考实现：`backend/channels/feishu.py`（本项目），可整体照搬骨架

## 主线步骤

### 1. 架构选型
长连接（`lark_oapi.ws.Client`）优先于 webhook：**无需公网回调地址、无需端口映射**，事件推送到本地 WebSocket。启动即 `ws.start()` 阻塞。

完成判据：bot 日志出现 `connected to wss://msg-frontier.feishu.cn`，白名单群数、默认岗位打印正确。

### 2. 事件解析（事件层核心）
事件模型（`P2ImMessageReceiveV1Data`）：
```
data.event.sender    = EventSender    → sender_id: UserId(open_id/union_id/user_id)、sender_type
data.event.message   = EventMessage   → message_id、chat_id、message_type、content(JSON 字符串)
```
- `content` 是 JSON 字符串需 `json.loads`：文本消息取 `text`，文件消息取 `file_key`/`file_name`
- 注册：`EventDispatcherHandler.builder("","").register_p2_im_message_receive_v1(on_message).build()`
- 抽纯函数 `parse_message(dict) -> ParsedMessage`（I/O 之外可测）；lark SDK 惰性导入（`import lark_oapi` 放 `run_bot` 内），使纯逻辑测试不依赖 SDK

完成判据：消息事件能解析出 chat_id/message_id/msg_type/text 或 file_key；单测覆盖正常 + 异常 content。

### 3. @ 发送者（事件层坑）
- open_id 取 **`data.event.sender`**：`_extract_sender_open_id(sender) = sender.sender_id.open_id`（safety：None → ""）
- 总结消息前缀：`at_prefix = f'<at user_id="{open_id}"></at> ' if open_id else ""`
- `EventMessage` 无 sender 字段；`Sender` 类（有 `id` 字段）是**另一套模型**，别混用
- 验证手段：`im:message` 历史消息 API 拿 sender.open_id，或发一条带 `<at>` 的测试消息看渲染（蓝底白字=成功，原始 `<at>` 代码=失败）

完成判据：真实消息处理后总结开头出现 `@用户名`（蓝底可点击），非原始代码。

### 4. 交互流程（设状态 → 触发 → 异步回执）
- 文本设状态：匹配岗位 key → 存 `pending[chat_id]` → 回复确认；匹配不到静默忽略
- 文件触发任务：长连接要求 **3 秒内回执** → 耗时长任务必须后台线程跑（`threading.Thread(target=work, daemon=True).start()`）
- `work()` 内：screener 跑管线 → 总结回复（带 @）；异常 catch 回执"处理失败"；finally 清理状态
- 消息去重：`seen_msg_ids`（set + deque LRU 500）防断线重连后飞书重推在途事件 → 同一 message_id 只处理一次
- 白名单：`FEISHU_CHAT_WHITELIST`（逗号分隔 chat_id），不在白名单直接忽略

完成判据：文本设岗位有确认；发文件触发筛选且**立即**有收到确认（长连接不超时）；断线重连重推不重复处理。

### 5. 取消机制（协作式取消）
Python 线程不可强杀，用 `threading.Event` 做**协作式取消**：
- `active[chat_id] = threading.Event()` 在任务开始注册、finally 清理
- 收到"停"关键词（文本最优先，先于岗位匹配）→ `ev.set()` + 回复"已终止"；无 active 回复"当前没有在筛简历"
- 检查点：zip 逐份之间（`screen_archive(cancel_event=...)` 每次迭代前检查 `is_set()` 抛 `CancelledError`）、单份调用前后
- 进行中的单次 LLM 调用（≤120s）无法中途打断，等当前份完成即停

完成判据：长任务中途发"停"→ 停止后续份、不发送总结；无任务时发"停"→ 提示说明。

### 6. 权限与验证
发消息 `im:message:send_as_bot`；读历史消息 `im:message:readonly`（排查 @/拿 open_id 用）；**查群成员 `im:chat.members:read` 默认没有**——拿不到群成员 open_id，别依赖它。完整 scopes 表见 [`references/permissions.md`](references/permissions.md)。

完成判据：涉及新 API 时对照权限表核对 scope，报 `99991672 Access denied` 时按提示补 scope。

### 7. 测试纪律
- 纯逻辑（parse_message / make_handler / 岗位解析 / @ 提取 / 取消逻辑）单测，用 FakeChannel 记录 `notify` 文本断言
- 真实 lark 模型构造测试：`EventSender({"sender_id": {"open_id": "ou_x"}})` 断言 `_extract_sender_open_id`（防 SDK 事件结构漂移）
- 长任务用注入 runner 同步执行 / 真实线程 + Event 同步，避免时序 flaky

完成判据：`pytest` 全绿；@ 提取、取消、失败兜底均有断言测试。

## 排障速查

| 症状 | 根因 | 修法 |
|---|---|---|
| @ 不生效（总结无提及） | sender 取错层 / 字段错 | 从 `data.event.sender.sender_id.open_id` 取；加日志打 `sender_open_id` 定位 |
| `99991672 Access denied` | 缺 scope | 对照 [`references/permissions.md`](references/permissions.md) 补权限 |
| 长连接反复断开 | 网络 keepalive | 正常自动重连；确认事件订阅切到"长连接接收事件" |
| 同一消息重复处理 | 断线重推 | `seen_msg_ids` LRU 去重 |
| 任务筛一半断 | 单份异常冒泡 | 逐份兜底（重试 1 次 + 失败继续）+ LLM 空响应归 `TransientError` |

## 参考资料

- [`references/event-structure.md`](references/event-structure.md) — 事件模型字段图、注册代码骨架
- [`references/permissions.md`](references/permissions.md) — 权限 scopes 清单与用途
- [`references/patterns.md`](references/patterns.md) — 异步任务 / 取消 / 去重 / 进度+总结模式代码
