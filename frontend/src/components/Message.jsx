import { BookIcon } from "./icons"

const CITE = /(\[Source \d+(?:\s*,\s*Source \d+)*\])/g

// Turns "[Source 1]" and "[Source 1, Source 2]" into clickable number chips
function withCitations(text, onCite) {
  return text.split(CITE).map((part, i) => {
    if (!/^\[Source \d/.test(part)) return part
    const nums = [...part.matchAll(/\d+/g)].map((m) => Number(m[0]))
    return (
      <span key={i} className="mx-0.5 inline-flex gap-0.5 align-baseline">
        {nums.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onCite(n)}
            className="rounded bg-brand-sky/60 px-1.5 text-xs font-medium text-brand-navy hover:bg-brand-sky"
          >
            {n}
          </button>
        ))}
      </span>
    )
  })
}

// **bold** inside a line
function renderInline(text, onCite) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.length > 4 && part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i} className="font-semibold">
        {withCitations(part.slice(2, -2), onCite)}
      </strong>
    ) : (
      <span key={i}>{withCitations(part, onCite)}</span>
    )
  )
}

// Minimal formatter: paragraphs, "* " / "- " bullets, **bold**
function FormattedText({ text, onCite }) {
  const blocks = []
  let list = []
  const flush = () => {
    if (list.length) {
      blocks.push({ type: "ul", items: list })
      list = []
    }
  }
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*[*-]\s+(.*)$/)
    if (m) list.push(m[1])
    else {
      flush()
      blocks.push({ type: "p", text: line })
    }
  }
  flush()

  return blocks.map((b, i) => {
    if (b.type === "ul")
      return (
        <ul key={i} className="my-2 list-disc space-y-1.5 pl-5">
          {b.items.map((item, j) => (
            <li key={j}>{renderInline(item, onCite)}</li>
          ))}
        </ul>
      )
    if (b.text.trim() === "") return <div key={i} className="h-2" />
    return <p key={i}>{renderInline(b.text, onCite)}</p>
  })
}

export default function Message({ message, panelOpenFor, onOpenSources }) {
  if (message.role === "user") {
    return (
      <div className="msg-in flex justify-end">
        <p className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-navy px-4 py-2.5 text-white">
          {message.text}
        </p>
      </div>
    )
  }

  const hasSources = message.sources?.length > 0
  const active = panelOpenFor === message.id

  return (
    <div className="msg-in flex justify-start">
      <div className="max-w-[88%]">
        {message.status === "loading" && (
          <div className="flex gap-1.5 py-3">
            {[0, 150, 300].map((d) => (
              <span
                key={d}
                style={{ animationDelay: `${d}ms` }}
                className="h-2 w-2 animate-bounce rounded-full bg-brand-teal"
              />
            ))}
          </div>
        )}

        {message.status === "error" && <p className="text-red-500">{message.text}</p>}

        {(message.status === "done" || message.status === "streaming") && (
          <>
            <div className="leading-relaxed text-brand-navy">
              <FormattedText
                text={message.text}
                onCite={(n) => onOpenSources(message.id, n)}
              />
            </div>
            {hasSources && (
              <button
                type="button"
                onClick={() => onOpenSources(message.id, null)}
                className={`mt-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition ${
                  active
                    ? "border-brand-teal bg-brand-sky/50 text-brand-navy"
                    : "border-brand-sky text-brand-teal hover:bg-white"
                }`}
              >
                <BookIcon className="h-3.5 w-3.5" />
                {message.sources.length} {message.sources.length === 1 ? "source" : "sources"}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}