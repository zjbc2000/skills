import { useEffect, useRef, useState } from 'react'

/**
 * 主题自定义下拉（替代原生 select，展开菜单适配深色主题）。
 * options 支持字符串数组或 [{value, label}]。
 */
export default function Dropdown({ value, options, onChange, className }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  const current = options.find((o) => (typeof o === 'object' ? o.value : o) === value)
  const label = current
    ? typeof current === 'object'
      ? current.label
      : current
    : value ?? ''

  return (
    <div className={`dropdown ${className || ''}`} ref={ref}>
      <button
        type="button"
        className="dropdown-trigger"
        onClick={() => setOpen(!open)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>{label}</span>
        <svg className="dropdown-caret" width="10" height="6" viewBox="0 0 10 6" aria-hidden="true">
          <path d="M0 0l5 6 5-6z" fill="currentColor" />
        </svg>
      </button>
      {open && (
        <ul className="dropdown-menu" role="listbox">
          {options.map((o) => {
            const v = typeof o === 'object' ? o.value : o
            const l = typeof o === 'object' ? o.label : o
            return (
              <li key={v}>
                <button
                  type="button"
                  className={v === value ? 'selected' : ''}
                  onClick={() => {
                    onChange(v)
                    setOpen(false)
                  }}
                >
                  <span>{l}</span>
                  {v === value && <span className="dropdown-check">✓</span>}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
