import { useState } from "react"
import { approveJob } from "../lib/api"

export default function ApprovalPanel({ jobId, onDecision }) {
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const decide = async (decision) => {
    setLoading(true)
    try {
      await approveJob(jobId, decision)
      setDone(true)
      onDecision && onDecision(decision)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div style={{
        background: "#052e16", border: "1px solid #16a34a",
        borderRadius: 10, padding: "16px 20px",
        color: "#4ade80", fontSize: 13, textAlign: "center",
      }}>
        Decision sent. Pipeline resuming — status will update shortly.
      </div>
    )
  }

  return (
    <div style={{
      background: "#3d2d00", border: "1px solid #d97706",
      borderRadius: 10, padding: "20px 24px",
    }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ color: "#fbbf24", fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
          Human Review Required
        </div>
        <div style={{ color: "#92400e", fontSize: 12 }}>
          Review the diff above. Approve to open a PR, or reject to discard.
        </div>
      </div>
      <div style={{ display: "flex", gap: 10 }}>
        <button
          onClick={() => decide("approve")}
          disabled={loading}
          style={{
            background: "#16a34a", color: "#fff", border: "none",
            borderRadius: 8, padding: "10px 24px", fontSize: 13,
            fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1, display: "flex", alignItems: "center", gap: 8,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          Approve — Open PR
        </button>
        <button
          onClick={() => decide("reject")}
          disabled={loading}
          style={{
            background: "transparent", color: "#f87171",
            border: "1px solid #7f1d1d",
            borderRadius: 8, padding: "10px 24px", fontSize: 13,
            fontWeight: 500, cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          Reject
        </button>
      </div>
    </div>
  )
}