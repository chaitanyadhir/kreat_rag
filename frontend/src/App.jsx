import { useCallback, useEffect, useRef, useState } from "react"
import { API } from "./components/api"
import { useDocuments } from "./hooks/useDocuments"
import { fetchSession, useSessions } from "./hooks/useSessions"
import Sidebar from "./components/Sidebar"
import { MenuIcon } from "./components/icons"
import Message from "./components/Message"
import ChatInput from "./components/ChatInput"
import SourcesPanel from "./components/SourcesPanel"

const WS_URL = API.replace(/^http/, "ws") + "/ws/ask"

function App() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [panel, setPanel] = useState({ open: false, messageId: null, highlight: null })

  const [sessionId, setSessionId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(min-width: 768px)").matches
  )
  const [notice, setNotice] = useState("")

  const docs = useDocuments()
  const history = useSessions()
  const bottomRef = useRef(null)
  const idRef = useRef(0)
  const wsRef = useRef(null)
  const loadToken = useRef(0) // ignores stale session loads if the user clicks around quickly

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
    wsRef.current = ws
    let finished = false
    ws.onopen = () => ws.send(JSON.stringify({ query, session_id: sessionId }))
    ws.onmessage = (e) => {
      if (wsRef.current !== ws) return // user switched chats; drop late events
      const msg = JSON.parse(e.data)
      if (msg.type === "session") {
        setSessionId(msg.id)
        syncUrl(msg.id)
        history.refresh()
      } else if (msg.type === "sources") patch(botId, { sources: msg.sources })
      else if (msg.type === "token")
        setMessages((all) =>
          all.map((m) => m.id === botId ? { ...m, status: "streaming", text: m.text + msg.text } : m)
        )
      else if (msg.type === "done") { finished = true; patch(botId, { status: "done" }); history.refresh() }
      else if (msg.type === "error") { finished = true; patch(botId, { status: "error", text: msg.detail }) }
    }
    ws.onclose = () => {
      if (wsRef.current !== ws) return // closed on purpose by closeStream()
      wsRef.current = null
      if (!finished) patch(botId, { status: "error", text: "Connection lost" })
      setLoading(false)
      history.refresh()
    }
  }

  const closeStream = () => {
    const ws = wsRef.current
    wsRef.current = null
    ws?.close()
    setLoading(false)
  }

  const syncUrl = (id) => {
    const url = new URL(window.location.href)
    if (id) url.searchParams.set("session", id)
    else url.searchParams.delete("session")
    window.history.replaceState(null, "", url)
  }

  const resetPanel = () => setPanel({ open: false, messageId: null, highlight: null })

  const newChat = () => {
    loadToken.current++
    closeStream()
    setMessages([])
    setSessionId(null)
    setNotice("")
    syncUrl(null)
    resetPanel()
    if (window.innerWidth < 768) setSidebarOpen(false)
  }

  const openSession = useCallback(async (id) => {
    const token = ++loadToken.current
    closeStream()
    setNotice("")
    try {
      const data = await fetchSession(id)
      if (token !== loadToken.current) return
      if (!data) {
        setNotice("That chat no longer exists.")
        setMessages([]); setSessionId(null); syncUrl(null)
        history.refresh()
        return
      }
      setMessages(
        data.messages.map((m) => {
          const ok = m.status === "done" || (m.role === "assistant" && m.content)
          return {
            id: ++idRef.current,
            role: m.role,
            text: ok || m.role === "user" ? m.content : "No answer was saved for this question.",
            status: m.role === "user" ? undefined : ok ? "done" : "error",
            sources: m.sources ?? [],
          }
        })
      )
      setSessionId(id)
      syncUrl(id)
      resetPanel()
    } catch (err) {
      if (token === loadToken.current) setNotice(err.message || "Couldn't load that chat.")
    }
    if (window.innerWidth < 768) setSidebarOpen(false)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // resume from ?session=ID on first load (refresh / shared link)
  useEffect(() => {
    const id = Number(new URL(window.location.href).searchParams.get("session"))
    if (id) openSession(id)
  }, [openSession])

  const deleteSession = async (s) => {
    if (!window.confirm(`Delete "${s.title}"? This can't be undone.`)) return
    const ok = await history.remove(s.id)
    if (ok && s.id === sessionId) newChat()
  }

  const openSources = (messageId, highlight) => {
    setPanel((p) =>
      p.open && p.messageId === messageId && highlight === null
        ? { ...p, open: false } // clicking the same pill again closes it
        : { open: true, messageId, highlight }
    )
  }

  const panelSources = messages.find((m) => m.id === panel.messageId)?.sources ?? []

  return (
    <div className="flex h-dvh overflow-hidden bg-brand-beige text-brand-navy">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={history.sessions}
        loadError={history.loadError}
        activeId={sessionId}
        onNew={newChat}
        onSelect={openSession}
        onRename={history.rename}
        onDelete={deleteSession}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 px-6 py-4">
          {!sidebarOpen && (
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open history"
              className="rounded p-1 text-brand-teal hover:bg-brand-sky/50 hover:text-brand-navy"
            >
              <MenuIcon className="h-5 w-5" />
            </button>
          )}
          <h1 className="text-xl font-bold text-brand-navy">Kreat RAG</h1>
        </header>
        {notice && (
          <p className="mx-auto w-full max-w-4xl px-6 text-sm text-red-500">{notice}</p>
        )}

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