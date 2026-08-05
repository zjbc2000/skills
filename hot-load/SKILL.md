---
name: "hot-load"
description: "生成代码热重载命令，把修改的 Python 文件 scp 到远程服务器并 docker cp 到对应容器后重启。Invoke when user asks for 热重载/hot reload/restart containers/更新代码到服务器，or after editing Python files that need deploying to remote Docker containers."
---

# 热重载（Hot-Load）

把本地修改的 Python 文件同步到远程服务器 Docker 容器，避免完整镜像构建。

## 1. 容器职责与队列映射

| 容器名 | 队列（-Q） | 负责的任务 | 主要代码路径 |
|---|---|---|---|
| `ai-bidding-writer` | — | FastAPI Web 服务，所有 HTTP 接口 | `app/api/**`, `app/services/**`, `app/schemas/**`, `app/utils/**` |
| `ai-bidding-celery-short` | `high_priority,default` | 短任务：目录生成、单章节写作、项目 CRUD 副作用 | `app/tasks/catalog_task.py`, `app/tasks/write_task.py`, `app/services/**` |
| `ai-bidding-celery-long` | `long_writing` | 长任务：批量章节写作、整篇重写 | `app/tasks/write_task.py`, `app/services/**` |
| `ai-bidding-celery-dispatcher` | `batch_dispatcher` | 派发任务：批量写作入口，分发到 long 队列 | `app/tasks/write_task.py` |
| `ai-bidding-celery-parse` | `ocr_parse` | OCR 解析任务：`parse_bidding_files` | `app/tasks/parse_task.py`, `app/utils/paddle_ocr.py`, `app/utils/document_layout.py`, `app/utils/document_parser.py`, `app/utils/mineru_client.py`, `app/utils/gotenberg.py` |
| `ai-bidding-celery-check` | `llm_check` | 检查任务：`execute_bid_check`, `refresh_category_check` | `app/tasks/check_task.py`, `app/services/bid_check_service.py`, `app/utils/**` |

## 2. 文件 → 容器映射规则

**默认规则**：所有 celery 容器都加载 `app/` 下任何文件（因为共享同一镜像代码）。但**为减少重启范围**，按文件路径判断需要更新的容器：

| 修改的文件 | 需要更新的容器 |
|---|---|
| `app/api/v1/endpoints/*.py` | writer（+ 所有 celery，若 endpoint 逻辑被 celery 间接调用） |
| `app/services/*.py` | writer + celery-short + celery-long + celery-dispatcher + celery-check |
| `app/tasks/catalog_task.py` | celery-short |
| `app/tasks/write_task.py` | celery-short + celery-long + celery-dispatcher |
| `app/tasks/parse_task.py` | celery-parse |
| `app/tasks/check_task.py` | celery-check |
| `app/utils/paddle_ocr.py` | writer + celery-parse |
| `app/utils/mineru_client.py` | writer + celery-parse |
| `app/utils/document_layout.py` | writer + celery-parse |
| `app/utils/document_parser.py` | writer + celery-parse |
| `app/utils/gotenberg.py` | writer + celery-parse |
| `app/utils/llm_client.py` | writer + celery-check + celery-long + celery-short |
| `app/utils/ai_client.py` | writer + celery-check + celery-long + celery-short |
| `app/utils/file_service.py` | writer + 所有 celery |
| `app/utils/markdown_grep.py` | writer + celery-short + celery-long |
| `app/config/settings.py` | writer + 所有 celery |
| `app/core/celery_app.py` | writer + 所有 celery |
| `app/core/llm.py` | writer + 所有 celery |
| `app/prompts/*.md` | writer + celery-short + celery-long + celery-dispatcher |
| `app/schemas/*.py` | writer（+ 涉及的 celery） |

## 3. 生成热重载命令

参考模板（修改的文件路径为 `app/services/ai_writing_service.py`）：

