import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT_ENV = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../.env')

export default defineConfig(() => {
  // 从项目根 .env 读取 X_API_KEY 注入为 VITE_API_KEY，避免双份维护
  try {
    process.loadEnvFile(ROOT_ENV)
  } catch {
    // 根 .env 可缺省（本地无鉴权调试）
  }
  process.env.VITE_API_KEY = process.env.VITE_API_KEY || process.env.X_API_KEY || ''

  return {
    plugins: [react()],
    server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  }
})
