import { useState } from 'react'
import EvalView from './views/EvalView.jsx'
import JdView from './views/JdView.jsx'
import ScreenView from './views/ScreenView.jsx'

const NAV = [
  { key: 'screen', label: '筛简历', icon: <ClipboardIcon /> },
  { key: 'jd', label: 'JD 管理', icon: <BriefcaseIcon /> },
  { key: 'eval', label: '评测', icon: <ChartIcon /> },
]

export default function App() {
  const [view, setView] = useState('screen')
  const [rolesVersion, setRolesVersion] = useState(0) // JD 保存后刷新筛简历页岗位
  return (
    <div className="shell">
      <Sidebar active={view} onSelect={setView} />
      <main className="content">
        {view === 'screen' && <ScreenView key={rolesVersion} />}
        {view === 'jd' && <JdView onSaved={() => setRolesVersion((v) => v + 1)} />}
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
        <span>~/ae</span>
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
          <div className="account-role">筛简历管理员</div>
        </div>
      </div>
    </aside>
  )
}

function LogoMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="m9 14 2 2 4-4" />
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