```bash
scp app/services/ai_writing_service.py root@ecs.imytimes.com:/data/docker/ai_writing_service.py
ssh root@ecs.imytimes.com "\
  docker cp /data/docker/ai_writing_service.py ai-bidding-writer:/app/app/services/ai_writing_service.py && \
  docker cp /data/docker/ai_writing_service.py ai-bidding-celery-short:/app/app/services/ai_writing_service.py && \
  docker cp /data/docker/ai_writing_service.py ai-bidding-celery-long:/app/app/services/ai_writing_service.py && \
  docker cp /data/docker/ai_writing_service.py ai-bidding-celery-dispatcher:/app/app/services/ai_writing_service.py && \
  docker cp /data/docker/ai_writing_service.py ai-bidding-celery-check:/app/app/services/ai_writing_service.py && \
  docker restart ai-bidding-writer ai-bidding-celery-short ai-bidding-celery-long ai-bidding-celery-dispatcher ai-bidding-celery-check"
```

**多文件场景**（一次改多个文件）：scp 多个文件到 `/data/docker/`，然后多次 docker cp，最后一次性 restart 所有相关容器：

```bash
scp app/utils/paddle_ocr.py app/api/v1/endpoints/ai_writing.py root@ecs.imytimes.com:/data/docker/
ssh root@ecs.imytimes.com "\
  docker cp /data/docker/paddle_ocr.py ai-bidding-writer:/app/app/utils/paddle_ocr.py && \
  docker cp /data/docker/paddle_ocr.py ai-bidding-celery-parse:/app/app/utils/paddle_ocr.py && \
  docker cp /data/docker/ai_writing.py ai-bidding-writer:/app/app/api/v1/endpoints/ai_writing.py && \
  docker restart ai-bidding-writer ai-bidding-celery-parse"
```

## 4. 生成命令的步骤

1. **收集修改的文件列表**（从用户输入或 git diff）
2. **查表**：每个文件需要更新到哪些容器（参考第 2 节）
3. **合并容器集合**：所有文件涉及的容器取并集
4. **scp 阶段**：把所有文件 scp 到 `root@ecs.imytimes.com:/data/docker/`（用 basename）
5. **docker cp 阶段**：每个文件对每个相关容器做一次 docker cp
6. **restart 阶段**：一次性 restart 所有涉及的容器

## 5. 注意事项

- **scp 目录用 basename**：`app/services/foo.py` → `/data/docker/foo.py`（不要带子目录）
- **docker cp 目标路径要保留原路径结构**：`/app/app/services/foo.py`
- **服务器 SSH 端口**：默认 22，如非默认需在 scp 加 `-P 端口`，ssh 加 `-p 端口`
- **密码**：如需非交互式，用 `sshpass -p '密码'` 或配置 SSH key
- **重启顺序**：restart 可以一次性多个容器，Docker 会并行重启
- **不需要重启的容器不要重启**：减少影响范围

## 6. 快速参考表（常见组合）

| 场景 | 修改的文件 | 需重启的容器 |
|---|---|---|
| 改 API 接口 | `app/api/v1/endpoints/xxx.py` | writer |
| 改 Service | `app/services/xxx.py` | writer + celery-short + celery-long + celery-dispatcher + celery-check |
| 改解析逻辑 | `app/tasks/parse_task.py`, `app/utils/paddle_ocr.py` | celery-parse（+ writer 如果 paddle_ocr 也被 writer 调用） |
| 改检查逻辑 | `app/tasks/check_task.py` | celery-check |
| 改写作任务 | `app/tasks/write_task.py` | celery-short + celery-long + celery-dispatcher |
| 改目录生成 | `app/tasks/catalog_task.py` | celery-short |
| 改配置 | `app/config/settings.py` | writer + 所有 celery |
| 改 LLM 客户端 | `app/utils/llm_client.py` | writer + celery-check + celery-long + celery-short |
| 改 Prompt 模板 | `app/prompts/xxx.md` | writer + celery-short + celery-long + celery-dispatcher |
