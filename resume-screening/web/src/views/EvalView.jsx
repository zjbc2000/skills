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
        {data && data.labeled > 0 && (
          <>
            <div className="metrics">
              <Metric label="准确率" value={pct(data.metrics.accuracy)} />
              <Metric label="精确率" value={pct(data.metrics.precision)} />
              <Metric label="召回率" value={pct(data.metrics.recall)} />
              <Metric label="F1" value={pct(data.metrics.f1)} />
              <Metric label="引用准确率" value={pct(data.quotation_accuracy.ratio)} />
            </div>
            <div className="row-between">
              <div className="muted">最优总分阈值 {data.best?.threshold}（准确率 {pct(data.best?.accuracy ?? 0)}）</div>
              <button onClick={onApplyThreshold} disabled={busy || !data.best}>
                应用建议阈值 T≥{data.best?.threshold}
              </button>
            </div>
            <details className="detail">
              <summary>阈值扫描明细</summary>
              <table className="table">
                <thead>
                  <tr><th>T 阈值</th><th>判 pass</th><th>判 fail</th><th>准确率</th></tr>
                </thead>
                <tbody>
                  {(data.threshold_scan || []).map((row) => (
                    <tr key={row.threshold} className={row.threshold === data.best?.threshold ? 'hl' : ''}>
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
