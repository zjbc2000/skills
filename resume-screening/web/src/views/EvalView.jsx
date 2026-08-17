import { useEffect, useState } from 'react'
import { applyThreshold, getEval, setLabel } from '../api.js'

export default function EvalView() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    setError('')
    setBusy(true)
    try {
      setData(await getEval())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function onLabel(recordKey, label) {
    setError('')
    try {
      await setLabel(recordKey, label)
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  async function onApplyThreshold() {
    if (!data?.best) return
    setError('')
    try {
      const { thresholds } = await applyThreshold(data.best.threshold)
      setNotice(`已应用：G≥${thresholds.general} 且 T≥${thresholds.total}（specific≥${thresholds.specific}）`)
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <>
      <h1>评测</h1>
      <p className="eyebrow">// 人工标注 manifest 记录，迭代阈值与指标</p>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice">{notice}</p>}

      <section className="card">
        <div className="row-between">
          <h2>核心指标（已标注 {data?.labeled ?? 0} / {data?.n ?? 0} 条）</h2>
          <button onClick={refresh} disabled={busy}>
            {busy ? '计算中…' : '刷新'}
          </button>
        </div>
        {data && (
          <div className="eval-thresholds">
            当前生效阈值：
            <span className="tag tag-pass">G ≥ {data.thresholds?.general}</span>
            <span className="tag tag-pass">T ≥ {data.thresholds?.total}</span>
            <span className="tag tag-pass">S ≥ {data.thresholds?.specific}</span>
            <span className="muted">（可用环境变量 THRESH_GENERAL / THRESH_SPECIFIC / THRESH_TOTAL 覆盖）</span>
          </div>
        )}
        {data && data.labeled > 0 && data.best && (
          <>
            <div className="metrics">
              <Metric label="准确率" value={pct(data.metrics.accuracy)} />
              <Metric label="精确率" value={pct(data.metrics.precision)} />
              <Metric label="召回率" value={pct(data.metrics.recall)} />
              <Metric label="F1" value={pct(data.metrics.f1)} />
              <Metric label="引用准确率" value={pct(data.quotation_accuracy.ratio)} />
            </div>
            <div className="row-between">
              <div className="muted">
                最优 T 阈值 <b>{data.best.threshold}</b> · 准确率 {pct(data.best.accuracy)}
              </div>
              <button onClick={onApplyThreshold} disabled={busy}>
                应用建议阈值 T≥{data.best.threshold}
              </button>
            </div>
            <details className="detail">
              <summary>阈值扫描明细（扫描范围 {scanRange(data.threshold_scan)}，聚焦最优 ±15）</summary>
              <table className="table">
                <thead>
                  <tr><th>T 阈值</th><th>判 pass</th><th>判 fail</th><th>准确率</th></tr>
                </thead>
                <tbody>
                  {(focusRows(data.threshold_scan, data.best?.threshold)).map((row) => (
                    <tr key={row.threshold} className={row.threshold === data.best.threshold ? 'hl' : ''}>
                      <td>{row.threshold}</td>
                      <td>{row.n_pass}</td>
                      <td>{row.n_fail}</td>
                      <td>{pct(row.accuracy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </>
        )}
        {data && data.labeled > 0 && !data.best && (
          <p className="muted">已标注 {data.labeled} 条但未得出最优阈值（样本或标注过少）。</p>
        )}
        {data && data.labeled === 0 && (
          <p className="muted">
            暂无人工标注（{data.unlabeled} 条未标注）。在下方记录表标注 pass/fail 后即可计算指标与阈值建议。
          </p>
        )}
      </section>

      <section className="card">
        <h2>记录标注</h2>
        {!data?.records?.length && <p className="muted">manifest 暂无记录，先去筛简历。</p>}
        {!!data?.records?.length && (
          <table className="table">
            <thead>
              <tr><th>简历</th><th>岗位</th><th>判定</th><th>人工标注</th></tr>
            </thead>
            <tbody>
              {data.records.map((r) => (
                <tr key={r.record_key}>
                  <td className="cell-name" title={r.resume}>{r.resume}</td>
                  <td>{r.jd_ref}</td>
                  <td className={r.predicted === r.label ? 'ok-text' : 'bad-text'}>{r.predicted}</td>
                  <td className="cell-actions">
                    <button
                      className={`mini ${r.label === 'pass' ? 'primary' : ''}`}
                      onClick={() => onLabel(r.record_key, r.label === 'pass' ? null : 'pass')}
                    >
                      通过
                    </button>
                    <button
                      className={`mini ${r.label === 'fail' ? 'danger' : ''}`}
                      onClick={() => onLabel(r.record_key, r.label === 'fail' ? null : 'fail')}
                    >
                      不通过
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  )
}

function pct(x) {
  return `${((x || 0) * 100).toFixed(1)}%`
}

/** 扫描范围展示：lo~hi（如 15~81），由扫描表首尾行推导。 */
function scanRange(rows) {
  if (!rows?.length) return '–'
  return `${rows[0].threshold}~${rows[rows.length - 1].threshold}`
}

/** 聚焦最优阈值 ±15 的行，避免全量逐行刷屏。 */
function focusRows(rows, bestT) {
  if (!rows?.length || bestT === undefined) return rows || []
  return rows.filter((r) => Math.abs(r.threshold - bestT) <= 15)
}
