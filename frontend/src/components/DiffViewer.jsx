export default function DiffViewer({ diff }) {
  if (!diff) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "#475569", fontSize: 13 }}>
        No diff generated yet.
      </div>
    )
  }

  const lines = diff.split("\n")

  return (
    <div style={{
      background: "#080810",
      borderRadius: 8,
      overflow: "auto",
      maxHeight: 400,
      fontFamily: "ui-monospace, monospace",
      fontSize: 12,
      lineHeight: 1.6,
    }}>
      {lines.map((line, i) => {
        let bg = "transparent"
        let color = "#94a3b8"

        if (line.startsWith("+") && !line.startsWith("+++")) {
          bg = "#052e16"
          color = "#4ade80"
        } else if (line.startsWith("-") && !line.startsWith("---")) {
          bg = "#2d0a0a"
          color = "#f87171"
        } else if (line.startsWith("@@")) {
          bg = "#1e1b4b"
          color = "#a78bfa"
        } else if (line.startsWith("+++") || line.startsWith("---")) {
          color = "#e2e8f0"
        }

        return (
          <div key={i} style={{
            display: "flex",
            background: bg,
            padding: "0 16px",
          }}>
            <span style={{ color: "#334155", width: 32, userSelect: "none", flexShrink: 0, paddingRight: 8 }}>
              {i + 1}
            </span>
            <span style={{ color, whiteSpace: "pre" }}>{line || " "}</span>
          </div>
        )
      })}
    </div>
  )
}