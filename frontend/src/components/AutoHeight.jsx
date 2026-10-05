import { useEffect, useRef, useState } from "react"

export default function AutoHeight({ children }) {
  const innerRef = useRef(null)
  const [height, setHeight] = useState("auto")

  useEffect(() => {
    const el = innerRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setHeight(el.offsetHeight))
    ro.observe(el)
    setHeight(el.offsetHeight)
    return () => ro.disconnect()
  }, [])

  return (
    <div
      style={{ height }}
      className="overflow-hidden transition-[height] duration-300 ease-out"
    >
      <div ref={innerRef}>{children}</div>
    </div>
  )
}
