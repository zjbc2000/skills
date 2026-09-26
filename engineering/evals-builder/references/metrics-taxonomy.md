# metrics-taxonomy: 评估指标族全景 + 置信区间

> 来源逐条见内联引用；完整出处见 ../resume-screening/docs/research/eval-methodology-skill-research.md §3/§5。

## 指标族表（LLM 打分系统）

| 指标族 | 是否 table-stakes | 说明 |
|---|---|---|
| 混淆矩阵 + 精确率/召回率/F1（per-verdict） | ✅ 必须 | 类不平衡看 macro/micro |
| 序数一致性 QWK（per-score） | ✅ 必须 | 分数级而非仅 pass/fail；与标注分比 |
| 逐指标区分度（discrimination） | ✅ 必须 | 发现"哪个指标没干活" |
| 证据/引用准确率（faithfulness 的确定性版） | ✅ 必须 | 防幻觉，后置确定性校验 |
| 阈值扫描 + 置信区间 | ✅ 必须 | 小样本下阈值只是量级参考 |
| judge↔human 一致性（kappa/ICC） | ✅ 应补 | 校准 LLM judge；双标注时尤其 |
| bootstrap / Wilson 置信区间 | ✅ 应补 | 见下方公式 |
| Brier/ECE/MCE 校准 | ⭕ 可选 | 仅当把分数当"概率/置信度"用时 |
| ICC（多 rater） | ⭕ 可选 | 单人标注用不上 |

## 置信区间公式（小样本必配）

### Wilson score interval（比例类指标默认）
Wald 区间在小样本 / p→0/1 时失效（越界、覆盖不足）。Wilson 恒在 [0,1] 且覆盖好。
来源：Brown, Cai & DasGupta (2001)《Interval Estimation for a Binomial Proportion》(projecteuclid.org/10.1214/ss/1009213286)。
例：n=50、p̂=0.8 → 95% CI ≈ [0.67, 0.90]（±0.12）；n=10 时宽到几乎无信息。

### Clopper-Pearson 精确区间
n<5 或必须保守保证（合规/医疗）时用。实现见 scripts/metrics.py。

### bootstrap 置信区间（QWK / F1 / MAE 等非正态指标）
percentile bootstrap；偏斜/小样本用 BCa（bias-corrected and accelerated）。
来源：Indeed Engineering《Bootstrap Confidence Intervals for LLM Evaluation》(2026-07)。
量级感：**interval 宽度 ∝ 1/√N**——10-50 条样本的 CI 能撑"排序/量级"，撑不起"精确调参"。
⚠️ CI 只测抽样噪声，不测 label error / distribution shift / judge 偏差——"紧区间套在偏置指标上仍是错的"。

## 一致性 / 序数度量

### QWK（quadratic weighted kappa）
序数打分的标准"机器分 vs 人类分"对齐指标（AES 领域标配）。
- 权重 w=(i-j)²/(N-1)²，N×N 列联表，期望一致率按边际独立计算。
- 实现见 scripts/metrics.py；测试与手算对拍。

**QWK 已知局限（一手：Doewes et al., EDM 2023《Evaluating QWK as the Standard Performance Metric for AES》）**：
- 对评分量纲敏感（档位越多 QWK 越高）
- **kappa paradox**：一致率高但 kappa 低
- 受 prevalence（类别先验分布）影响；对角线位置影响；不适用大量 rater
- 结论：**QWK 与其他指标一起报，不要单独用**。

### Cohen's kappa
二元/名义一致性，扣掉 chance agreement；配对两 rater。
来源：Cohen (1960)。判读参考：0.55 是 judge 校准告警线（dev.to 2026 复盘，见 eval-methodology 调研 §2.4）。

### ICC
适合 2+ rater、连续/序数量表；多 LLM judge vs 人类常用 ICC(2,1)/(3,1)。单人标注用不上。

## 显著性检验（改进了还是没改进）

来源：Dror et al., ACL 2018《The Hitchhiker's Guide to Testing Statistical Significance in NLP》(aclanthology.org/P18-1128)；Card et al., EMNLP 2020 提醒小样本下先报 effect size。

| 场景 | 检验 |
|---|---|
| 二元结果 | McNemar（n<10 用精确版） |
| 连续、正态、n>30 | paired t |
| 序数 / 非正态 | Wilcoxon signed-rank |
| 复杂/自定义 | bootstrap permutation |

## 校准（可选增强）

只当"分数被当概率/置信度"用时才需要。Brier score（越低越好，0.25-0.57 即比随机差）、ECE（<0.1）、MCE（<0.25）、AUROC（>0.85）。校准方法：Platt scaling（需数百条标注）、isotonic regression。实现需专门作业，小样本阶段不做。

## 小样本纪律速查

- 10-50 条就够起步（Anthropic 官方），**质量 > 数量**，来自真实失败。
- n<30：逐条 case review 比汇总数字可信（读 transcript/预测/证据）。
- 阈值扫描：建议区间 + 样本级列举，不输出单点精确值。
- 回归 eval 应有 ~100% pass 率才护得住不倒退；capability eval 才允许低 pass 起步。
