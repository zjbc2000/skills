import { useEffect, useState } from 'react'
import { getEval, getRoles, screenResume } from './api.js'

const MODES = [
  { value: 'general_specific', label: '通用+特定（双闸门）' },
  { value: 'general', label: '通用' },
  { value: 'specific', label: '特定' },
]

const NAV = [{ key: 'screen', label: '筛简历', icon: <ClipboardIcon /> }]

export default function App() {
  const [view, setView] = useState('screen')
  return (
    <div className="shell">
      <Sidebar active={view} onSelect={setView} />
      <main className="content">{view === 'screen' && <ScreenView />}</main>
    </div>
  )
}

function Sidebar({ active, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <LogoMark />
        <span>AE 工作台</span>
      </div>
      <nav className="nav" aria-label="主导航">
        {NAV.map((item) => (
          <button
            key={item.key}
            className={`nav-item${active === item.key ? ' active' : ''}`}
            onClick={() => onSelect(item.key)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="account">
        <div className="avatar" aria-hidden="true">Z</div>
        <div className="account-meta">
          <div className="account-name">zed</div>
          <div className="account-role">筛简历管理员</div>
        </div>
      </div>
    </aside>
  )
}

function ScreenView() {
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
      .catch((e) => setError(`加载岗位失败：${e.message}`))
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
    <>
      <h1>筛简历</h1>

      <section className="card">
        <form onSubmit={onScreen}>
          <div className="field-grid">
            <label className="field">
              <span>岗位</span>
              <select value={jd} onChange={(e) => setJd(e.target.value)}>
                {roles.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>模式</span>
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>简历</span>
              <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
            </label>
          </div>
          <button className="primary" disabled={busy}>
            {busy ? '筛选中…' : '开始筛选'}
          </button>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
        {result && <ResultView result={result} />}
      </section>

      <section className="card">
        <div className="row-between">
          <h2>评估</h2>
          <button onClick={onEval} disabled={busy}>
            {busy ? '计算中…' : '跑评估'}
          </button>
        </div>
        {evalData && <EvalView data={evalData} />}
        {!evalData && !error && <p className="muted">跑评估查看 skill 的准确率 / 引用准确率 / 阈值建议</p>}
      </section>
    </>
  )
}

function ResultView({ result }) {
  const pass = result.verdict === 'pass'
  return (
    <div className="result">
      <div className={`verdict ${pass ? 'pass' : 'fail'}`}>
        <span className="dot" aria-hidden="true" />
        {result.verdict.toUpperCase()}
      </div>
      <div className="scores">
        <Score label="G" value={result.totals.G} />
        <Score label="S" value={result.totals.S} />
        <Score label="T" value={result.totals.T} />
      </div>
      <div className="muted">
        阈值 G≥{result.thresholds.general} 且 T≥{result.thresholds.total} · 解析器 {result.doc_loader}
      </div>
      <details className="detail">
        <summary>打分明细</summary>
        <pre>{JSON.stringify(result.snapshot, null, 2)}</pre>
      </details>
    </div>
  )
}

function Score({ label, value }) {
  return (
    <div className="score">
      <span className="score-label">{label}</span>
      <span className="score-value">{value}</span>
    </div>
  )
}

function EvalView({ data }) {
  if (!data.n) return <p className="muted">暂无记录</p>
  const m = data.metrics
  return (
    <div className="eval">
      <div className="metrics">
        <Metric label="准确率" value={pct(m.accuracy)} />
        <Metric label="精确率" value={pct(m.precision)} />
        <Metric label="召回率" value={pct(m.recall)} />
        <Metric label="F1" value={pct(m.f1)} />
        <Metric label="引用准确率" value={pct(data.quotation_accuracy.ratio)} />
      </div>
      <div className="muted">最优总分阈值 {data.best?.threshold} · 样本 {data.n}</div>
    </div>
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
  return `${(x * 100).toFixed(1)}%`
}

function LogoMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="m9 14 2 2 4-4" />
    </svg>
  )
}

function ClipboardIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="m9 14 2 2 4-4" />
    </svg>
  )
}
