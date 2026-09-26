"""metrics 数学单测：手算对拍（Wilson / Clopper-Pearson / QWK / Cohen's kappa / bootstrap）。

只测外部行为（纯函数返回值），不测内部实现。
"""
import pytest

from metrics import (
    accuracy,
    bootstrap_ci,
    clopper_pearson,
    cohen_kappa,
    confusion_matrix,
    discrimination,
    f1,
    precision,
    qwk,
    recall,
    wilson_ci,
)


class TestConfidenceIntervals:
    def test_wilson_ci_known_value(self):
        # n=50, p̂=0.8 → 95% CI ≈ (0.6696, 0.8876)（Brown-Cai-DasGupta 手算）
        lo, hi = wilson_ci(50, 40)
        assert lo == pytest.approx(0.6696, abs=5e-3)
        assert hi == pytest.approx(0.8876, abs=5e-3)

    def test_wilson_ci_inside_unit_interval(self):
        for n, k in [(10, 0), (10, 10), (3, 1), (5, 5)]:
            lo, hi = wilson_ci(n, k)
            assert 0.0 <= lo <= hi <= 1.0

    def test_wilson_ci_invalid_k(self):
        with pytest.raises(ValueError):
            wilson_ci(10, 11)

    def test_clopper_pearson_edge_k0(self):
        # k=0,n=10：lo=0, hi=1-(0.025)^0.1 ≈ 0.3084
        lo, hi = clopper_pearson(10, 0)
        assert lo == pytest.approx(0.0, abs=1e-6)
        assert hi == pytest.approx(0.3084, abs=1e-3)

    def test_clopper_pearson_edge_kn(self):
        # k=n=10：lo=(0.025)^0.1 ≈ 0.6916, hi=1
        lo, hi = clopper_pearson(10, 10)
        assert lo == pytest.approx(0.6916, abs=1e-3)
        assert hi == pytest.approx(1.0, abs=1e-6)

    def test_bootstrap_ci_contains_statistic_and_is_deterministic(self):
        values = list(range(1, 11))
        mean = sum(values) / len(values)
        lo, hi = bootstrap_ci(values, lambda s: sum(s) / len(s), seed=42)
        assert lo <= mean <= hi
        assert lo >= min(values) and hi <= max(values)
        assert bootstrap_ci(values, lambda s: sum(s) / len(s), seed=42) == (lo, hi)


class TestAgreement:
    def test_cohen_kappa_perfect(self):
        assert cohen_kappa([0, 0, 0], [0, 0, 0]) == pytest.approx(1.0)

    def test_cohen_kappa_known_value(self):
        # po=0.8（2 处不一致）, pe=0.34 → kappa=0.46/0.66≈0.6970
        r1 = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2]
        r2 = [0, 0, 0, 1, 1, 1, 1, 2, 2, 2]
        assert cohen_kappa(r1, r2) == pytest.approx(0.6970, abs=1e-3)

    def test_cohen_kappa_raises_on_mismatched_length(self):
        with pytest.raises(ValueError):
            cohen_kappa([0], [0, 1])

    def test_qwk_perfect(self):
        r1 = [0, 1, 2, 0, 1]
        assert qwk(r1, r1) == pytest.approx(1.0)

    def test_qwk_two_class_random(self):
        # 2 类时二次权重退化为线性：随机配对 → kappa=0
        assert qwk([0, 0, 1, 1], [0, 1, 0, 1], n_classes=2) == pytest.approx(0.0, abs=1e-9)

    def test_qwk_degenerate_all_same_does_not_crash(self):
        assert qwk([0, 0, 0, 0], [0, 0, 0, 0], n_classes=2) >= 0.0


class TestCorrectness:
    def test_confusion_and_derived_metrics(self):
        actual = [True, True, True, False, False]
        predicted = [True, True, False, False, False]
        c = confusion_matrix(actual, predicted)
        assert c == {"tp": 2, "fp": 0, "tn": 2, "fn": 1}
        assert accuracy(c) == pytest.approx(0.8)
        assert precision(c) == pytest.approx(1.0)
        assert recall(c) == pytest.approx(2 / 3)
        assert f1(c) == pytest.approx(0.8)

    def test_discrimination_means(self):
        d = discrimination([3, 2, 1], [0, 0])
        assert d["mean_pass"] == pytest.approx(2.0)
        assert d["mean_fail"] == pytest.approx(0.0)
        assert d["n_pass"] == 3 and d["n_fail"] == 2
