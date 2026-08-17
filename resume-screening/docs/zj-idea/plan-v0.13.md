# v0.13 计划：JD 管理 + 批量上传（zip/docx）+ 评测工作台

已确认的设计决策：
- JD 结构化：粘贴 JD 原文 -> LLM 抽取 position/skills/red_lines -> 可编辑预览 -> 写入 jd_map.yml
- 评测真值：评测页人工打标，存 `datasets/labels.json`（manifest 保持 append-only）
- 支持一键把扫描出的最优总分阈值回写 `config/thresholds.yml`

---

## Feature 1：JD 管理（新菜单页）

### 后端
- `backend/scoring/prompts.py` 新增 `JD_EXTRACT_SYSTEM_PROMPT` + `build_jd_extract_prompt(jd_raw)`：
  要求 LLM 只输出 `{"position": str, "skills": [str], "red_lines": [str]}`
- `backend/scoring/schema.py` 新增 `validate_jd_output(text) -> dict`（轻校验：JSON 可解析 + 字段类型）
- `backend/persistence/jd_map.py` 新增 `save_jd_map(path, roles)`（`yaml.safe_dump`，`allow_unicode=True`）
- `backend/api/main.py` 新增两个端点（均需 X-API-Key）：
  - `POST /jd/extract`：`{jd_raw, llm}` -> 结构化字段。复用 `LLMClient`（validator 换成 `validate_jd_output`）；`llm=fake` 返回固定结构（供测试）
  - `POST /jd/save`：`{key, position, skills[], red_lines[]}` -> 写入 jd_map.yml。key 已存在返回 409

### 前端（App.jsx）
- 导航加「JD 管理」（新图标）
- `JdView`：JD 原文 textarea -> 「抽取字段」-> 表单预览（岗位名 key / position / skills 多行 / red_lines 多行，均可编辑）-> 「保存」
- 保存成功后刷新 roles；切回筛简历页即可选到新岗位

## Feature 2：批量上传 + docx 支持

### 后端
- 新增 `backend/doc_loader/docx_local.py`：python-docx 抽取段落 + 表格文本，失败抛 `LoaderError`
- `doc_loader/base.py:get_loader` 注册 `local_docx`；`config/tools.yml` fallback 改为 `[local_pymupdf, local_docx, local_paddleocr]`
- `requirements.txt` 加 `python-docx>=1.1`
- `backend/api/main.py` 新增 `POST /screen/batch`：
  - `files: List[UploadFile]` + jd/mode/llm
  - `.zip` -> `zipfile` 解包到临时目录（过滤路径穿越 `..`/绝对路径，只收 `.pdf`/`.docx`），其余文件直接处理
  - 逐份串行调 `screen_file`，每份独立写 manifest；单份失败不中断批次
  - 返回 `results[]`：`{name, verdict?, totals?, error?}`

### 前端
- 文件输入改 `multiple` + `accept=".pdf,.docx,.zip"`
- 提交时所有文件放进一个 FormData 打 `/screen/batch`
- 结果区改为逐文件卡片（复用 ResultView 的分数渲染，失败文件显示错误）

## Feature 3：评测工作台（从筛简历页拆出为独立菜单页）

### 真值与数据
- `datasets/labels.json`：`{record_key: "pass"|"fail"}`；`record_key = sha1(resume|jd_ref|time)`
- `backend/eval/run_eval.py:build_records` 改造：
  - `actual` 来自 labels（未标注为 None）
  - `predicted` 改为按当前配置阈值从 totals **重算**（G≥general 且 T≥total）——调阈值后无需重新筛简历即可重新评测，这是「便于迭代」的核心
- 指标只在已标注子集上计算；`build_eval_data` 返回增加 `unlabeled` 数量

### 端点（api/main.py）
- `GET /eval`：响应增加 records 明细（record_key / resume / jd_ref / G/S/T / predicted / label）
- `POST /label`：`{record_key, label}` upsert labels.json
- `POST /eval/apply-threshold`：`{threshold}` -> 回写 thresholds.yml 的 total（其余不动）
- thresholds.yml 路径支持 `RESUME_CONFIG` 环境变量覆盖（缺省仓库 config/），测试用 tmp 目录，不碰真实配置

### 前端
- 「评测」独立菜单页：
  - 指标卡（准确率/精确率/召回率/F1/引用准确率，基于已标注子集）+ 未标注数量提示
  - 阈值扫描表（最优行高亮）+「应用建议阈值」按钮（成功后提示新阈值）
  - 记录表：resume / jd_ref / G/S/T / 引擎判定 / 人工标注按钮（通过/不通过/清除）

## 测试（沿用现有 tmp_path + monkeypatch 模式）
- `tests/test_docx_loader.py`：python-docx 现造一份 docx -> 抽取文本
- `tests/test_api.py` 扩展：/jd/extract(fake)、/jd/save 落盘 + 409、/screen/batch（zip 内 2 份 PDF）、/label、/eval 含标签指标、/eval/apply-threshold 写 tmp 配置
- 既有 106 个测试保持通过

## 收尾
- `npm run build` 重新构建前端
- HISTORY.md 记 v0.13，按既有惯例提交一个 commit
