import { useState } from 'react'
import { extractJd, saveJd, waitTask } from '../api.js'

export default function JdView({ onSaved }) {
  const [jdRaw, setJdRaw] = useState('')
  const [form, setForm] = useState(null) // {key, position, skills, red_lines}
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  async function onExtract() {
    if (!jdRaw.trim()) {
      setError('请先粘贴 JD 原文')
      return
    }
    setError('')
    setNotice('')
    setLogs([])
    setBusy(true)
    try {
      const { task_id } = await extractJd(jdRaw)
      const fields = await waitTask(task_id, {
        onLog: (lines) => setLogs(lines),
      })
      setForm({
        key: '',
        position: fields.position || '',
        skills: (fields.skills || []).join('\n'),
        red_lines: (fields.red_lines || []).join('\n'),
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function onSave(e) {
    e.preventDefault()
    if (!form) return
    const skills = form.skills.split('\n').map((s) => s.trim()).filter(Boolean)
    if (!form.key.trim()) {
      setError('请填写岗位名（将注册到岗位下拉框）')
      return
    }
    if (!skills.length) {
      setError('skills 不能为空')
      return
    }
    setError('')
    setBusy(true)
    try {
      const { roles } = await saveJd({
        key: form.key.trim(),
        position: form.position.trim(),
        skills,
        red_lines: form.red_lines.split('\n').map((s) => s.trim()).filter(Boolean),
      })
      setNotice(`已保存「${form.key.trim()}」，当前岗位：${roles.join('、')}`)
      setForm(null)
      setJdRaw('')
      if (onSaved) onSaved(roles)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h1>JD 管理</h1>

      <section className="card">
        <h2>从 JD 原文抽取字段</h2>
        <label className="field">
          <span>JD 原文（粘贴岗位职责与要求）</span>
          <textarea
            rows={10}
            value={jdRaw}
            onChange={(e) => setJdRaw(e.target.value)}
            placeholder="粘贴 JD 原文，LLM 将抽取 position / skills / red_lines 结构化字段"
          />
        </label>
        <button className="primary" onClick={onExtract} disabled={busy}>
          {busy ? '抽取中…' : '抽取字段'}
        </button>
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="notice">{notice}</p>}
        {(busy || logs.length > 0) && (
          <div className="task-log">
            <pre className="log-box">
              {logs.map((line, i) => (
                <div key={i} className="log-line">{line}</div>
              ))}
            </pre>
          </div>
        )}
      </section>

      {form && (
        <section className="card">
          <h2>确认并保存（可编辑）</h2>
          <form onSubmit={onSave}>
            <div className="field-grid">
              <label className="field">
                <span>岗位名（jd_map key，保存后出现在筛简历岗位下拉框）</span>
                <input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
              </label>
              <label className="field">
                <span>position（岗位名称）</span>
                <input value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
              </label>
            </div>
            <label className="field">
              <span>skills（每行一条，逐条对应 JD 条目）</span>
              <textarea rows={8} value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
            </label>
            <label className="field">
              <span>red_lines（每行一条，一票否决条件；可留空）</span>
              <textarea rows={3} value={form.red_lines} onChange={(e) => setForm({ ...form, red_lines: e.target.value })} />
            </label>
            <button className="primary" disabled={busy}>
              {busy ? '保存中…' : '保存到 jd_map'}
            </button>
          </form>
        </section>
      )}
    </>
  )
}
