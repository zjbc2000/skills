import { useEffect, useState } from 'react'
import { getRoles, screenBatch, waitTask } from '../api.js'

const MODES = [
  { value: 'general', label: '通用' },
  { value: 'specific', label: '特定' },
]

export default function ScreenView({ onRolesLoaded }) {
  const [roles, setRoles] = useState([])
  const [jd, setJd] = useState('')
  const [mode, setMode] = useState('general')
  const [files, setFiles] = useState([])
  const [results, setResults] = useState(null)
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getRoles()
      .then(({ roles }) => {
        setRoles(roles)
        setJd(roles[0] || '')
        if (onRolesLoaded) onRolesLoaded(roles)
      })
      .catch((e) => setError(`加载岗位失败：${e.message}`))
  }, [onRolesLoaded])

  async function onScreen(e) {
    e.preventDefault()
    if (!files.length) {
      setError('请选择简历文件（PDF / docx / zip）')
      return
    }
    setError('')
    setBusy(true)
    setResults(null)
    setLogs([])
    try {
      const { task_id } = await screenBatch(files, { jd, mode })
      const result = await waitTask(task_id, {
        onLog: (lines) => setLogs(lines),
      })
      setResults(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h1>筛简历</h1>
      <p className="eyebrow">// 批量筛选：多选 PDF/docx，或上传 zip 压缩包</p>

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
              <span>简历（可多选 pdf / docx，或上传 zip 包）</span>
              <div className="file-picker">
                <label htmlFor="resume-files" className="btn-secondary">选择文件…</label>
                <input
                  id="resume-files"
                  type="file"
                  accept=".pdf,.docx,.zip"
                  multiple
                  onChange={(e) => setFiles(Array.from(e.target.files || []))}
                />
                {files.length > 0 ? (
                  <span className="file-count">{files.length} 个文件</span>
                ) : (
                  <span className="muted">未选择</span>
                )}
              </div>
            </label>
          </div>
          <button className="primary" disabled={busy}>
            {busy ? `筛选中…（${files.length} 份）` : `开始筛选（${files.length} 份）`}
          </button>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
        {(busy || logs.length > 0) && (
          <div className="task-log">
            <div className="muted">{busy ? '任务进行中…' : '完成'}</div>
            <pre className="log-box">
              {logs.map((line, i) => (
                <div key={i} className="log-line">{line}</div>
              ))}
            </pre>
          </div>
        )}
        {results && (
          <div className="batch">
            <div className="muted">
              成功 {results.n_ok} · 失败 {results.n_fail}
            </div>
            {results.results.map((r, i) => (
              <ResultRow key={`${r.name}-${i}`} result={r} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function ResultRow({ result }) {
  const [open, setOpen] = useState(false)
  const hasVerdict = Boolean(result.verdict)
  return (
    <div className={`batch-row ${hasVerdict ? (result.verdict === 'pass' ? 'ok' : 'bad') : 'bad'}`}>
      <div className="row-between">
        <span className="batch-name">{result.name}</span>
        {hasVerdict ? (
          <span className={`tag ${result.verdict === 'pass' ? 'tag-pass' : 'tag-fail'}`}>
            {result.verdict.toUpperCase()} · G{result.totals.G} S{result.totals.S} T{result.totals.T}
          </span>
        ) : (
          <span className="tag tag-fail">失败</span>
        )}
      </div>
      {hasVerdict ? (
        <>
          <div className="muted">解析器 {result.doc_loader} · 阈值 G≥{result.thresholds.general} 且 T≥{result.thresholds.total}</div>
          <button className="link" onClick={() => setOpen(!open)}>{open ? '收起明细' : '打分明细'}</button>
          {open && <pre className="detail-pre">{JSON.stringify(result.snapshot, null, 2)}</pre>}
        </>
      ) : (
        <div className="error">{result.error}</div>
      )}
    </div>
  )
}
