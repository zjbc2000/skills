"""飞书长连接双向 bot（SPEC §6）。

纯逻辑（parse_message / make_handler / build_summary）可测；
飞书 I/O（FeishuChannel / make_lark_screener / run_bot）惰性导入 lark SDK。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Set

from ..screening.pipeline import build_summary
from .base import Channel, ChannelError


@dataclass(frozen=True)
class ParsedMessage:
    chat_id: str
    message_id: str
    msg_type: str
    file_key: Optional[str] = None
    file_name: Optional[str] = None
    text: Optional[str] = None


def parse_message(message: dict) -> ParsedMessage:
    """从事件消息体解析出结构化消息（纯函数，可测）。"""
    content = {}
    raw = message.get("content") or ""
    if isinstance(raw, str) and raw.strip():
        try:
            content = json.loads(raw)
        except ValueError:
            content = {}
    return ParsedMessage(
        chat_id=message.get("chat_id", ""),
        message_id=message.get("message_id", ""),
        msg_type=message.get("msg_type", ""),
        file_key=content.get("file_key"),
        file_name=content.get("file_name"),
        text=content.get("text"),
    )


def extract_jd_key(text: str, jd_map: dict) -> Optional[str]:
    """从消息文本里按格式提取 jd_map 的岗位 key（确定性匹配，非模型提取）。"""
    for key in jd_map:
        if key and key in (text or ""):
            return key
    return None


def make_handler(
    channel: Channel,
    screener: Callable,
    whitelist: Set[str],
    jd_map: Optional[dict] = None,
    default_jd: str = "",
    runner=None,
) -> Callable:
    """生成单条消息处理器。

    交互：@bot 发文本设岗位（格式匹配 jd_map key）→ 发简历 → 异步筛选 → 纯文本回复。
    chat 内的 pending 岗位用完即清；未设置则用 default_jd；都没有则提示。
    runner 用于测试注入同步执行；默认后台线程（长连接需 3 秒内回执）。
    """
    jd_map = jd_map or {}
    pending: dict = {}

    def default_runner(fn):
        threading.Thread(target=fn, daemon=True).start()

    run_fn = runner or default_runner

    def handle(parsed: ParsedMessage) -> None:
        if parsed.chat_id not in whitelist:
            return
        if parsed.msg_type == "text":
            key = extract_jd_key(parsed.text or "", jd_map)
            if key:
                pending[parsed.chat_id] = key
                channel.notify(parsed.chat_id, f"岗位已设为：{key}，请发送简历")
            else:
                channel.notify(parsed.chat_id, "请发送 jd_map 中的岗位名（如 @我 输入岗位 key）")
            return
        if parsed.msg_type != "file" or not parsed.file_key:
            channel.notify(parsed.chat_id, "请发送 PDF 简历文件（可先 @我 输入岗位）")
            return

        jd_ref = pending.pop(parsed.chat_id, default_jd)
        if not jd_ref:
            channel.notify(parsed.chat_id, "未指定岗位：请先 @我 输入岗位名")
            return

        def work():
            try:
                summary = screener(parsed.file_key, parsed.message_id, parsed.file_name, jd_ref)
            except Exception as e:  # noqa: BLE001 —— 出错必须回执，不静默
                channel.notify(parsed.chat_id, f"处理失败：{e}")
                return
            channel.notify(parsed.chat_id, summary)

        run_fn(work)

    return handle


class FeishuChannel(Channel):
    def __init__(self, client):
        self._client = client

    def notify(self, chat_id: str, text: str) -> None:
        from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

        body = (
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text}, ensure_ascii=False))
            .build()
        )
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(body)
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise ChannelError(f"发送失败: {resp.code} {resp.msg}")


def make_lark_screener(client, screen_fn: Callable[[Path, str], dict]) -> Callable:
    """下载消息文件 → 跑管线 → 纯文本摘要（zip 走安全解压逐份筛）。

    screen_fn(path, jd_ref) -> dict；screener(file_key, message_id, file_name, jd_ref) -> str。
    """
    from lark_oapi.api.im.v1 import GetMessageResourceRequest

    def screener(file_key: str, message_id: str, file_name: str = None, jd_ref: str = "") -> str:
        req = (
            GetMessageResourceRequest.builder()
            .message_id(message_id)
            .file_key(file_key)
            .type("file")
            .build()
        )
        resp = client.im.v1.message_resource.get(req)
        if not resp.success():
            raise ChannelError(f"下载失败: {resp.code} {resp.msg}")
        blob = resp.data.file if hasattr(resp.data, "file") else resp.data.resource
        suffix = Path(file_name or "resume.pdf").suffix.lower() or ".pdf"
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(blob)
        try:
            tmp_path = Path(tmp)
            if suffix == ".zip":
                from ..archive import screen_archive

                return screen_archive(tmp_path, lambda p: screen_fn(p, jd_ref))
            return build_summary(screen_fn(tmp_path, jd_ref))
        finally:
            Path(tmp).unlink(missing_ok=True)

    return screener


def run_bot(
    app_id: str,
    app_secret: str,
    whitelist: Set[str],
    screen_fn: Callable[[Path, str], dict],
    jd_map: Optional[dict] = None,
    default_jd: str = "",
) -> None:
    """启动长连接 bot（阻塞）。需在飞书开放平台将事件订阅切换为「使用长连接接收事件」。"""
    import lark_oapi

    client = lark_oapi.Client.builder().app_id(app_id).app_secret(app_secret).build()
    channel = FeishuChannel(client)
    screener = make_lark_screener(client, screen_fn)
    handler = make_handler(channel, screener, whitelist, jd_map=jd_map or {}, default_jd=default_jd)

    def on_message(data):
        msg = data.event.message
        handler(parse_message({
            "message_id": msg.message_id,
            "chat_id": msg.chat_id,
            "msg_type": msg.msg_type,
            "content": msg.content,
        }))

    dispatcher = (
        lark_oapi.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message)
        .build()
    )
    ws = lark_oapi.ws.Client(app_id, app_secret, event_handler=dispatcher)
    ws.start()
