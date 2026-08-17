import { useEffect, useState } from 'react'
import { listJds, saveJd, updateJd } from '../api.js'
import JdModal from './JdModal.jsx'

export default function JdView({ onSaved }) {
  const [jds, setJds] = useState(null)
  const [modal, setModal] = useState(null) // null | {mode:'new'} | {mode:'edit', jd}
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    setError('')
    try {
      const { jds } = await listJds()
      setJds(jds)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function onSave(payload) {
    setError('')
    setBusy(true)
    try {
      const { roles } = payload.old_key ? await updateJd(payload) : await saveJd(payload)
      setNotice(`已保存「${payload.key}」，当前岗位：${roles.join('、')}`)
      setModal(null)
      await refresh()
      if (onSaved) onSaved(roles)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>JD 管理</h1>
          <p className="eyebrow">// 已有 JD 卡片可直接编辑，或新建注册新岗位</p>
        </div>
        <button className="primary" onClick={() => setModal({ mode: 'new' })}>
          + 新建 JD
        </button>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice">{notice}</p>}

      {!jds?.length && !error && <p className="muted">暂无 JD，点击右上角「新建 JD」。</p>}

      <div className="jd-grid">
        {jds?.map((jd) => (
          <article key={jd.key} className="jd-card">
            <div className="row-between jd-card-head">
              <span className="jd-key">{jd.key}</span>
              <button className="mini" onClick={() => setModal({ mode: 'edit', jd })}>
                编辑
              </button>
            </div>
            {jd.position && <div className="jd-position">{jd.position}</div>}
            <ul className="jd-skills">
              {(jd.skills || []).slice(0, 4).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
              {(jd.skills || []).length > 4 && (
                <li className="muted">… 共 {(jd.skills || []).length} 条</li>
              )}
            </ul>
            {jd.red_lines?.length > 0 && (
              <div className="jd-red">
                <span className="eyebrow">红线 {jd.red_lines.length}</span>
              </div>
            )}
          </article>
        ))}
      </div>

      {modal && (
        <JdModal
          jd={modal.mode === 'edit' ? modal.jd : null}
          busy={busy}
          onClose={() => setModal(null)}
          onSave={onSave}
        />
      )}
    </>
  )
}
