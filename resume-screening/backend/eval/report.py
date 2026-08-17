"""自包含 HTML 评估报告（极客风暗色，无外部依赖）。"""
from __future__ import annotations

_CSS = """<style>
body{background:#0d1117;color:#c9d1d9;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;padding:24px;max-width:960px;margin:auto;line-height:1.5}
h1,h2,h3{color:#58a6ff}h1{border-bottom:1px solid #30363d;padding-bottom:8px}
table{border-collapse:collapse;width:100%;margin:12px 0}
th,td{border:1px solid #30363d;padding:6px 10px;text-align:left}th{background:#161b22;color:#8b949e}
.pass{color:#3fb950}.fail{color:#f85149}.muted{color:#8b949e}.best{background:#1f6feb22}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px}
.card .num{font-size:26px;font-weight:bold;color:#58a6ff}
.bar-wrap{background:#21262d;border-radius:3px;height:14px;width:100%;overflow:hidden}
.bar{background:#3fb950;height:14px}
.fail .bar{background:#f85149}
</style>"""


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _metric_card(label: str, value: str, cls: str = "") -> str:
    return f'<div class="card {cls}"><div class="muted">{label}</div><div class="num">{value}</div></div>'


def _confusion_table(c: dict) -> str:
    return f"""<table>
<tr><th></th><th>预测 pass</th><th>预测 fail</th></tr>
<tr><td>实际 pass</td><td class="pass">{c['tp']}</td><td class="fail">{c['fn']}</td></tr>
<tr><td>实际 fail</td><td class="fail">{c['fp']}</td><td class="pass">{c['tn']}</td></tr>
</table>"""


def _scan_table(rows: list, best_threshold) -> str:
    head = "<tr><th>总分阈值</th><th>pass 数</th><th>fail 数</th><th>准确率</th></tr>"
    body = []
    for r in rows:
        cls = " class='best'" if r["threshold"] == best_threshold else ""
        body.append(
            f"<tr{cls}><td>{r['threshold']}</td><td>{r['n_pass']}</td>"
            f"<td>{r['n_fail']}</td><td>{_pct(r['accuracy'])}</td></tr>"
        )
    return f"<table>{head}{''.join(body)}</table>"


def _discrimination_table(disc: list) -> str:
    head = "<tr><th>指标组</th><th>pass 平均加分</th><th>fail 平均加分</th><th>区分度</th></tr>"
    body = []
    for d in disc:
        gap = d["avg_pass"] - d["avg_fail"]
        bar_cls = "" if gap > 0 else " fail"
        width = max(0, min(100, abs(gap) * 20))
        body.append(
            f"<tr><td>{d['metric']}</td><td>{d['avg_pass']:.1f}</td><td>{d['avg_fail']:.1f}</td>"
            f"<td><div class='bar-wrap'><div class='bar{bar_cls}' style='width:{width}%'></div></div>"
            f"<span class='muted'>{gap:+.1f}</span></td></tr>"
        )
    return f"<table>{head}{''.join(body)}</table>"


def _records_table(records: list) -> str:
    head = "<tr><th>简历</th><th>岗位</th><th>人工标注</th><th>判定</th></tr>"
    body = []
    for r in records:
        label = r.get("label") or "-"
        cls = "pass" if r["predicted"] == label else "fail"
        body.append(
            f"<tr><td>{r['resume']}</td><td>{r.get('jd_ref') or '-'}</td><td>{label}</td>"
            f"<td class='{cls}'>{r['predicted']}</td></tr>"
        )
    return f"<table>{head}{''.join(body)}</table>"


def render_html(data: dict) -> str:
    m = data["metrics"]
    qa = data["quotation_accuracy"]
    best = data.get("best") or {}
    best_threshold = best.get("threshold")
    if m:
        cards = (
            _metric_card("准确率", _pct(m["accuracy"]))
            + _metric_card("精确率", _pct(m["precision"]))
            + _metric_card("召回率", _pct(m["recall"]))
            + _metric_card("F1", _pct(m["f1"]))
            + _metric_card("样本数", str(m["n"]))
            + _metric_card("引用准确率", _pct(qa["ratio"]), "fail" if qa["ratio"] < 0.8 else "")
        )
        metrics_html = "<h2>核心指标</h2><div class='grid'>" + cards + "</div>" \
            + "<h2>混淆矩阵</h2>" + _confusion_table(data["confusion"]) \
            + "<h2>阈值扫描（固定通用阈值）</h2>" + best_line(best) + _scan_table(data["threshold_scan"], best_threshold) \
            + "<h2>单指标区分度</h2>" + _discrimination_table(data["discrimination"])
    else:
        metrics_html = (
            f"<p class='muted'>暂无人工标注（未标注 {data.get('unlabeled', data.get('n', 0))} 条），"
            "请在评测页标注后重跑。</p>"
        )
    return (
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
        f"<title>筛简历评估报告</title>{_CSS}</head><body>"
        "<h1>筛简历评估报告</h1>"
        + metrics_html
        + "<h2>逐条记录</h2>" + _records_table(data["records"])
        + "<p class='muted'>本报告由 `python -m backend.eval.run_eval` 生成。</p>"
        "</body></html>"
    )


def best_line(best: dict) -> str:
    best_threshold = best.get("threshold")
    if best_threshold is None:
        return ""
    return (
        f"<p>最优总分阈值：<span class='pass'>{best_threshold}</span> "
        f"（准确率 {_pct(best.get('accuracy', 0))}）</p>"
    )
