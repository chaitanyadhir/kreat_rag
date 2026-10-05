import { API } from "./api"
import { useState } from "react"

function Search() {
  const [query, setQuery] = useState("")
  const [answer, setAnswer] = useState("")
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError("")
    setAnswer("")
    setSources([])

    try {
      const response = await fetch(`${API}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      })

      const data = await response.json()

      if (response.ok) {
        setAnswer(data.answer)
        setSources(Array.isArray(data.sources) ? data.sources : [])
      } else {
        setError(data.detail || "Request failed")
      }
    } catch (err) {
      setError("Could not reach the server")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Ask your documents</h2>
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Ask a question..."
          className="border rounded px-4 py-2 flex-1"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>

      {error && <p className="text-red-500 mt-4">{error}</p>}

      {answer && (
        <div className="mt-6 border rounded p-4">
          <p className="text-gray-800 whitespace-pre-wrap">{answer}</p>
        </div>
      )}

      {sources.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-2">Sources</h3>
          <div className="space-y-2">
            {sources.map((s) => (
              <div key={s.id} className="border rounded p-3">
                <span className="text-sm font-medium text-blue-600">
                  [{s.id}] {s.source}
                </span>
                <p className="text-xs text-gray-500 mt-1">{s.snippet}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Search