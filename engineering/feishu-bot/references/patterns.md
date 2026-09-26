# 飞书 bot 模式（异步 / 取消 / 去重 / 消息整合）

以下模式来自本项目 `backend/channels/feishu.py`，可整体照搬骨架。

## 处理器骨架（make_handler）

```python
def make_handler(channel, screener, whitelist, jd_map=None, default_jd="", runner=None):
    jd_map = jd_map or {}
    pending = {}          # chat_id -> {"jd": key, "mode": mode}
    active = {}           # chat_id -> threading.Event（取消标志）
    seen_msg_ids = set()  # 消息去重
    seen_msg_queue = deque(maxlen=500)

    def default_runner(fn):
        threading.Thread(target=fn, daemon=True).start()

    run_fn = runner or default_runner

    def handle(parsed):
        if parsed.chat_id not in whitelist:
            return                                   # 白名单过滤
        if parsed.message_id in seen_msg_ids:
            return                                   # 去重（断线重推）
        seen_msg_ids.add(parsed.message_id)
        if parsed.msg_type == "text":
            if "停" in (parsed.text or ""):          # 取消：最优先于岗位匹配
                ev = active.get(parsed.chat_id)
                if ev is not None:
                    ev.set()
                    channel.notify(parsed.chat_id, "已终止当前筛选")
                else:
                    channel.notify(parsed.chat_id, "当前没有在筛简历")
                return
            key = extract_jd_key(parsed.text or "", jd_map)
            if key:
                pending[parsed.chat_id] = {"jd": key, "mode": "general"}
                channel.notify(parsed.chat_id, f"岗位已设为：{key}，请发送简历")
            return
        if parsed.msg_type != "file" or not parsed.file_key:
            channel.notify(parsed.chat_id, "请发送 PDF 简历文件")
            return
        jd_ref = pending.pop(parsed.chat_id, {}).get("jd") or default_jd
        if not jd_ref:
            channel.notify(parsed.chat_id, "未指定岗位：请先输入岗位名")
            return

        def work():
            ev = threading.Event()                   # 注册取消标志
            active[parsed.chat_id] = ev
            try:
                summary = screener(parsed.file_key, parsed.message_id, parsed.file_name,
                                   jd_ref, "general", parsed.chat_id, cancel_event=ev)
            except CancelledError:
                channel.notify(parsed.chat_id, "筛选已终止")
                return
            except Exception as e:
                channel.notify(parsed.chat_id, f"处理失败：{e}")
                return
            finally:
                active.pop(parsed.chat_id, None)
            at = f'<at user_id="{parsed.sender_open_id}"></at> ' if parsed.sender_open_id else ""
            channel.notify(parsed.chat_id, at + summary)

        run_fn(work)   # 后台线程：长连接 3 秒回执限制

    return handle
```

## 协作式取消

- Python 线程不可强杀 → `threading.Event` 标志 + **检查点**（zip 逐份之间、单份调用前后）
- `screen_archive(..., cancel_event=...)` 每次迭代前 `if cancel_event.is_set(): raise CancelledError`
- 进行中的单次 LLM 调用（≤120s 超时）无法打断，等当前份完成即停
- 取消不发送总结（work 捕获 `CancelledError` 后回执"筛选已终止"）

## 逐份失败兜底（不中断整包）

```python
for i, p in enumerate(pdfs, 1):
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError("筛选已取消")
    result = None
    for attempt in range(2):  # 初始 + 重试 1 次
        try:
            result = screen_fn(p)
            break
        except Exception as e:
            logger.warning("第 %d/%d 份失败: %s: %s", i, len(pdfs), p.name, e)
    if result is None:
        failed.append(p.name)
        continue
    parts.append(build_summary(result))
text = "\n\n".join(parts)
if failed:
    text += f"\n\n⚠️ 另有 {len(failed)} 份处理失败：{'、'.join(failed)}"
```

## LLM 空响应重试

- 空响应（模型偶发）归为 `TransientError`（瞬时错误）→ 走 `LLMClient` 现有重试 + provider 降级，**不直接中断整包**
- 区别于 `LLMError`（终态错误，直接冒泡）

## 进度消息 + 总结去重

- 进度消息：`on_progress(i, n, name, score)` → `第 1/12：张三，综合分80`（i=0 发"收到 N 份"）
- **总结去重**：判定/G/S/T 等详细结果放 HTML 文件（`render_results_html`），bot 总结只发一句话结论（`conclusion_line`：`全部不通过：张三`），避免重复
- 最终消息 = `@发送者 + 一句话结论`

## 消息去重（防重推）

```python
if parsed.message_id in seen_msg_ids:
    return
if len(seen_msg_queue) == seen_msg_queue.maxlen:
    seen_msg_ids.discard(seen_msg_queue[0])   # deque 同步丢最旧，保持 set 一致
seen_msg_queue.append(parsed.message_id)
seen_msg_ids.add(parsed.message_id)
```

## 测试注入

```python
class FakeChannel:
    def __init__(self): self.sent = []
    def notify(self, chat_id, text): self.sent.append((chat_id, text))

# 同步 runner：长任务测试注入 runner=lambda fn: fn()；取消测试用真实线程 + Event 同步
handler = make_handler(ch, screener, whitelist={"oc_1"}, runner=lambda fn: fn())
```
