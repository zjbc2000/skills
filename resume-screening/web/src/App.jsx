import { useEffect, useState } from 'react'
import { API_BASE, API_KEY, getEval, getRoles, screenResume } from './api.js'

const MODES = [
  { value: 'general_specific', label: '通用+特定（双闸门）' },
  { value: 'general', label: '通用' },
  { value: 'specific', label: '特定' },
]

export default function App() {
  const [roles, setRoles] = useState([])
  const [jd, setJd] = useState('')
  const [mode, setMode] = useState('general_specific')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [evalData, setEvalData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getRoles()
      .then(({ roles }) => {
        setRoles(roles)
        setJd(roles[0] || '')
      })
      .catch((e) => setError(`加载岗位失败: ${e.message}`))
  }, [])

  async function onScreen(e) {
    e.preventDefault()
    if (!file) {
      setError('请选择简历文件')
      return
    }
    setError('')
    setBusy(true)
    setResult(null)
    try {
      setResult(await screenResume(file, { jd, mode }))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function onEval() {
    setError('')
    setBusy(true)
    try {
      setEvalData(await getEval())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>AE 工作台</h1>
        <span className="muted">
          API {API_BASE}
          {API_KEY ? '' : ' · 未配置 X-API-Key'}
        </span>
      </header>

      <section>
        <h2>筛简历</h2>
        <form onSubmit={onScreen}>
          <label>
            岗位
            <select value={jd} onChange={(e) => setJd(e.target.value)}>
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label>
            模式
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              {MODES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            简历
            <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
          </label>
          <button disabled={busy}>{busy ? '筛选中…' : '筛选'}</button>
        </form>
        {error && <p className="error">{error}</p>}
        {result && <ResultView result={result} />}
      </section>

      <section>
        <h2>评估</h2>
        <button onClick={onEval} disabled={busy}>
          跑评估
        </button>
        {evalData && <EvalView data={evalData} />}
      </section>

      <section>
        <h2>岗位映射（jd_map）</h2>
        <ul>
          {roles.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function ResultView({ result }) {
  const cls = result.verdict === 'pass' ? 'pass' : 'fail'
  return (
    <div className="card">
      <div className="verdict">
        <span className={cls}>{result.verdict.toUpperCase()}</span>
      </div>
      <div>
        G={result.totals.G} · S={result.totals.S} · T={result.totals.T}
      </div>
      <div className="muted">
        阈值 G≥{result.thresholds.general} 且 T≥{result.thresholds.total} · 解析器 {result.doc_loader}
      </div>
      <details>
        <summary>打分明细</summary>
        <pre>{JSON.stringify(result.snapshot, null, 2)}</pre>
      </details>
    </div>
  )
}

function EvalView({ data }) {
  if (!data.n) return <p className="muted">暂无记录</p>
  const m = data.metrics
  return (
    <div className="card">
      <div>
        准确率 {pct(m.accuracy)} · 精确率 {pct(m.precision)} · 召回率 {pct(m.recall)} · F1 {pct(m.f1)}
      </div>
      <div className="muted">
        引用准确率 {pct(data.quotation_accuracy.ratio)} · 最优总分阈值 {data.best?.threshold}
      </div>
    </div>
  )
}

function pct(x) {
  return `${(x * 100).toFixed(1)}%`
}
