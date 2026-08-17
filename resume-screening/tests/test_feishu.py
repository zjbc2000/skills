"""飞书长连接 bot 逻辑（T08）：消息解析、白名单、异步筛选、回复。"""
from __future__ import annotations

from backend.channels.feishu import (
    ParsedMessage,
    build_summary,
    make_handler,
    parse_message,
)


class FakeChannel:
    def __init__(self):
        self.sent = []

    def notify(self, chat_id, text):
        self.sent.append((chat_id, text))


def _parsed(**kw):
    defaults = {
        "chat_id": "oc_1", "message_id": "om_1", "msg_type": "file",
        "file_key": "file_key_1", "file_name": "r.pdf",
    }
    defaults.update(kw)
    return ParsedMessage(**defaults)


def test_parse_file_message():
    m = parse_message({
        "chat_id": "oc_1", "message_id": "om_1", "msg_type": "file",
        "content": '{"file_key": "k1", "file_name": "r.pdf"}',
    })
    assert m.file_key == "k1"
    assert m.file_name == "r.pdf"


def test_parse_text_message():
    m = parse_message({
        "chat_id": "oc_1", "message_id": "om_1", "msg_type": "text",
        "content": '{"text": "hello"}',
    })
    assert m.text == "hello"


def test_parse_bad_content_safe():
    m = parse_message({
        "chat_id": "oc_1", "message_id": "om_1", "msg_type": "file", "content": "not json",
    })
    assert m.file_key is None


def test_handler_blocks_non_whitelisted_chat():
    ch = FakeChannel()
    calls = []
    handler = make_handler(ch, lambda fk, mid: calls.append(fk) or "ok",
                           whitelist={"oc_good"}, runner=lambda fn: fn())
    handler(_parsed(chat_id="oc_bad"))
    assert calls == []
    assert ch.sent == []


def test_handler_whitelisted_chat_screens_and_replies():
    ch = FakeChannel()
    seen = []
    handler = make_handler(ch, lambda fk, mid: seen.append((fk, mid)) or "判定：PASS",
                           whitelist={"oc_1"}, runner=lambda fn: fn())
    handler(_parsed())
    assert seen == [("file_key_1", "om_1")]
    assert ch.sent == [("oc_1", "判定：PASS")]


def test_handler_non_file_message_prompts_pdf():
    ch = FakeChannel()
    handler = make_handler(ch, lambda fk, mid: "x", whitelist={"oc_1"}, runner=lambda fn: fn())
    handler(_parsed(msg_type="text", file_key=None))
    assert "PDF" in ch.sent[0][1]


def test_handler_screener_error_reports_failure():
    ch = FakeChannel()

    def bad(fk, mid):
        raise RuntimeError("boom")

    handler = make_handler(ch, bad, whitelist={"oc_1"}, runner=lambda fn: fn())
    handler(_parsed())
    assert "失败" in ch.sent[0][1]


def test_build_summary_contains_scores_and_loader():
    result = {
        "verdict": type("V", (), {"g": 11, "s": 5, "t": 16, "red_lines_hit": []}),
        "snapshot": {"verdict": "pass", "thresholds": {"general": 8, "total": 16}},
        "doc": type("D", (), {"loader": "layout_parsing"}),
    }
    s = build_summary(result)
    assert "PASS" in s
    assert "G=11" in s and "S=5" in s and "T=16" in s
    assert "layout_parsing" in s


def test_build_summary_lists_red_lines():
    result = {
        "verdict": type("V", (), {"g": 0, "s": 0, "t": 0, "red_lines_hit": ["失信记录"]}),
        "snapshot": {"verdict": "fail", "thresholds": {"general": 8, "total": 16}},
        "doc": type("D", (), {"loader": "local_pymupdf"}),
    }
    assert "失信记录" in build_summary(result)
