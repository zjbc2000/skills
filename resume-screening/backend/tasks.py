"""进程内异步任务（v0.15）：线程执行 + 日志缓冲 + 状态查询。

本地单进程 uvicorn 场景够用；任务在 daemon 线程跑（不阻塞事件循环），
日志按行追加，GET /tasks/{id} 返回累计日志与最终结果。
"""
from __future__ import annotations

import threading
import uuid
from typing import Callable, Dict, Optional


class TaskManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: Dict[str, dict] = {}
        self._logs: Dict[str, list] = {}

    def submit(self, fn: Callable, *args, **kwargs) -> str:
        """fn(log, *args, **kwargs) 在线程中执行；log 为追加日志的可调用对象。"""
        tid = uuid.uuid4().hex
        with self._lock:
            self._tasks[tid] = {"id": tid, "status": "pending", "error": None}
            self._logs[tid] = []

        def run() -> None:
            log = self._logs[tid].append
            with self._lock:
                self._tasks[tid]["status"] = "running"
            try:
                result = fn(log, *args, **kwargs)
                with self._lock:
                    t = self._tasks[tid]
                    t["status"] = "done"
                    t["result"] = result
            except Exception as e:  # noqa: BLE001 任务边界：任何异常都落为 failed
                with self._lock:
                    t = self._tasks[tid]
                    t["status"] = "failed"
                    t["error"] = str(e)

        threading.Thread(target=run, daemon=True).start()
        return tid

    def get(self, tid: str) -> Optional[dict]:
        with self._lock:
            t = self._tasks.get(tid)
            if t is None:
                return None
            return {**t, "logs": list(self._logs.get(tid, []))}


tasks = TaskManager()
