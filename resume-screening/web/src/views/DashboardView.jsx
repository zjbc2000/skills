import { useEffect, useState } from 'react'
import Dropdown from '../components/Dropdown.jsx'
import { clearUsage, getDashboard, getModels, setDefaultModel } from '../api.js'

export default function DashboardView() {
  const [data, setData] = useState(null)
  const [models, setModels] = useState(null)
  const [defaultSel, setDefaultSel] = useState(null) // "provider/model"
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    setError('')
    try {
      const [d, m] = await Promise.all([getDashboard(), getModels()])
      setData(d)
      setModels(m)
      setDefaultSel(`${m.default.provider}/${m.default.model}`)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function onApplyDefault(e) {
    e.preventDefault()
    const [provider, model] = defaultSel.split('/')
    setError('')
    setNotice('')
    setBusy(true)
    try {
      await setDefaultModel(provider, model)
      setNotice(`默认模型已切换为 ${provider}/${model}`)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function onClear() {
    setError('')
    try {
      await clearUsage()
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  const s = data?.summary
  const options = models
    ? Object.entries(models.providers).flatMap(([p, ms]) => ms.map((m) => `${p}/${m}`))
    : []

  return (
    <>
      <h1>模型面板</h1>
      <p className="eyebrow">// LLM 用量监控：token · 调用次数 · 成功率</p>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice">{notice}</p>}

      <section className="card">
        <div className="row-between">
          <h2>总览</h2>
          <button onClick={refresh} disabled={busy}>刷新</button>
        </div>
        {s && (
          <div className="metrics">
            <Metric label="调用次数" value={s.n} />
            <Metric label="成功率" value={pct(s.success_rate)} />
            <Metric label="输入 token" value={fmtTok(s.prompt_tokens)} />
            <Metric label="输出 token" value={fmtTok(s.completion_tokens)} />
            <Metric label="平均耗时" value={`${s.avg_duration_ms}ms`} />
          </div>
        )}
        {!s?.n && <p className="muted">暂无调用记录（用真实模型筛一份简历后可见）</p>}
      </section>

      <section className="card">
        <div className="row-between">
          <h2>默认模型</h2>
        </div>
        <form onSubmit={onApplyDefault} className="row-between model-switch">
          <Dropdown value={defaultSel || ''} options={options} onChange={setDefaultSel} />
          <button className="primary" disabled={busy || !defaultSel}>
            {busy ? '应用中…' : '切换默认模型'}
          </button>
        </form>
        <p className="muted">写 config/default_model.yml（运行时覆盖，models.yml 不变）</p>
      </section>

      <section className="card">
        <div className="row-between">
          <h2>按模型</h2>
          <button className="link" onClick={onClear}>清空用量</button>
        </div>
        {!!data?.by_model?.length && (
          <table className="table">
            <thead>
              <tr>
                <th>模型</th>
                <th className="th-num">次数</th>
                <th className="th-num">成功/失败</th>
                <th className="th-num">成功率</th>
                <th className="th-num">输入/输出 token</th>
                <th className="th-num">平均耗时</th>
              </tr>
            </thead>
            <tbody>
              {data.by_model.map((r) => (
                <tr key={`${r.provider}/${r.model}`}>
                  <td>{r.provider} / <b>{r.model}</b></td>
                  <td className="th-num">{r.n}</td>
                  <td className="th-num">
                    <span className="ok-text">{r.n_ok}</span> / <span className="bad-text">{r.n_fail}</span>
                  </td>
                  <td className="th-num">{pct(r.success_rate)}</td>
                  <td className="th-num">{fmtTok(r.prompt_tokens)} / {fmtTok(r.completion_tokens)}</td>
                  <td className="th-num">{r.avg_duration_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>最近调用</h2>
        {!!data?.recent?.length && (
          <table className="table">
            <thead>
              <tr>
                <th>时间</th>
                <th>模型</th>
                <th className="th-num">输入</th>
                <th className="th-num">输出</th>
                <th className="th-num">耗时</th>
                <th>结果</th>
              </tr>
            </thead>
            <tbody>
              {data.recent.map((r, i) => (
                <tr key={i}>
                  <td className="cell-name" title={r.ts}>{fmtTime(r.ts)}</td>
                  <td>{r.provider}/{r.model}</td>
                  <td className="th-num">{r.prompt_tokens}</td>
                  <td className="th-num">{r.completion_tokens}</td>
                  <td className="th-num">{r.duration_ms}ms</td>
                  <td className={r.ok ? 'ok-text' : 'bad-text'}>{r.ok ? 'ok' : 'fail'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!data?.recent?.length && <p className="muted">暂无调用</p>}
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

function fmtTok(n) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

function fmtTime(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (x) => String(x).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}
