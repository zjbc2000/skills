import { useState } from 'react'

/**
 * 把一次筛选的 snapshot（general/specific 打分明细）渲染成表格组。
 * 通用：projects / tech_stack / highlights / red_lines
 * 特定：position_match / skills
 */
export default function DetailTable({ snapshot }) {
  if (!snapshot) return <p className="muted">无明细数据</p>
  const general = snapshot.general || {}
  const specific = snapshot.specific || {}

  const groups = [
    { key: 'projects', title: '项目经历', items: general.projects },
    { key: 'tech_stack', title: '技术栈', items: general.tech_stack },
    { key: 'highlights', title: '亮点', items: general.highlights },
    { key: 'red_lines', title: '红线', items: general.red_lines, red: true },
  ]
  const pm = specific.position_match
  const skillItems = specific.skills || []

  return (
    <div className="detail-tables">
      {groups
        .filter((g) => g.items && g.items.length > 0)
        .map((g) => <ItemTable key={g.key} {...g} />)}
      {pm && <ItemTable key="position_match" title="岗位匹配" items={[pm]} />}
      {skillItems.length > 0 && (
        <ItemTable key="skills" title="特定技能命中" items={skillItems} skill />
      )}
      {!groups.some((g) => g.items && g.items.length > 0) && !pm && !skillItems.length && (
        <p className="muted">无打分明细</p>
      )}
    </div>
  )
}

function ItemTable({ title, items, red = false, skill = false }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="detail-group">
      <div className="row-between">
        <span className="eyebrow">{title}</span>
        <button className="link" onClick={() => setOpen(!open)}>
          {open ? '收起' : '展开'}
        </button>
      </div>
      {open && (
        <table className="table">
          <thead>
            <tr>
              <th>{skill ? '技能' : red ? '红线' : '条目'}</th>
              {!red && <th className="th-num">bonus</th>}
              <th>判定理由</th>
              <th>原文引用</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td>{skill ? it.skill : red ? it.rule : it.name}</td>
                {!red && (
                  <td className="th-num">
                    {skill && !it.hit ? '—' : it.bonus}
                    {skill && it.hit && <span className="hit-mark">✓</span>}
                  </td>
                )}
                <td className="cell-evidence">{it.evidence}</td>
                <td className="cell-quote" title={it.quotation}>
                  {it.quotation}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
