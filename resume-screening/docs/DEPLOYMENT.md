# 部署与本地环境

## 本地开发环境

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+（推荐 3.11） | 后端运行；用系统 `python3`，避免 conda `bidding_env` 缺依赖 |
| Node.js | 18+ | 前端 vite 构建 |
| Docker | 可选 | 生产部署用 |

Python 依赖：`pip install -r requirements.txt`（pymupdf / openai / PyYAML / python-dotenv / requests / lark-oapi / python-docx）。
前端依赖：`cd web && npm install`。

### 启动
```bash
./scripts/start.sh start     # API + 前端（vite 热重载）
./scripts/start.sh all       # 额外启动飞书 bot
./scripts/start.sh stop
```
端口：`.env` 的 `API_PORT`（默认 8000，当前 8010）/ `WEB_PORT`（默认 5173）。

### 必须配置的 .env 项
```dotenv
ARK_API_KEY=        # 火山方舟（默认 provider）
DEEPSEEK_API_KEY=   # DeepSeek 官方降级
LAYOUT_PARSING_URL= LAYOUT_PARSING_TOKEN=   # 文档解析（可留空走本地 pymupdf）
X_API_KEY=          # 前端访问后端的共享令牌
```
其余为可选项（飞书 bot、阈值 env 覆盖 `THRESH_*`）。

## 无 Docker 服务器部署（联网即可，无需 Dockerfile）

如果服务器能访问外网，可以直接装依赖跑，Docker 只是可选：

```bash
# 1. 依赖与配置
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 填 key

# 2. 构建前端
cd web && npm install && npm run build && cd ..

# 3. 启动 API（后台，日志落 var/log）
mkdir -p var/log
nohup .venv/bin/python -m backend.cli.api >> var/log/api.log 2>&1 &

# 4. 前端静态文件交给 nginx（或任意静态服务器）
#    将 web/dist 指到 nginx root，反向代理 / 到后端：
#    server {
#      listen 80;
#      root /srv/ae/web/dist;
#      location / { try_files $uri /index.html; }
#    }
#    前端构建时 VITE_API_BASE 指向 http://<服务器IP>:8000（默认即 localhost:8000，按需改）
```

## Docker 部署（可选）

Dockerfile 用于**环境隔离**（统一 Python/Node 版本、免装系统依赖）；服务器已联网且环境干净时，上节直接部署更简单。架构：`api` 容器跑 FastAPI（8000），`web` 容器用 nginx 服务前端静态文件（8080）；前端编译时 `VITE_API_BASE` 指向宿主 `http://localhost:8000`。

### 步骤
```bash
# 1. 准备 .env（cp .env.example .env 并填 key）
cp .env.example .env

# 2. 构建前端（dist 挂载进 web 容器）
cd web && npm run build && cd ..

# 3. 构建并启动
docker compose up -d --build

# 4. 访问
#    前端 http://localhost:8080
#    API  http://localhost:8000/health
```

### 数据与配置持久化
| 挂载 | 内容 |
|------|------|
| `./datasets` | 简历、`history.db`、`manifest.jsonl`、`labels.json`（个人数据不入镜像） |
| `./config` | `thresholds.yml` / `models.yml` / 运行时 `providers.local.yml`、`default_model.yml` |
| `./var` | 任务日志、pid |

### 运维
```bash
docker compose logs -f api
docker compose down        # 停止（保留数据卷）
docker compose down -v     # 停止并清数据卷（慎用）
docker compose pull && docker compose up -d --build   # 更新
```

### 说明
- 模型 API 均走 **OpenAI 兼容协议**：可在「模型面板 → API 端点」里添加 provider（base_url + api_key + 模型名），key 写入 `.env` 的 `<PROVIDER>_API_KEY`，配置落在 `config/providers.local.yml`（不入 git）。
- 判定阈值：`config/thresholds.yml` 或环境变量 `THRESH_GENERAL/THRESH_SPECIFIC/THRESH_TOTAL`。
- 默认模型：`config/models.yml` 的 `default`，或「模型面板」切换（写 `config/default_model.yml`）。
