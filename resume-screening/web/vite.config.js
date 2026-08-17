import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT_ENV = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../.env')
const API_PORT = () => process.env.API_PORT || '8000'

export default defineConfig(() => {
  // 从项目根 .env 读取端口与密钥，避免双份维护
  try {
    process.loadEnvFile(ROOT_ENV)
  } catch {
    // 根 .env 可缺省
  }
  process.env.VITE_API_KEY = process.env.VITE_API_KEY || process.env.X_API_KEY || ''
  process.env.VITE_API_BASE =
    process.env.VITE_API_BASE || `http://localhost:${API_PORT()}`

  return {
    plugins: [react()],
    server: {
      port: Number(process.env.WEB_PORT || 5173),
      proxy: { '/api': `http://localhost:${API_PORT()}` },
    },
  }
})
