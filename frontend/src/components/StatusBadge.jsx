const STATUS = {
  pending:          { bg: "#1e293b", color: "#94a3b8", label: "Pending" },
  running:          { bg: "#1e3a5f", color: "#60a5fa", label: "Running" },
  awaiting_review:  { bg: "#3d2d00", color: "#fbbf24", label: "Awaiting Review" },
  approved:         { bg: "#1e1b4b", color: "#a78bfa", label: "Approved" },
  completed:        { bg: "#052e16", color: "#4ade80", label: "Completed" },
  failed:           { bg: "#2d0a0a", color: "#f87171", label: "Failed" },
}

export default function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS.pending
  return (
    <span style={{
      background: s.bg,
      color: s.color,
      border: "1px solid " + s.color + "33",
      borderRadius: 20,
      padding: "3px 10px",
      fontSize: 11,
      fontWeight: 500,
      letterSpacing: "0.03em",
      whiteSpace: "nowrap",
    }}>
      {s.label}
    </span>
  )
}