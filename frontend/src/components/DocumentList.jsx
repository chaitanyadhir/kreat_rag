import { useState, useEffect } from "react"

function DocumentList({ refresh }) {
  const [documents, setDocuments] = useState([])

  const fetchDocuments = async () => {
    const response = await fetch("http://localhost:8000/api/documents")
    const data = await response.json()
    setDocuments(data)
  }

  const handleDelete = async (id) => {
    await fetch(`http://localhost:8000/api/documents/${id}`, {
      method: "DELETE"
    })
    fetchDocuments()
  }

  useEffect(() => {
    fetchDocuments()
  }, [refresh])

  useEffect(() => {
    const hasProcessing = documents.some(d => d.status === "processing")
    if (!hasProcessing) return
    const interval = setInterval(fetchDocuments, 3000)
    return () => clearInterval(interval)
  }, [documents])

  const statusColor = (status) => {
    if (status === "success") return "text-green-600"
    if (status === "processing") return "text-yellow-500"
    return "text-red-500"
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Indexed Documents</h2>
      {documents.length === 0 ? (
        <p className="text-gray-500">No documents indexed yet.</p>
      ) : (
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b">
              <th className="py-2 pr-4">Filename</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Chunks</th>
              <th className="py-2 pr-4">Uploaded</th>
              <th className="py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {documents.map(doc => (
              <tr key={doc.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-4 max-w-xs truncate">{doc.filename}</td>
                <td className={`py-2 pr-4 font-medium ${statusColor(doc.status)}`}>
                  {doc.status}
                </td>
                <td className="py-2 pr-4">{doc.chunk_count ?? "—"}</td>
                <td className="py-2 pr-4 text-sm text-gray-500">
                  {new Date(doc.created_at).toLocaleDateString()}
                </td>
                <td className="py-2">
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default DocumentList