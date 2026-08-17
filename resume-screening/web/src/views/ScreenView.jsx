import { useEffect, useState } from 'react'
import Dropdown from '../components/Dropdown.jsx'
import { getRoles, getThresholds, screenBatch, waitTask } from '../api.js'
import DetailTable from './DetailTable.jsx'

const MODES = [
  { value: 'general', label: '通用' },
  { value: 'specific', label: '特定' },
]

export default function ScreenView({ onRolesLoaded }) {
  const [roles, setRoles] = useState([])
  const [jd, setJd] = useState('')
  const [mode, setMode] = useState('general')
  const [files, setFiles] = useState([])
  const [thresholds, setThresholds] = useState(null)
  const [results, setResults] = useState(null)
  const [logs, setLogs] = useState([])
  const [selected, setSelected] = useState(null) // 排行中选中的记录
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
    getThresholds()
      .then(({ thresholds }) => setThresholds(thresholds))
      .catch(() => {})
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
    setSelected(null)
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

  function removeFile(i) {
    setFiles((fs) => fs.filter((_, j) => j !== i))
  }

  // 评分排行：只列有判定的，按 T 降序
  const ranking = (results?.results || [])
    .filter((r) => r.verdict)
    .sort((a, b) => b.totals.T - a.totals.T)

  return (
    <>
      <h1>简历筛选</h1>
      <p className="eyebrow">// 批量筛选：多选 PDF/docx，或上传 zip 压缩包</p>

      <div className="screen-layout">
        <div className="screen-main">
          <section className="card">
            <form onSubmit={onScreen}>
              <div className="field-grid two-up">
                <label className="field">
                  <span>岗位</span>
                  <Dropdown value={jd} options={roles} onChange={setJd} />
                </label>
                <label className="field">
                  <span>模式</span>
                  <Dropdown value={mode} options={MODES} onChange={setMode} />
                </label>
              </div>
              <label className="field file-field">
                <span>简历（可多选 pdf / docx，或上传 zip 包）</span>
                <div className="file-drop">
                  <label htmlFor="resume-files" className="file-drop-label">
                    点击选择文件…
                  </label>
                  <input
                    id="resume-files"
                    type="file"
                    accept=".pdf,.docx,.zip"
                    multiple
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
                  />
                  {files.length > 0 && (
                    <ul className="file-list">
                      {Array.from(files).map((f, i) => (
                        <li key={`${f.name}-${i}`}>
                          <span className="file-name" title={f.name}>{f.name}</span>
                          <button
                            type="button"
                            className="file-remove"
                            onClick={() => removeFile(i)}
                            aria-label={`移除 ${f.name}`}
                          >
                            ×
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </label>
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
          </section>

          {results && (
            <section className="card">
              <div className="row-between">
                <h2>评分排行</h2>
                <span className="muted">成功 {results.n_ok} · 失败 {results.n_fail}</span>
              </div>
              {ranking.length === 0 && <p className="muted">无评分结果</p>}
              <table className="table ranking">
                <thead>
                  <tr>
                    <th className="th-num">#</th>
                    <th>简历</th>
                    <th className="th-num">G</th>
                    <th className="th-num">S</th>
                    <th className="th-num">T</th>
                    <th>判定</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((r, i) => (
                    <tr key={`${r.name}-${i}`} className={selected === r ? 'hl' : ''}>
                      <td className="th-num">{i + 1}</td>
                      <td className="cell-name" title={r.name}>{r.name}</td>
                      <td className="th-num">{r.totals.G}</td>
                      <td className="th-num">{r.totals.S}</td>
                      <td className="th-num rank-t">{r.totals.T}</td>
                      <td className={r.verdict === 'pass' ? 'ok-text' : 'bad-text'}>{r.verdict}</td>
                      <td className="cell-actions">
                        <button className="mini" onClick={() => setSelected(selected === r ? null : r)}>
                          {selected === r ? '收起' : '查看详情'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {results.results
                .filter((r) => !r.verdict)
                .map((r, i) => (
                  <div key={`err-${i}`} className="batch-row bad">
                    <span className="batch-name">{r.name}</span>
                    <span className="error">{r.error}</span>
                  </div>
                ))}
              {selected && (
                <div className="detail-wrap">
                  <div className="row-between">
                    <span className="batch-name">{selected.name}</span>
                    <span className={`tag ${selected.verdict === 'pass' ? 'tag-pass' : 'tag-fail'}`}>
                      {selected.verdict.toUpperCase()} · T{selected.totals.T}
                    </span>
                  </div>
                  <DetailTable snapshot={selected.snapshot} />
                </div>
              )}
            </section>
          )}
        </div>

        <aside className="screen-side">
          <section className="card mode-guide">
            <h2>模式说明</h2>
            <div className="mode-item">
              <div className="mode-title"><span className="mode-tag">通用</span>综合素质</div>
              <p>
                按项目经历、技术栈、亮点加分得 <b>G</b>。需 <b>G≥{thresholds?.general ?? '–'}</b> 且总分{' '}
                <b>T≥{thresholds?.total ?? '–'}</b> 才通过——两头都要达标。
              </p>
            </div>
            <div className="mode-item">
              <div className="mode-title"><span className="mode-tag">特定</span>岗位匹配</div>
              <p>
                按岗位匹配度 + 命中技能加分得 <b>S</b>。需 <b>S≥{thresholds?.specific ?? '–'}</b> 才通过——
                只看匹配度，不看综合。
              </p>
            </div>
            <p className="muted">两种模式下红线均一票否决。</p>
          </section>
        </aside>
      </div>
    </>
  )
}
