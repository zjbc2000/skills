import { useEffect, useState } from 'react'
import { getHistory, getHistorySession } from '../api.js'
import DetailTable from './DetailTable.jsx'

export default function HistoryView() {
  const [sessions, setSessions] = useState(null)
  const [selected, setSelected] = useState(null) // {id, detail}
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    setError('')
    try {
      const { sessions } = await getHistory()
      setSessions(sessions)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function onOpen(id) {
    setError('')
    setBusy(true)
    try {
      const detail = await getHistorySession(id)
      setSelected(detail)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h1>历史记录</h1>
      <p className="eyebrow">// 每次筛选会话，点击查看当时的打分明细</p>

      {error && <p className="error" role="alert">{error}</p>}

      <section className="card">
        <div className="row-between">
          <h2>会话</h2>
          <button onClick={refresh} disabled={busy}>刷新</button>
        </div>
        {!sessions?.length && <p className="muted">暂无筛选历史，先去筛简历。</p>}
        {!!sessions?.length && (
          <table className="table">
            <thead>
              <tr>
                <th className="th-num">#</th>
                <th>时间</th>
                <th>岗位</th>
                <th>模式</th>
                <th className="th-num">成功/失败</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id} className={selected?.id === s.id ? 'hl' : ''}>
                  <td className="th-num">{s.id}</td>
                  <td className="cell-name" title={s.created_at}>{fmtTime(s.created_at)}</td>
                  <td>{s.jd}</td>
                  <td>{s.mode}</td>
                  <td className="th-num">
                    <span className="ok-text">{s.n_ok}</span> / <span className="bad-text">{s.n_fail}</span>
                  </td>
                  <td className="cell-actions">
                    <button className="mini" onClick={() => onOpen(s.id)} disabled={busy}>
                      查看
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {selected && (
        <section className="card">
          <div className="row-between">
            <h2>会话 #{selected.id} · {selected.jd} · {selected.mode}</h2>
            <span className="muted">{fmtTime(selected.created_at)}</span>
          </div>
          {selected.records.map((r, i) => (
            <RecordBlock key={i} record={r} />
          ))}
        </section>
      )}
    </>
  )
}

function RecordBlock({ record }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="history-record">
      <div className="row-between">
        <span className="batch-name">{record.name}</span>
        {record.verdict ? (
          <span className={`tag ${record.verdict === 'pass' ? 'tag-pass' : 'tag-fail'}`}>
            {record.verdict.toUpperCase()} · G{record.g} S{record.s} T{record.t}
          </span>
        ) : (
          <span className="tag tag-fail">失败</span>
        )}
      </div>
      {record.error && <div className="error">{record.error}</div>}
      {record.snapshot && (
        <button className="link" onClick={() => setOpen(!open)}>
          {open ? '收起明细' : '查看详情'}
        </button>
      )}
      {open && <DetailTable snapshot={record.snapshot} />}
    </div>
  )
}

function fmtTime(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
