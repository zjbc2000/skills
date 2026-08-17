"""飞书长连接 bot 逻辑（T08/T09）：消息解析、岗位设置、白名单、异步筛选、回复。"""
from __future__ import annotations

from backend.channels.feishu import (
    ParsedMessage,
    extract_jd_key,
    make_handler,
    parse_message,
)
from backend.screening.pipeline import build_summary

JD_MAP = {"西安AE": {}, "后端": {}}


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


def _handler(ch, screener, jd_map=JD_MAP, default_jd="", runner=None):
    return make_handler(ch, screener, whitelist={"oc_1"}, jd_map=jd_map,
                        default_jd=default_jd, runner=runner or (lambda fn: fn()))


# --- 消息解析 ---


def test_parse_file_message():
    m = parse_message({
        "chat_id": "oc_1", "message_id": "om_1", "msg_type": "file",
        "content": '{"file_key": "k1", "file_name": "r.pdf"}',
    })
    assert m.file_key == "k1"
    assert m.file_name == "r.pdf"


def test_parse_bad_content_safe():
    m = parse_message({
        "chat_id": "oc_1", "message_id": "om_1", "msg_type": "file", "content": "not json",
    })
    assert m.file_key is None


# --- 岗位 key 提取（格式匹配，非模型） ---


def test_extract_jd_key_matches_substring():
    assert extract_jd_key("帮我看看西安AE这个岗", JD_MAP) == "西安AE"


def test_extract_jd_key_returns_none():
    assert extract_jd_key("随便看看", JD_MAP) is None


def test_extract_jd_key_empty_text():
    assert extract_jd_key("", JD_MAP) is None


# --- 处理器：白名单 / 岗位 / 文件 ---


def test_handler_blocks_non_whitelisted_chat():
    ch = FakeChannel()
    calls = []
    handler = make_handler(ch, lambda *a: calls.append(a) or "ok",
                           whitelist={"oc_good"}, jd_map=JD_MAP, default_jd="西安AE",
                           runner=lambda fn: fn())
    handler(_parsed(chat_id="oc_bad"))
    assert calls == []
    assert ch.sent == []


def test_handler_text_sets_pending_jd():
    ch = FakeChannel()
    handler = _handler(ch, lambda *a: "ok")
    handler(_parsed(msg_type="text", text="西安AE", file_key=None))
    assert "岗位已设为：西安AE" in ch.sent[0][1]


def test_handler_text_unknown_jd_prompts():
    ch = FakeChannel()
    handler = _handler(ch, lambda *a: "ok")
    handler(_parsed(msg_type="text", text="瞎写的岗位", file_key=None))
    assert "jd_map 中的岗位名" in ch.sent[0][1]


def test_handler_file_uses_pending_jd():
    ch = FakeChannel()
    seen = []
    handler = _handler(ch, lambda fk, mid, name, jd: seen.append(jd) or "判定：PASS")
    handler(_parsed(msg_type="text", text="后端", file_key=None))  # 设岗位
    handler(_parsed())  # 发简历
    assert seen == ["后端"]
    assert ch.sent[-1][1] == "判定：PASS"


def test_handler_file_without_pending_uses_default():
    ch = FakeChannel()
    seen = []
    handler = _handler(ch, lambda fk, mid, name, jd: seen.append(jd) or "ok", default_jd="西安AE")
    handler(_parsed())  # 没设岗位直接用默认
    assert seen == ["西安AE"]


def test_handler_file_without_any_jd_prompts():
    ch = FakeChannel()
    handler = _handler(ch, lambda *a: "ok")  # default_jd=""
    handler(_parsed())
    assert "未指定岗位" in ch.sent[0][1]


def test_handler_non_file_message_prompts_pdf():
    ch = FakeChannel()
    handler = _handler(ch, lambda *a: "ok", default_jd="西安AE")
    handler(_parsed(msg_type="file", file_key=None))  # 文件消息但无 file_key
    assert "PDF" in ch.sent[0][1]


def test_handler_screener_error_reports_failure():
    ch = FakeChannel()

    def bad(fk, mid, name, jd):
        raise RuntimeError("boom")

    handler = _handler(ch, bad, default_jd="西安AE")
    handler(_parsed())
    assert "失败" in ch.sent[0][1]


# --- 摘要 ---


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
