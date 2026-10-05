import { useState } from "react"
import AttachMenu from "./AttachMenu"
import { SendIcon } from "./icons"

export default function ChatInput({ onSend, loading, attach }) {
  const [value, setValue] = useState("")

  const submit = () => {
    const q = value.trim()
    if (!q || loading) return
    onSend(q)
    setValue("")
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 pb-6 pt-2">
      <div className="flex items-center gap-1 rounded-2xl border border-brand-sky bg-white px-2 py-2.5 shadow-sm transition focus-within:border-brand-teal focus-within:shadow-md">
        <AttachMenu {...attach} />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.nativeEvent.isComposing && submit()}
          maxLength={1000}
          placeholder="Ask your documents..."
          className="min-w-0 flex-1 bg-transparent px-2 py-2 text-brand-navy outline-none placeholder:text-brand-teal/60"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!value.trim() || loading}
          aria-label="Send"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-teal text-white transition hover:bg-brand-navy disabled:bg-brand-sky disabled:hover:bg-brand-sky"
        >
          <SendIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}