const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || ''

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (API_KEY) headers['X-API-Key'] = API_KEY
  let resp
  try {
    resp = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new Error(`无法连接后端 ${API_BASE}，请确认已启动（uvicorn backend.api.main:app）`)
  }
  const body = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error(body.detail || `HTTP ${resp.status}`)
  return body
}

export function getRoles() {
  return request('/roles')
}

export function getEval() {
  return request('/eval')
}

export function screenResume(file, { jd, mode }) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('jd', jd)
  fd.append('mode', mode)
  return request('/screen', { method: 'POST', body: fd })
}

export { API_BASE, API_KEY }
