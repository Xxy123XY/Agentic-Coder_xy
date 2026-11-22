import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { solveIssue } from "../lib/api"

export default function SolveIssueForm() {
  const [repo, setRepo] = useState("Iam-raunac/bug_test")
  const [issueNumber, setIssueNumber] = useState("1")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const job = await solveIssue(repo, issueNumber)
      navigate("/jobs/" + job.id)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    background: "#0a0a0f",
    border: "1px solid #1e293b",
    borderRadius: 8,
    padding: "10px 14px",
    color: "#f1f5f9",
    fontSize: 13,
    fontFamily: "ui-monospace, monospace",
    outline: "none",
    width: "100%",
    transition: "border-color 0.15s",
  }

  return (
    <div style={{
      background: "#0f0f17",
      border: "1px solid #1e293b",
      borderRadius: 12,
      padding: "20px 24px",
    }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", marginBottom: 4 }}>
          Solve a GitHub Issue
        </div>
        <div style={{ fontSize: 12, color: "#475569" }}>
          Paste a repo and issue number — the pipeline handles the rest.
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="owner/repo"
            value={repo}
            onChange={e => setRepo(e.target.value)}
            style={{ ...inputStyle, flex: "1 1 200px" }}
            onFocus={e => e.target.style.borderColor = "#6366f1"}
            onBlur={e => e.target.style.borderColor = "#1e293b"}
            required
          />
          <input
            type="number"
            placeholder="Issue #"
            value={issueNumber}
            onChange={e => setIssueNumber(e.target.value)}
            style={{ ...inputStyle, flex: "0 0 100px" }}
            onFocus={e => e.target.style.borderColor = "#6366f1"}
            onBlur={e => e.target.style.borderColor = "#1e293b"}
            required
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "#3730a3" : "#6366f1",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "10px 20px",
              fontSize: 13,
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              opacity: loading ? 0.7 : 1,
              transition: "background 0.15s",
              whiteSpace: "nowrap",
            }}
          >
            {loading ? (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth="2" style={{ animation: "spin 1s linear infinite" }}>
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
                Starting...
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5,3 19,12 5,21"/>
                </svg>
                Run Pipeline
              </>
            )}
          </button>
        </div>
        {error && (
          <div style={{
            marginTop: 10, padding: "8px 12px",
            background: "#2d0a0a", border: "1px solid #7f1d1d",
            borderRadius: 6, fontSize: 12, color: "#f87171",
          }}>
            {error}
          </div>
        )}
      </form>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
      `}</style>
    </div>
  )
}