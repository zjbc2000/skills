import { useState } from 'react'
import DashboardView from './views/DashboardView.jsx'
import EvalView from './views/EvalView.jsx'
import HistoryView from './views/HistoryView.jsx'
import JdView from './views/JdView.jsx'
import ScreenView from './views/ScreenView.jsx'

const NAV = [
  { key: 'screen', label: '简历筛选', icon: <ClipboardIcon /> },
  { key: 'jd', label: 'JD 管理', icon: <BriefcaseIcon /> },
  { key: 'history', label: '历史记录', icon: <HistoryIcon /> },
  { key: 'dashboard', label: '模型面板', icon: <GaugeIcon /> },
  { key: 'eval', label: '数据·评测', icon: <ChartIcon /> },
]

export default function App() {
  const [view, setView] = useState('screen')
  const [rolesVersion, setRolesVersion] = useState(0) // JD 保存后刷新筛简历页岗位
  return (
    <div className="shell">
      <Sidebar active={view} onSelect={setView} />
      <main className="content">
        {/* 含异步任务的视图常驻（hidden 而非卸载），切换栏后任务/日志/结果不丢失 */}
        <div hidden={view !== 'screen'}>
          <ScreenView key={rolesVersion} />
        </div>
        <div hidden={view !== 'jd'}>
          <JdView onSaved={() => setRolesVersion((v) => v + 1)} />
        </div>
        {view === 'history' && <HistoryView key={rolesVersion} />}
        {view === 'dashboard' && <DashboardView />}
        {view === 'eval' && <EvalView />}
      </main>
    </div>
  )
}

function Sidebar({ active, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <LogoMark />
        <span>AE工作台</span>
      </div>
      <nav className="nav" aria-label="主导航">
        {NAV.map((item) => (
          <button
            key={item.key}
            className={`nav-item${active === item.key ? ' active' : ''}`}
            onClick={() => onSelect(item.key)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="account">
        <div className="avatar" aria-hidden="true">Z</div>
        <div className="account-meta">
          <div className="account-name">zed</div>
          <div className="account-role">AE</div>
        </div>
      </div>
    </aside>
  )
}

function LogoMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {/* 终端窗口 */}
      <rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 8h18" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="6.5" cy="6" r="0.9" fill="#ef4444" />
      <circle cx="9.5" cy="6" r="0.9" fill="#fbbf24" />
      <circle cx="12.5" cy="6" r="0.9" fill="#22c55e" />
      {/* AE + 光标 */}
      <text x="7" y="16" fontSize="7" fontFamily="JetBrains Mono, monospace" fontWeight="500" fill="currentColor">AE</text>
      <rect x="14.5" y="12.5" width="3.5" height="5" fill="#22c55e" opacity="0.9" />
    </svg>
  )
}

function ClipboardIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="m9 14 2 2 4-4" />
    </svg>
  )
}

function BriefcaseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
      <path d="M3 13h18" />
    </svg>
  )
}

function ChartIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M4 20V4" />
      <path d="M4 20h16" />
      <path d="M8 16v-5" />
      <path d="M13 16V8" />
      <path d="M18 16v-8" />
    </svg>
  )
}

function HistoryIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

function GaugeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M4 18a8 8 0 1 1 16 0" />
      <path d="M12 18l4-6" />
      <circle cx="12" cy="18" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  )
}
