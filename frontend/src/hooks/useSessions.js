import { useCallback, useEffect, useState } from "react"
import { API } from "../components/api"

export function useSessions() {
  const [sessions, setSessions] = useState([])
  const [loadError, setLoadError] = useState("")

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/sessions`)
      if (!res.ok) throw new Error(res.status)
      setSessions(await res.json())
      setLoadError("")
    } catch {
      setLoadError("Couldn't load history")
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const rename = async (id, title) => {
    // optimistic, then reconcile
    setSessions((all) => all.map((s) => (s.id === id ? { ...s, title } : s)))
    try {
      const res = await fetch(`${API}/api/sessions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      })
      if (!res.ok) throw new Error(res.status)
    } catch {
      await refresh()
    }
  }

  const remove = async (id) => {
    try {
      const res = await fetch(`${API}/api/sessions/${id}`, { method: "DELETE" })
      if (!res.ok && res.status !== 404) throw new Error(res.status)
      setSessions((all) => all.filter((s) => s.id !== id))
      return true
    } catch {
      setLoadError("Couldn't delete that chat")
      return false
    }
  }

  return { sessions, loadError, refresh, rename, remove }
}

export async function fetchSession(id) {
  const res = await fetch(`${API}/api/sessions/${id}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Couldn't load chat (${res.status})`)
  return res.json()
}
