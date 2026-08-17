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


def make_call_fn(cfg) -> Callable:
    """返回 call(provider, model, prompt, feedback=None) -> str。"""

    def call(
        provider: str, model: str, prompt: str, feedback: Optional[str] = None
    ) -> str:
        pcfg = cfg.providers[provider]
        try:
            api_key = os.environ[pcfg["api_key_env"]]
        except KeyError as e:
            raise LLMError(f"缺少环境变量 {pcfg['api_key_env']}") from e
        client = OpenAI(base_url=pcfg["base_url"], api_key=api_key)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
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
