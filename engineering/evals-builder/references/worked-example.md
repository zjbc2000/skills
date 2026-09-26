# worked-example: resume-screening 完整案例

> 把 resume-screening skill 的评估体系抽象成 8 个通用模块，作为本 skill 的完整落地案例。
> 完整源码在 ../resume-screening/；完整调研在 ../resume-screening/docs/research/resume-screening-eval-research.md。

## 8 个通用模块（从案例抽出的可复用件）

| # | 通用模块 | 案例化身 | 通用化表述 |
|---|---|---|---|
| 1 | **评分契约 + 快照** | `scoring/snapshot.py` | LLM judge 与确定性引擎之间**校验过的版本化输出契约**（条目 = 分数 + 证据 + 引用），快照是跨栈接口，改结构 = 跨栈改动 |
| 2 | **结构化输出守卫** | `scoring/schema.py` + `registry/llm_client.py` | 校验 LLM 输出 JSON；非法 → 带错误信息纠正性重试，仍失败进 failed 队列（不静默丢弃） |
| 3 | **证据落地校验** | `verify/quotation.py` | 后置确定性 grep：证据/引用是否真的在源文本里（exact/fuzzy/missing）；**不让 LLM 内联验证**（防"看不见的 padding"） |
| 4 | **确定性评分引擎** | `scoring/engine.py` | rubric 聚合：加权求和 + 双闸门 AND（G≥ 且 T≥）+ 红线一票否决 |
| 5 | **事实表 / 标注分离** | `persistence/manifest.py` + `persistence/labels.py` | append-only 预测日志（事实表）+ 独立存放的人工真值（按身份 key 关联）；**评估以快照为准，不重跑** |
| 6 | **阈值重算而非重筛** | `eval/run_eval.py` | 参数扫描是纯计算：predicted 从快照 totals 重算，改阈值/扫描不重跑昂贵的 LLM |
| 7 | **指标层（带 CI）** | `eval/metrics.py` | 混淆矩阵 + P/R/F1 + QWK + 引用准确率 + 阈值扫描 + 逐指标区分度 |
| 8 | **双输出报告** | `eval/report.py` | 自包含 HTML（用户侧）+ 结构化 JSON（数据侧） |

## 与 canonical eval-loop 的映射

| eval-loop | 案例中对应 |
|---|---|
| task | 一份简历 + 一个 JD（jd_map） |
| grader（code-based） | schema 校验 + quotation 后置 grep |
| grader（model-based） | rubric 打分 JSON 契约（G/S/T + bonus 0-3） |
| transcript | manifest.jsonl（append-only 事件流） |
| 聚合 | 双闸门 + 红线否决 |
| 报告/门禁 | HTML 报告 + 阈值扫描建议 |

## 案例关键决策（可直接抄）

1. **不信任 LLM**：quotation 必填 + 后置确定性校验，而非让 LLM 自证。
2. **评估快照分离**：评估以 score_snapshot 为准，不以当前 jd_map/manifest——回测的是"当时实际应用了什么"。
3. **阈值重算**：predicted 从 totals 重算，阈值扫描是纯计算，秒级。
4. **suspect 只标记不惩罚**：错误率先沉淀，惩罚规则延迟决策。
5. **接口即测试面**：snapshot 契约在产出口 `validate_snapshot` 校验。
6. **数据模型**：manifest（事实流）与 labels（真值）分离，record_key 身份稳定——改 manifest 行结构会静默破坏标注关联。

## 已知坑（来自调研，务必读）

- **LLM 打分方差**：HackerRank hiring-agent 同一份简历跑 100 次 66-99 波动；checklist 型（技能命中）稳定，主观型（经历质量）最不稳 → 硬数字 cutoff 危险，阈值扫描 + 区分度分析是防线。
- **judge 要校准**：绿门禁 ≠ 评估有效；judge 需周期性对人类校准（kappa drift 告警）。
- **小样本**：阈值调到 max-F1 再直接上线是常见错误（过拟合到 10-50 条噪声）。
