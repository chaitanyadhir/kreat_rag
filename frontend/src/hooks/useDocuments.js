import { useCallback, useEffect, useState } from "react"
import { API } from "../components/api"

const MAX_BYTES = 25 * 1024 * 1024 // matches the backend limit

async function errorText(res, fallback) {
  try {
    const d = await res.json()
    return typeof d.detail === "string" ? d.detail : fallback
  } catch {
    return fallback
  }
}

export function useDocuments() {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const [loadError, setLoadError] = useState("")

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/documents`)
      if (!res.ok) {
        setLoadError(`Couldn't load documents (${res.status})`)
        return
      }
      const data = await res.json()
      setDocuments([...data].sort((a, b) => b.id - a.id)) // newest first
      setLoadError("")
    } catch {
      setLoadError("Couldn't reach the server")
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Poll only while something is processing, so statuses update live
  const hasProcessing = documents.some((d) => d.status === "processing")
  useEffect(() => {
    if (!hasProcessing) return
    const t = setInterval(refresh, 3000)
    return () => clearInterval(t)
  }, [hasProcessing, refresh])

  const upload = async (file) => {
    setError("")
    const ext = file.name.split(".").pop()?.toLowerCase()
    if (ext !== "pdf" && ext !== "pptx") {
      setError("Only PDF and PPTX files are supported")
      return
    }
    if (file.size > MAX_BYTES) {
      setError("File too large (max 25 MB)")
      return
    }

    setUploading(true)
    try {
      const form = new FormData()
      form.append("file", file)
      const res = await fetch(`${API}/api/ingest`, { method: "POST", body: form })
      if (!res.ok) setError(await errorText(res, "Upload failed"))
      await refresh()
    } catch {
      setError("Could not reach the server")
    } finally {
      setUploading(false)
    }
  }

  const remove = async (id) => {
    setError("")
    try {
      const res = await fetch(`${API}/api/documents/${id}`, { method: "DELETE" })
      if (!res.ok) setError(await errorText(res, "Delete failed"))
      await refresh()
    } catch {
      setError("Could not reach the server")
    }
  }

  return { documents, uploading, error, loadError, upload, remove, refresh }
}