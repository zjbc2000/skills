import { useEffect, useState } from 'react'
import { extractJd, waitTask } from '../api.js'

/**
 * JD 新建/编辑弹窗。
 * 新建：JD 原文 -> 抽取字段（弹窗内异步，带日志）-> 可编辑表单 -> 保存
 * 编辑：预填现有字段，可重新抽取或直接改
 */
export default function JdModal({ jd, onClose, onSave, busy }) {
  const editing = Boolean(jd)
  const [jdRaw, setJdRaw] = useState('')
  const [form, setForm] = useState(
    jd
      ? {
          key: jd.key,
          position: jd.position || '',
          skills: (jd.skills || []).join('\n'),
          red_lines: (jd.red_lines || []).join('\n'),
        }
      : { key: '', position: '', skills: '', red_lines: '' },
  )
  const [logs, setLogs] = useState([])
  const [extracting, setExtracting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function onExtract() {
    if (!jdRaw.trim()) {
      setError('请先粘贴 JD 原文')
      return
    }
    setError('')
    setLogs([])
    setExtracting(true)
    try {
      const { task_id } = await extractJd(jdRaw)
      const fields = await waitTask(task_id, {
        onLog: (lines) => setLogs(lines),
      })
      if (fields) {
        setForm((f) => ({
          ...f,
          position: fields.position || f.position,
          skills: (fields.skills || []).join('\n'),
          red_lines: (fields.red_lines || []).join('\n'),
        }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setExtracting(false)
    }
  }

  function onSubmit(e) {
    e.preventDefault()
    const skills = form.skills.split('\n').map((s) => s.trim()).filter(Boolean)
    if (!form.key.trim()) {
      setError('请填写岗位名')
      return
    }
    if (!skills.length) {
      setError('skills 不能为空')
      return
    }
    setError('')
    onSave({
      old_key: jd?.key, // 新建时 undefined
      key: form.key.trim(),
      position: form.position.trim(),
      skills,
      red_lines: form.red_lines.split('\n').map((s) => s.trim()).filter(Boolean),
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{editing ? `编辑 · ${jd.key}` : '新建 JD'}</h2>
          <button className="link" onClick={onClose} aria-label="关闭">×</button>
        </div>

        <form onSubmit={onSubmit}>
          {!editing && (
            <div className="field modal-extract">
              <span className="eyebrow">JD 原文 → 抽取字段</span>
              <textarea
                rows={6}
                value={jdRaw}
                onChange={(e) => setJdRaw(e.target.value)}
                placeholder="粘贴 JD 原文，LLM 抽取 position / skills / red_lines"
              />
              <button type="button" className="extract-btn" onClick={onExtract} disabled={extracting}>
                <DownloadIcon />
                {extracting ? '抽取中…' : '抽取字段'}
              </button>
              {(extracting || logs.length > 0) && (
                <pre className="log-box modal-logs">
                  {logs.map((line, i) => (
                    <div key={i} className="log-line">{line}</div>
                  ))}
                </pre>
              )}
            </div>
          )}

          <div className="field-grid modal-grid">
            <label className="field">
              <span>岗位名（jd_map key）</span>
              <input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
            </label>
            <label className="field">
              <span>position（岗位名称）</span>
              <input value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
            </label>
          </div>
          <label className="field">
            <span>skills（每行一条）</span>
            <textarea rows={7} value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
          </label>
          <label className="field">
            <span>red_lines（每行一条，可留空）</span>
            <textarea rows={3} value={form.red_lines} onChange={(e) => setForm({ ...form, red_lines: e.target.value })} />
          </label>

          {error && <p className="error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>取消</button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? '保存中…' : editing ? '保存修改' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 3v12" />
      <path d="m6 11 6 6 6-6" />
      <path d="M4 21h16" />
    </svg>
  )
}
