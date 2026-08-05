---
name: "llm-log"
description: "为大模型（LLM）调用代码补全诊断日志。Use when writing or modifying code that calls LLM APIs (chat completions, embeddings, reranking), including app/utils/llm_client.py, app/tasks/*.py, app/services/*.py. 触发场景：用户提到 LLM 调用/大模型/Qwen/OpenAI/chat completions，或代码涉及 llm_client.chat / chat_with_retry / chat_with_tools，或排查 LLM 返回空/JSON 解析失败/fallback/超时/响应异常。"
---

# LLM 调用日志规范

为 LLM 调用代码补全 `loguru` 诊断日志，确保失败时可定位根因。

## 1. 何时使用

**必须加日志的场景：**
- 新写 LLM 调用代码（`llm_client.chat` / `chat_with_retry` / `chat_with_tools`）
- 修改现有 LLM 调用
- 排查 LLM 返回空 content / JSON 解析失败 / fallback 触发 / 响应异常
- 用户反馈"LLM 没生效""评分满分""解析失败""任务卡住"

**不需要加日志的场景：**
- 普通 HTTP 调用（非 LLM）
- 已有充分日志的代码
- 单元测试代码

## 2. 四个关键日志点

每处 LLM 调用必须有这四个日志点：

### 2.1 调用前（INFO）

```python
from loguru import logger

logger.info(
    f"[模块] 任务名 LLM call starting | "
    f"messages_count={len(messages)} | "
    f"estimated_input_tokens={sum(len(m.get('content', '')) for m in messages) // 3} | "
    f"temperature={temperature} | max_tokens={max_tokens}"
)
```

### 2.2 响应后（INFO）

```python
choice = (response.get("choices") or [{}])[0]
message = choice.get("message") or {}
content = message.get("content", "") or ""
finish_reason = choice.get("finish_reason")
usage = response.get("usage") or {}
message_keys = list(message.keys())

logger.info(
    f"[模块] 任务名 LLM response | "
    f"finish_reason={finish_reason} | "
    f"message_keys={message_keys} | "
    f"usage={usage} | "
    f"content_len={len(content)} | "
    f"content_first_200={content[:200]!r}"
)
```

### 2.3 异常时（WARNING/ERROR）

```python
except Exception as exc:
    logger.warning(
        f"[模块] 任务名 LLM call failed, fallback to xxx | "
        f"error_type={type(exc).__name__} | "
        f"error={exc}"
    )
    return _fallback_xxx()
```

### 2.4 降级时（WARNING）

```python
if not isinstance(parsed, dict):
    logger.warning(
        f"[模块] 任务名 JSON parse failed, fallback to xxx | "
        f"content_first_200={content[:200]!r}"
    )
    return _fallback_xxx()
```

## 3. 关键诊断字段

| 字段 | 作用 | 异常值含义 |
|---|---|---|
| `finish_reason` | 响应结束原因 | `length`=被 max_tokens 截断；`stop`=正常；`tool_calls`=工具调用 |
| `message_keys` | message 字段列表 | 含 `reasoning`=thinking 模式开启 |
| `usage.completion_tokens` | 生成 token 数 | 接近 `max_tokens`=可能被截断 |
| `content_len` | content 长度 | `0`=thinking 消耗完 token 或 LLM 异常 |
| `content_first_200` | content 前 200 字符 | 用于排查 JSON 格式问题、markdown fence、trailing comma |

## 4. 真实案例：评分任务诊断

[check_task.py:341-355](app/tasks/check_task.py) 的评分日志（基于此 skill 修复的真实 bug）：

```python
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(
            async_llm_client.chat(messages, temperature=0.1, max_tokens=16000)
        )
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content", "") or ""
        finish_reason = choice.get("finish_reason")
        usage = response.get("usage") or {}
        message_keys = list(message.keys())
        logger.info(
            f"[Check] Dimension scoring LLM response | "
            f"finish_reason={finish_reason} | "
            f"message_keys={message_keys} | "
            f"usage={usage} | "
            f"content_len={len(content)} | "
            f"content_first_200={content[:200]!r}"
        )
    finally:
        try:
            loop.run_until_complete(async_llm_client.aclose())
        except Exception:
            pass
        loop.close()
except Exception as exc:
    logger.warning(f"[Check] Dimension scoring LLM call failed, fallback to full score: {exc}")
    return _fallback_full_score_dimensions()

parsed = async_llm_client.extract_json(content)
if not isinstance(parsed, dict):
    logger.warning(
        f"[Check] Dimension scoring JSON parse failed, fallback to full score | "
        f"content_first_200={content[:200]!r}"
    )
    return _fallback_full_score_dimensions()

logger.info(f"[Check] Dimension scoring parsed successfully | keys={list(parsed.keys())}")
return _normalize_llm_dimension_scores(parsed)
```

