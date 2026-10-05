import { useEffect, useRef, useState } from "react"
import AutoHeight from "./AutoHeight"
import {
  PaperclipIcon,
  TrashIcon,
  CheckIcon,
  AlertIcon,
  UploadIcon,
} from "./icons"

function StatusIcon({ status }) {
  if (status === "processing")
    return (
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-brand-teal border-t-transparent" />
    )
  if (status === "success")
    return <CheckIcon className="h-4 w-4 shrink-0 text-green-600" />
  return <AlertIcon className="h-4 w-4 shrink-0 text-red-500" />
}

function statusText(doc) {
  if (doc.status === "processing") return "Processing…"
  if (doc.status === "success") {
    const date = new Date(doc.created_at).toLocaleDateString()
    return `Ready · ${doc.chunk_count ?? 0} chunks · ${date}`
  }
  return doc.error_message || "Failed"
}

function statusColor(status) {
  if (status === "processing") return "text-brand-teal animate-pulse"
  if (status === "success") return "text-green-700"
  return "text-red-500"
}

export default function AttachMenu({
  documents,
  uploading,
  error,
  loadError,
  onUpload,
  onDelete,
  onRefresh,
}) {
  const [open, setOpen] = useState(false)
  const [confirmId, setConfirmId] = useState(null)
  const wrapRef = useRef(null)
  const fileRef = useRef(null)

  const processingCount = documents.filter((d) => d.status === "processing").length
  const shownError = error || loadError

  // Always show fresh data when the popup opens
  useEffect(() => {
    if (open) onRefresh()
  }, [open, onRefresh])

  // Close on outside click or Escape
  useEffect(() => {
    if (!open) return
    const onDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => e.key === "Escape" && setOpen(false)
    document.addEventListener("mousedown", onDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
    e.target.value = "" // allow re-selecting the same file
  }

  const handleDelete = (id) => {
    if (confirmId === id) {
      setConfirmId(null)
      onDelete(id)
      return
    }
    setConfirmId(id)
    setTimeout(() => setConfirmId((c) => (c === id ? null : c)), 3000)
  }

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label="Documents"
        className={`relative flex h-10 w-10 items-center justify-center rounded-full transition hover:bg-brand-sky/40 ${
          open ? "bg-brand-sky/50 text-brand-navy" : "text-brand-teal"
        }`}
      >
        <PaperclipIcon />
        {processingCount > 0 && (
          <span className="absolute right-0.5 top-0.5 h-2.5 w-2.5 animate-pulse rounded-full bg-brand-teal" />
        )}
      </button>

      {/* Popup: grows upward from the button */}
      <div
        inert={!open}
        className={`absolute bottom-full left-0 mb-4 w-[22rem] max-w-[85vw] origin-bottom-left rounded-2xl border border-brand-sky bg-white shadow-xl transition duration-200 ease-out ${
          open
            ? "translate-y-0 scale-100 opacity-100"
            : "pointer-events-none translate-y-3 scale-95 opacity-0"
        }`}
      >
        <AutoHeight>
          <div className="p-3">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.pptx"
              className="hidden"
              onChange={handleFile}
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-brand-sky px-3 py-3 text-sm text-brand-teal transition hover:border-brand-teal hover:bg-brand-beige hover:text-brand-navy disabled:opacity-60"
            >
              {uploading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-teal border-t-transparent" />
              ) : (
                <UploadIcon className="h-4 w-4" />
              )}
              {uploading ? "Uploading…" : "Upload PDF or PPTX"}
            </button>

            {shownError && <p className="mt-2 text-xs text-red-500">{shownError}</p>}

            <div className="mt-4 flex items-center justify-between px-1">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-brand-teal">
                Documents
              </h3>
              <span className="text-xs text-brand-teal">{documents.length}</span>
            </div>

            {documents.length === 0 ? (
              <p className="px-1 py-3 text-sm text-brand-teal/70">No documents yet.</p>
            ) : (
              <ul className="mt-2 max-h-64 space-y-1 overflow-y-auto">
                {documents.map((doc) => (
                  <li
                    key={doc.id}
                    className="flex items-center gap-2 rounded-lg px-2 py-2 hover:bg-brand-beige"
                  >
                    <StatusIcon status={doc.status} />
                    <div className="min-w-0 flex-1">
                      <p
                        className="truncate text-sm text-brand-navy"
                        title={doc.filename}
                      >
                        {doc.filename}
                      </p>
                      <p
                        className={`truncate text-xs ${statusColor(doc.status)}`}
                        title={statusText(doc)}
                      >
                        {statusText(doc)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      disabled={doc.status === "processing"}
                      title={
                        doc.status === "processing"
                          ? "Wait until processing finishes"
                          : "Delete"
                      }
                      className={`flex h-8 shrink-0 items-center justify-center rounded-lg px-2 text-xs transition disabled:cursor-not-allowed disabled:opacity-30 ${
                        confirmId === doc.id
                          ? "bg-red-50 font-medium text-red-600"
                          : "text-brand-teal/60 hover:bg-red-50 hover:text-red-500"
                      }`}
                    >
                      {confirmId === doc.id ? "Delete?" : <TrashIcon className="h-4 w-4" />}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </AutoHeight>
      </div>
    </div>
  )
}