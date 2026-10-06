import { useEffect, useRef, useState } from "react"
import { API } from "./components/api"
import { useDocuments } from "./hooks/useDocuments"
import Message from "./components/Message"
import ChatInput from "./components/ChatInput"
import SourcesPanel from "./components/SourcesPanel"

const WS_URL = API.replace(/^http/, "ws") + "/ws/ask"

function App() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [panel, setPanel] = useState({ open: false, messageId: null, highlight: null })

  const docs = useDocuments()
  const bottomRef = useRef(null)
  const idRef = useRef(0)

  // Props names must match what AttachMenu expects
  const attach = {
    documents: docs.documents,
    uploading: docs.uploading,
    error: docs.error,
    loadError: docs.loadError,
    onUpload: docs.upload,
    onDelete: docs.remove,
    onRefresh: docs.refresh,
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const patch = (id, fields) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, ...fields } : m)))

  const ask = (query) => {
    const userId = ++idRef.current
    const botId = ++idRef.current
    setMessages((all) => [
      ...all,
      { id: userId, role: "user", text: query },
      { id: botId, role: "assistant", status: "loading", text: "", sources: [] },
    ])
    setLoading(true)

    const ws = new WebSocket(WS_URL)
    let finished = false
    ws.onopen = () => ws.send(JSON.stringify({ query }))
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === "sources") patch(botId, { sources: msg.sources })
      else if (msg.type === "token")
        setMessages((all) =>
          all.map((m) => m.id === botId ? { ...m, status: "streaming", text: m.text + msg.text } : m)
        )
      else if (msg.type === "done") { finished = true; patch(botId, { status: "done" }) }
      else if (msg.type === "error") { finished = true; patch(botId, { status: "error", text: msg.detail }) }
    }
    ws.onclose = () => {
      if (!finished) patch(botId, { status: "error", text: "Connection lost" })
      setLoading(false)
    }
  }

  const openSources = (messageId, highlight) => {
    setPanel((p) =>
      p.open && p.messageId === messageId && highlight === null
        ? { ...p, open: false } // clicking the same pill again closes it
        : { open: true, messageId, highlight }
    )
  }

  const clearChat = () => {
    setMessages([])
    setPanel({ open: false, messageId: null, highlight: null })
  }

  const panelSources = messages.find((m) => m.id === panel.messageId)?.sources ?? []

  return (
    <div className="flex h-dvh overflow-hidden bg-brand-beige text-brand-navy">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold text-brand-navy">Kreat RAG</h1>
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearChat}
              className="text-sm text-brand-teal hover:text-brand-navy"
            >
              Clear chat
            </button>
          )}
        </header>

        <main className="flex-1 overflow-y-auto">
          {/* justify-end anchors messages to the bottom, next to the input bar */}
          <div className="mx-auto flex min-h-full max-w-4xl flex-col justify-end gap-6 px-4 py-6">
            {messages.length === 0 && (
              <div className="my-auto text-center">
                <p className="text-xl text-brand-navy">Ask anything about your documents</p>
                <p className="mt-1 text-sm text-brand-teal">
                  {docs.documents.length === 0
                    ? "Use the paperclip to upload a PDF or PPTX first."
                    : `${docs.documents.length} document${docs.documents.length === 1 ? "" : "s"} indexed.`}
                </p>
              </div>
            )}

            {messages.map((m) => (
              <Message
                key={m.id}
                message={m}
                panelOpenFor={panel.open ? panel.messageId : null}
                onOpenSources={openSources}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        </main>

        <ChatInput onSend={ask} loading={loading} attach={attach} />
      </div>

      <SourcesPanel
        open={panel.open}
        sources={panelSources}
        highlight={panel.highlight}
        onClose={() => setPanel((p) => ({ ...p, open: false }))}
      />
    </div>
  )
}

export default App