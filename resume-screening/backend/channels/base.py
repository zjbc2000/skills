"""频道抽象：notify 统一接口（SPEC §5.4）。"""
from __future__ import annotations

from abc import ABC, abstractmethod


class ChannelError(Exception):
    pass


class Channel(ABC):
    @abstractmethod
    def notify(self, chat_id: str, text: str) -> None:
        """向会话推送纯文本。"""
