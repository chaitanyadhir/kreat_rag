import { useState } from "react"
import { CheckIcon, CloseIcon, MenuIcon, PencilIcon, PlusIcon, TrashIcon } from "./icons"

const DAY = 86_400_000

// Server timestamps are UTC but may arrive without a "Z"; treat them as UTC.
const toDate = (s) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + "Z")

function groupByDate(sessions) {
  const startOfToday = new Date().setHours(0, 0, 0, 0)
  const buckets = [
    ["Today", []],
    ["Yesterday", []],
    ["Previous 7 days", []],
    ["Older", []],
  ]
  for (const s of sessions) {
    const t = toDate(s.updated_at).getTime()
    const i = t >= startOfToday ? 0 : t >= startOfToday - DAY ? 1 : t >= startOfToday - 7 * DAY ? 2 : 3
    buckets[i][1].push(s)
  }
  return buckets.filter(([, items]) => items.length)
}

function Row({ session, active, onSelect, onRename, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState("")

  const start = () => {
    setDraft(session.title)
    setEditing(true)
  }
  const commit = () => {
    const t = draft.trim()
    setEditing(false)
    if (t && t !== session.title) onRename(session.id, t)
  }

  if (editing) {
    return (
      <div className="flex items-center gap-1 rounded-lg bg-white px-2 py-1.5">
        <input
          autoFocus
          value={draft}
          maxLength={200}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) commit()
            if (e.key === "Escape") setEditing(false)
          }}
          onBlur={commit}
          className="min-w-0 flex-1 bg-transparent text-sm text-brand-navy outline-none"
        />
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={commit} aria-label="Save title" className="text-brand-teal hover:text-brand-navy">
          <CheckIcon className="h-4 w-4" />
        </button>
      </div>
    )
  }

  return (
    <div
      className={`group flex items-center rounded-lg transition ${
        active ? "bg-brand-sky/70" : "hover:bg-brand-sky/40"
      }`}
    >
      <button
        type="button"
        onClick={() => onSelect(session.id)}
        onDoubleClick={start}
        title={session.title}
        aria-current={active ? "true" : undefined}
        className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm text-brand-navy"
      >
        {session.title}
      </button>
      <div className="flex shrink-0 gap-0.5 pr-1.5 opacity-0 transition focus-within:opacity-100 group-hover:opacity-100 max-md:opacity-100">
        <button type="button" onClick={start} aria-label="Rename chat" className="rounded p-1 text-brand-teal hover:bg-white hover:text-brand-navy">
          <PencilIcon className="h-3.5 w-3.5" />
        </button>
        <button type="button" onClick={() => onDelete(session)} aria-label="Delete chat" className="rounded p-1 text-brand-teal hover:bg-white hover:text-red-500">
          <TrashIcon className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}

export default function Sidebar({ open, onClose, sessions, loadError, activeId, onNew, onSelect, onRename, onDelete }) {
  const groups = groupByDate(sessions)

  return (
    <>
      {/* mobile backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-20 bg-brand-navy/30 transition-opacity md:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        aria-hidden={!open}
        inert={!open}
        className={`fixed inset-y-0 left-0 z-30 overflow-hidden border-brand-sky bg-brand-beige transition-all duration-200 ease-out md:static md:z-auto ${
          open ? "w-72 border-r" : "w-72 -translate-x-full md:w-0 md:translate-x-0 md:border-r-0"
        }`}
      >
        {/* fixed-width inner box so content slides rather than squishes */}
        <div className="flex h-full w-72 flex-col">
          <div className="flex items-center justify-between px-4 py-4">
            <span className="text-sm font-semibold text-brand-teal">History</span>
            <button type="button" onClick={onClose} aria-label="Close sidebar" className="rounded p-1 text-brand-teal hover:bg-brand-sky/50 hover:text-brand-navy">
              <MenuIcon className="h-5 w-5" />
            </button>
          </div>

          <div className="px-3 pb-2">
            <button
              type="button"
              onClick={onNew}
              className="flex w-full items-center gap-2 rounded-lg border border-brand-sky bg-white px-3 py-2 text-sm text-brand-navy transition hover:border-brand-teal"
            >
              <PlusIcon className="h-4 w-4 text-brand-teal" />
              New chat
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 pb-4">
            {loadError && (
              <p className="flex items-center gap-1 px-1 py-2 text-xs text-red-500">
                <CloseIcon className="h-3.5 w-3.5" /> {loadError}
              </p>
            )}
            {!loadError && sessions.length === 0 && (
              <p className="px-1 py-3 text-xs text-brand-teal">No chats yet. Ask a question to start one.</p>
            )}
            {groups.map(([label, items]) => (
              <div key={label} className="mt-3">
                <p className="px-3 pb-1 text-xs font-medium text-brand-teal/80">{label}</p>
                <div className="space-y-0.5">
                  {items.map((s) => (
                    <Row key={s.id} session={s} active={s.id === activeId} onSelect={onSelect} onRename={onRename} onDelete={onDelete} />
                  ))}
                </div>
              </div>
            ))}
          </nav>
        </div>
      </aside>
    </>
  )
}
