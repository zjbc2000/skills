"""评估指标库（纯 stdlib）：混淆矩阵 + P/R/F1 + Wilson/Clopper-Pearson 置信区间 + QWK + Cohen's kappa + bootstrap。

所有函数都是纯函数，输入输出可复现；QWK/CI 数学见 references/metrics-taxonomy.md。
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

# ---------- 置信区间 ----------


def wilson_ci(n: int, k: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval（比例类指标默认）。

    Brown, Cai & DasGupta (2001)；Wald 区间在小样本/p→0/1 失效，Wilson 恒在 [0,1]。
    """
    if n <= 0:
        return (0.0, 0.0)
    if k < 0 or k > n:
        raise ValueError(f"k 越界: {k}")
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _betacf(a: float, b: float, x: float, maxit: int = 200, eps: float = 3e-12) -> float:
    """正则化不完全 beta 的连分数（Numerical Recipes betacf）。"""
    fpm = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpm:
        d = fpm
    d = 1.0 / d
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpm:
            d = fpm
        c = 1.0 + aa / c
        if abs(c) < fpm:
            c = fpm
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpm:
            d = fpm
        c = 1.0 + aa / c
        if abs(c) < fpm:
            c = fpm
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """正则化不完全 beta 函数 I_x(a, b)。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(a * math.log(x) + b * math.log1p(-x) + lbeta)
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _inv_beta(a: float, b: float, p: float, tol: float = 1e-9) -> float:
    """不完全 beta 的反函数（二分）。"""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _betai(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def clopper_pearson(n: int, k: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Clopper-Pearson 精确二项区间（n<5 或需保守保证时用）。"""
    if n <= 0:
        return (0.0, 0.0)
    if k < 0 or k > n:
        raise ValueError(f"k 越界: {k}")
    lo = 0.0 if k == 0 else _inv_beta(k, n - k + 1, alpha / 2)
    hi = 1.0 if k == n else _inv_beta(k + 1, n - k, 1 - alpha / 2)
    return (lo, hi)


def bootstrap_ci(
    values: Sequence[float],
    stat: Callable[[List[float]], float],
    n_boot: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Tuple[float, float]:
    """percentile bootstrap 置信区间（QWK/F1/MAE 等非正态指标）。"""
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boots.append(stat(sample))
    boots.sort()
    lo = boots[int((alpha / 2) * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot) - 1]
    return (lo, hi)


# ---------- 一致性 ----------


def cohen_kappa(r1: Sequence, r2: Sequence) -> float:
    """Cohen's kappa（二元/名义，扣掉 chance agreement）。"""
    if len(r1) != len(r2) or len(r1) == 0:
        raise ValueError("两序列长度不等且非空")
    n = len(r1)
    classes = sorted(set(r1) | set(r2))
    idx = {c: i for i, c in enumerate(classes)}
    k = len(classes)
    obs = [[0] * k for _ in range(k)]
    for a, b in zip(r1, r2):
        obs[idx[a]][idx[b]] += 1
    po = sum(obs[i][i] for i in range(k)) / n
    pe = sum(sum(obs[i]) * sum(obs[r][i] for r in range(k)) for i in range(k)) / (n * n)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def qwk(r1: Sequence[int], r2: Sequence[int], n_classes: int | None = None) -> float:
    """Quadratic Weighted Kappa（序数一致性；AES 标准度量）。

    权重 w=(i-j)²/(N-1)²。局限见 references/metrics-taxonomy.md（EDM 2023）：
    量纲敏感 / kappa paradox / 受 prevalence 影响——必须与其他指标一起报。
    """
    if len(r1) != len(r2) or len(r1) == 0:
        raise ValueError("两序列长度不等且非空")
    if n_classes is None:
        n_classes = max(max(r1), max(r2)) + 1
    if n_classes <= 1:
        return 0.0
    if len(r1) != len(r2):
        raise ValueError("两序列长度不等")
    n = len(r1)
    obs = [[0] * n_classes for _ in range(n_classes)]
    for a, b in zip(r1, r2):
        obs[a][b] += 1
    weights = [[(i - j) ** 2 / (n_classes - 1) ** 2 for j in range(n_classes)] for i in range(n_classes)]
    num = den = 0.0
    row = [sum(obs[i]) for i in range(n_classes)]
    col = [sum(obs[r][i] for r in range(n_classes)) for i in range(n_classes)]
    for i in range(n_classes):
        for j in range(n_classes):
            expected = row[i] * col[j] / n
            num += weights[i][j] * obs[i][j]
            den += weights[i][j] * expected
    if den == 0:
        return 0.0
    return 1.0 - num / den


# ---------- 正确性 ----------


def confusion_matrix(actual: Iterable[bool], predicted: Iterable[bool]) -> Dict[str, int]:
    tp = fp = tn = fn = 0
    for a, p in zip(actual, predicted):
        if a and p:
            tp += 1
        elif (not a) and p:
            fp += 1
        elif (not a) and (not p):
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def accuracy(c: Dict[str, int]) -> float:
    d = c["tp"] + c["fp"] + c["tn"] + c["fn"]
    return (c["tp"] + c["tn"]) / d if d else 0.0


def precision(c: Dict[str, int]) -> float:
    d = c["tp"] + c["fp"]
    return c["tp"] / d if d else 0.0


def recall(c: Dict[str, int]) -> float:
    d = c["tp"] + c["fn"]
    return c["tp"] / d if d else 0.0


def f1(c: Dict[str, int]) -> float:
    p, r = precision(c), recall(c)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def discrimination(pass_values: Sequence[float], fail_values: Sequence[float]) -> Dict:
    """逐指标区分度：pass/fail 两个桶的均值差（发现哪个指标没干活）。"""
    mean = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    return {
        "mean_pass": mean(pass_values),
        "mean_fail": mean(fail_values),
        "n_pass": len(pass_values),
        "n_fail": len(fail_values),
    }
