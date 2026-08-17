import { useEffect, useState } from 'react'
import { saveProvider } from '../api.js'

/**
 * API 端点配置弹窗（OpenAI 兼容协议）：
 * provider 名 / base_url / api_key / 模型名。
 */
export default function ProviderModal({ onClose, onSaved, busy }) {
  const [form, setForm] = useState({ provider: '', base_url: '', api_key: '', model: '' })
  const [error, setError] = useState('')

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    for (const [k, v] of Object.entries(form)) {
      if (!v.trim()) {
        setError(`${k} 必填`)
        return
      }
    }
    try {
      await saveProvider({
        provider: form.provider.trim(),
        base_url: form.base_url.trim(),
        api_key: form.api_key.trim(),
        model: form.model.trim(),
      })
      onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>添加 API 端点</h2>
          <button className="link" onClick={onClose} aria-label="关闭">×</button>
        </div>

        <form onSubmit={onSubmit}>
          <p className="muted">仅支持 OpenAI 兼容协议（base_url + api_key + 模型名）</p>
          <div className="field-grid modal-grid">
            <label className="field">
              <span>provider 名（如 qwen）</span>
              <input
                value={form.provider}
                onChange={(e) => setForm({ ...form, provider: e.target.value })}
                placeholder="qwen"
              />
            </label>
            <label className="field">
              <span>模型名</span>
              <input
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                placeholder="qwen-max"
              />
            </label>
          </div>
          <label className="field">
            <span>base_url（OpenAI 兼容端点）</span>
            <input
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
            />
          </label>
          <label className="field">
            <span>api_key</span>
            <input
              type="password"
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              placeholder="sk-…"
            />
          </label>

          {error && <p className="error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>取消</button>
            <button className="primary" type="submit" disabled={busy}>
              {busy ? '保存中…' : '保存端点'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
