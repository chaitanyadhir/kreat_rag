import { useState } from "react"
import Upload from "./components/Upload"
import DocumentList from "./components/DocumentList"
import Search from "./components/Search"

function App() {
  const [tab, setTab] = useState("documents")
  const [refresh, setRefresh] = useState(0)

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Kreat RAG</h1>

      <div className="flex gap-4 border-b mb-6">
        {["upload", "documents", "search"].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-2 capitalize ${tab === t ? "border-b-2 border-blue-500 font-medium" : "text-gray-500"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "upload" && <Upload onUploadSuccess={() => { setRefresh(r => r + 1); setTab("documents") }} />}
      {tab === "documents" && <DocumentList refresh={refresh} />}
      {tab === "search" && <Search />}
    </div>
  )
}

export default App