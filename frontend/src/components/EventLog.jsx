export default function EventLog({ events = [] }) {
  if (events.length === 0) {
    return (
      <div style={{ padding: "16px", color: "#475569", fontSize: 12, textAlign: "center" }}>
        No events yet.
      </div>
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 240, overflowY: "auto" }}>
      {events.map((event, i) => {
        const type = event.type || event.event_type || ""
        const color = type === "completed" ? "#4ade80"
          : type === "failed" ? "#f87171"
          : type === "started" ? "#60a5fa"
          : "#94a3b8"

        return (
          <div key={i} style={{
            display: "flex", alignItems: "flex-start", gap: 10,
            padding: "8px 12px", background: "#0f0f17",
            borderRadius: 6, fontSize: 12,
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: color, flexShrink: 0, marginTop: 4,
            }} />
            <div style={{ flex: 1 }}>
              <span style={{ color: "#6366f1", fontWeight: 500 }}>
                {event.agent}
              </span>
              <span style={{ color: "#475569", marginLeft: 6 }}>
                {event.summary || event.message || ""}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}