该日志曾定位到的真实 bug：
```
finish_reason=length | message_keys=[..., 'reasoning'] | content_len=0 | completion_tokens=4000
```
→ 诊断：Qwen3 thinking 模式消耗完 max_tokens，content 完全为空。

## 5. 日志前缀规范

不同模块用不同前缀，便于 grep：

| 模块 | 前缀 | 示例 |
|---|---|---|
| 检查任务 | `[Check]` | `[Check] Dimension scoring LLM response` |
| 解析任务 | `[Parse]` | `[Parse] LLM extraction response` |
| 写作任务 | `[Write]` | `[Write] Section xxx LLM response` |
| 目录生成 | `[Catalog]` | `[Catalog] Generate LLM response` |
| RAG 检索 | `[RAG]` | `[RAG] Search LLM response` |
| Embedding | `[Embed]` | `[Embed] Embedding call response` |
| Rerank | `[Rerank]` | `[Rerank] Rerank call response` |

## 6. 日志级别

| 级别 | 场景 |
|---|---|
| `logger.info` | 调用前参数、响应后元数据、解析成功 |
| `logger.warning` | LLM 调用失败但有 fallback、JSON 解析失败但有 fallback、超时重试 |
| `logger.error` | LLM 调用失败且无 fallback、关键任务失败 |
| `logger.debug` | 完整 messages 内容（仅开发环境，生产不输出） |

## 7. 反模式

### ❌ 不要打印完整 content

```python
# 错误：content 可能几千字符，污染日志
logger.info(f"LLM response: {content}")
```

```python
# 正确：只打印前 200 字符
logger.info(f"LLM response | content_first_200={content[:200]!r}")
```

### ❌ 不要打印 API Key / 完整 messages

```python
# 错误：泄露敏感信息
logger.info(f"LLM request: {messages}")
```

```python
# 正确：只打印元数据
logger.info(f"LLM call starting | messages_count={len(messages)}")
```

### ❌ 不要用 print

```python
# 错误：不受日志级别控制，生产环境无法关闭
print(f"LLM response: {content}")
```

```python
# 正确：用 loguru
logger.info(f"LLM response | content_len={len(content)}")
```

### ❌ 不要省略 finish_reason 和 message_keys

```python
# 错误：无法诊断 thinking 模式 / 截断问题
logger.info(f"LLM response | content_len={len(content)}")
```

```python
# 正确：包含 finish_reason 和 message_keys
logger.info(
    f"LLM response | finish_reason={finish_reason} | "
    f"message_keys={message_keys} | content_len={len(content)}"
)
```

## 8. 验证清单

写完 LLM 调用代码后，检查：

- [ ] 调用前有 `logger.info` 记录参数（messages_count, temperature, max_tokens）
- [ ] 响应后有 `logger.info` 记录 `finish_reason`、`message_keys`、`usage`、`content_len`、`content_first_200`
- [ ] 异常时有 `logger.warning` 记录 error_type 和 error 消息
- [ ] 降级时有 `logger.warning` 记录 fallback 原因和 content 前 200 字符
- [ ] 成功路径有 `logger.info` 记录解析结果（如 `keys=...`）
- [ ] 日志前缀符合规范（`[Check]` / `[Parse]` / `[Write]` 等）
- [ ] 没有打印完整 content / messages / API Key
- [ ] 用 `loguru.logger`，不用 `print`

## 9. 快速应用

修改 LLM 调用代码时，按此模板套用：

```python
from loguru import logger

# 1. 调用前
logger.info(f"[模块] 任务名 LLM call starting | messages_count={len(messages)} | max_tokens={max_tokens}")

try:
    # 2. LLM 调用
    response = ...  # llm_client.chat(...)
    
    # 3. 响应后
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content", "") or ""
    logger.info(
        f"[模块] 任务名 LLM response | "
        f"finish_reason={choice.get('finish_reason')} | "
        f"message_keys={list(message.keys())} | "
        f"usage={response.get('usage', {})} | "
        f"content_len={len(content)} | "
        f"content_first_200={content[:200]!r}"
    )
except Exception as exc:
    # 4. 异常
    logger.warning(f"[模块] 任务名 LLM call failed, fallback to xxx | error_type={type(exc).__name__} | error={exc}")
    return _fallback_xxx()

# 5. 解析
parsed = extract_json(content)
if not parsed:
    # 6. 降级
    logger.warning(f"[模块] 任务名 JSON parse failed, fallback to xxx | content_first_200={content[:200]!r}")
    return _fallback_xxx()

# 7. 成功
logger.info(f"[模块] 任务名 parsed successfully | keys={list(parsed.keys()) if isinstance(parsed, dict) else 'N/A'}")
return parsed
```
