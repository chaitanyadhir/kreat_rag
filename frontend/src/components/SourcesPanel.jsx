import { CloseIcon } from "./icons"

export default function SourcesPanel({ open, sources, highlight, onClose }) {
  return (
    <aside
      className={`h-full shrink-0 overflow-hidden bg-brand-beige transition-[width] duration-300 ease-out max-md:fixed max-md:inset-y-0 max-md:right-0 max-md:z-30 ${
        open ? "w-96 max-w-[100vw] border-l border-brand-sky max-md:shadow-xl" : "w-0"
      }`}
    >
      {/* Fixed inner width so text doesn't reflow while the panel animates */}
      <div className="flex h-full w-96 max-w-[100vw] flex-col">
        <div className="flex items-center justify-between border-b border-brand-sky px-5 py-4">
          <h2 className="font-semibold text-brand-navy">Sources</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sources"
            className="rounded-full p-1.5 text-brand-teal hover:bg-brand-sky/50"
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {sources.map((s) => (
            <div
              key={s.id}
              className={`rounded-xl border bg-white p-4 transition ${
                s.id === highlight
                  ? "border-brand-teal ring-2 ring-brand-sky"
                  : "border-brand-sky"
              }`}
            >
              <p className="text-sm font-medium text-brand-teal">
                [{s.id}] {s.source}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-brand-navy/80">{s.snippet}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}