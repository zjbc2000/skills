"""真实 LLM 调用（OpenAI 兼容，SPEC §5.1）。"""
from __future__ import annotations

import os
from typing import Callable, Optional

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)

from ..scoring.prompts import SYSTEM_PROMPT
from .llm_client import LLMError, TransientError

# 单次 LLM 调用超时（秒）。不设则会用 openai SDK 默认 600s：
# 网络卡死时任务线程阻塞 10 分钟，前端表现为"无响应"。60s 内失败即抛错回落 failed 队列。
REQUEST_TIMEOUT_SECONDS = 60.0


def make_call_fn(cfg, system_prompt: str = SYSTEM_PROMPT) -> Callable:
    """返回 call(provider, model, prompt, feedback=None) -> str。

    system_prompt 可注入：默认评分提示词；JD 抽取等任务传各自提示词，
    否则模型按评分格式输出、校验永远失败、触发全链重试（表现为任务长时间挂起）。
    """

    def call(
        provider: str, model: str, prompt: str, feedback: Optional[str] = None
    ) -> str:
        pcfg = cfg.providers[provider]
        try:
            api_key = os.environ[pcfg["api_key_env"]]
        except KeyError as e:
            raise LLMError(f"缺少环境变量 {pcfg['api_key_env']}") from e
        client = OpenAI(
            base_url=pcfg["base_url"], api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        if feedback:
            messages.append(
                {"role": "user", "content": f"上次输出不合规：{feedback}。请重新输出合法 JSON。"}
            )
        try:
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
        except (APIConnectionError, APITimeoutError) as e:
            raise TransientError(f"连接/超时: {e}") from e
        except APIStatusError as e:
            if e.status_code == 429 or e.status_code >= 500:
                raise TransientError(f"服务端状态 {e.status_code}") from e
            raise LLMError(f"API 错误 {e.status_code}: {e}") from e
        content = resp.choices[0].message.content if resp.choices else None
        if not content:
            raise LLMError("模型返回空响应")
        return content

    return call
