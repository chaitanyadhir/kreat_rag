import { useState } from "react"

function Search() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError("")

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/retrieve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      })

      const data = await response.json()

      if (response.ok) {
        setResults(Array.isArray(data.data.fused_top_results) ? data.data.fused_top_results : [])
      } else {
        setError(data.detail || "Retrieval failed")
      }
    } catch (err) {
      setError("Could not reach the server")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Search</h2>
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
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {error && <p className="text-red-500 mt-4">{error}</p>}

      <div className="mt-6 space-y-4">
        {results.map((result, index) => (
          <div key={index} className="border rounded p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-blue-600">
                {result.parent.metadata?.source || "Unknown source"}
              </span>
              <span className="text-xs text-gray-400">
                Score: {result.rrf_score.toFixed(3)}
              </span>
            </div>
            <p className="text-sm text-gray-700">{result.child.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Search