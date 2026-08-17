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

function postJson(path, payload) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function getRoles() {
  return request('/roles')
}

export function getThresholds() {
  return request('/config/thresholds')
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

export function screenBatch(files, { jd, mode }) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  fd.append('jd', jd)
  fd.append('mode', mode)
  return request('/screen/batch', { method: 'POST', body: fd })
}

export function extractJd(jdRaw) {
  return postJson('/jd/extract', { jd_raw: jdRaw })
}

export function getTask(taskId) {
  return request(`/tasks/${taskId}`)
}

/** 轮询任务直至 done/failed；onLog 每次拿到累计日志（含新增行）。 */
export async function waitTask(
  taskId,
  { onLog, interval = 1200, timeout = 180000 } = {},
) {
  const deadline = Date.now() + timeout
  let last = 0
  for (;;) {
    const t = await getTask(taskId)
    if (onLog && t.logs.length !== last) {
      last = t.logs.length
      onLog(t.logs)
    }
    if (t.status === 'done') {
      if (onLog) onLog(t.logs)
      return t.result
    }
    if (t.status === 'failed') throw new Error(t.error || '任务失败')
    if (Date.now() > deadline) {
      throw new Error('任务超时（3 分钟未完成），请查看后端 var/log/api.log')
    }
    await new Promise((r) => setTimeout(r, interval))
  }
}

export function saveJd(payload) {
  return postJson('/jd/save', payload)
}

export function listJds() {
  return request('/jd/list')
}

export function updateJd(payload) {
  return postJson('/jd/update', payload)
}

export function setLabel(recordKey, label) {
  return postJson('/label', { record_key: recordKey, label })
}

export function getHistory() {
  return request('/history')
}

export function getHistorySession(sessionId) {
  return request(`/history/${sessionId}`)
}

export function getDashboard() {
  return request('/dashboard')
}

export function getModels() {
  return request('/models')
}

export function setDefaultModel(provider, model) {
  return postJson('/models/default', { provider, model })
}

export function clearUsage() {
  return postJson('/dashboard/clear', {})
}

export function applyThreshold(threshold) {
  return postJson('/eval/apply-threshold', { threshold })
}

export { API_BASE, API_KEY }
