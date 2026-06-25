import { useState } from "react"

function Upload({ onUploadSuccess }) {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState(null)
  const [message, setMessage] = useState("")

  const handleFileChange = (e) => {
    // get the first file from e.target.files and set it
    setFile(e.target.files[0])
}

  const handleUpload = async () => {
    if (!file) return

    const formData = new FormData()
    // append file to formData with key "file"
    formData.append("file", file)

    setStatus("uploading")

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/ingest`, {
        method: "POST",
        body: formData
      })

      const data = await response.json()

      if (response.ok) {
        setStatus("processing")
        setMessage(`Upload successful. Document ID: ${data.document_id}`)
        // call onUploadSuccess so DocumentList refreshes
        if (onUploadSuccess) onUploadSuccess()
      } else {
        setStatus("error")
        setMessage(data.detail || "Upload failed")
      }

    } catch (err) {
      setStatus("error")
      setMessage("Could not reach the server")
    }
  }

  return (
    <div className="p-6">
      <input
        type="file"
        accept=".pdf,.pptx"
        onChange={handleFileChange}
      />
      <button
        onClick={handleUpload}
        disabled={!file || status === "uploading"}
        className="bg-blue-500 text-white px-4 py-2 rounded ml-4"
      >
        {status === "uploading" ? "Uploading..." : "Upload"}
      </button>
      {message && <p className="mt-4">{message}</p>}
    </div>
  )
}

export default Upload