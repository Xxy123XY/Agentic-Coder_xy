import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { getJob } from "../lib/api"
import StatusBadge from "../components/StatusBadge"
import PipelineDag from "../components/PipelineDag"
import DiffViewer from "../components/DiffViewer"
import ApprovalPanel from "../components/ApprovalPanel"
import EventLog from "../components/EventLog"
import { formatDate, timeAgo } from "../lib/utils"

const SECTION = ({ title, children }) => (
  <div style={{ background: "#0f0f17", border: "1px solid #1e293b", borderRadius: 10, overflow: "hidden" }}>
    <div style={{
      padding: "12px 20px", borderBottom: "1px solid #1e293b",
      fontSize: 11, fontWeight: 600, color: "#475569",
      textTransform: "uppercase", letterSpacing: "0.08em",
    }}>
      {title}
    </div>
    <div style={{ padding: "16px 20px" }}>{children}</div>
  </div>
)

export default function JobDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    try {
      const data = await getJob(id)
      setJob(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 4000)
    return () => clearInterval(interval)
  }, [id])

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "64px 0", color: "#475569", fontSize: 13 }}>
        Loading job...
      </div>
    )
  }

  if (!job) {
    return (
      <div style={{ textAlign: "center", padding: "64px 0", color: "#f87171", fontSize: 13 }}>
        Job not found.
      </div>
    )
  }

  const events = (() => {
    try { return JSON.parse(job.relevant_files || "[]") } catch { return [] }
  })()

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Back + Header */}
      <div>
        <button
          onClick={() => navigate("/")}
          style={{
            background: "none", border: "none", color: "#475569",
            cursor: "pointer", fontSize: 12, padding: "0 0 12px",
            display: "flex", alignItems: "center", gap: 6,
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          All Jobs
        </button>

        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 18, fontWeight: 600, color: "#f1f5f9" }}>
              {job.repo_full_name}
              <span style={{ color: "#475569" }}>{" #" + job.issue_number}</span>
            </div>
            <div style={{ fontSize: 12, color: "#475569", marginTop: 4 }}>
              {"Created " + timeAgo(job.created_at) + " — " + formatDate(job.created_at)}
            </div>
          </div>
          <StatusBadge status={job.status} />
        </div>
      </div>

      {/* PR URL if completed */}
      {job.pr_url && (
        <div style={{
          background: "#052e16", border: "1px solid #16a34a",
          borderRadius: 10, padding: "14px 20px",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ color: "#4ade80", fontSize: 13, fontWeight: 500 }}>
            Pull Request opened successfully
          </div>
          <a
            href={job.pr_url}
            target="_blank"
            rel="noreferrer"
            style={{
              color: "#4ade80", fontSize: 12,
              display: "flex", alignItems: "center", gap: 6,
              textDecoration: "none",
            }}
            onMouseEnter={e => e.currentTarget.style.textDecoration = "underline"}
            onMouseLeave={e => e.currentTarget.style.textDecoration = "none"}
          >
            {job.pr_url}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15,3 21,3 21,9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>
        </div>
      )}

      {/* Error */}
      {job.error_message && (
        <div style={{
          background: "#2d0a0a", border: "1px solid #7f1d1d",
          borderRadius: 10, padding: "14px 20px",
          color: "#f87171", fontSize: 13,
        }}>
          <strong>Error:</strong> {job.error_message}
        </div>
      )}

      {/* Approval panel */}
      {job.status === "awaiting_review" && (
        <ApprovalPanel jobId={job.id} onDecision={refresh} />
      )}

      {/* Pipeline DAG */}
      <SECTION title="Pipeline">
        <PipelineDag status={job.status} events={events} />
      </SECTION>

      {/* Proposed diff */}
      {job.proposed_diff && (
        <SECTION title="Proposed Fix (diff)">
          <DiffViewer diff={job.proposed_diff} />
        </SECTION>
      )}

      {/* Test code */}
      {job.test_code && (
        <SECTION title="Generated Tests">
          <pre style={{
            background: "#080810", borderRadius: 8,
            padding: "16px", overflow: "auto", maxHeight: 300,
            fontFamily: "ui-monospace, monospace", fontSize: 12,
            color: "#94a3b8", lineHeight: 1.6, margin: 0,
          }}>
            {job.test_code}
          </pre>
        </SECTION>
      )}

      {/* Meta */}
      <SECTION title="Details">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12 }}>
          {[
            ["Job ID",      job.id],
            ["Status",      job.status],
            ["Retry count", job.retry_count || 0],
            ["Issue URL",   job.issue_url],
          ].map(([label, value]) => (
            <div key={label}>
              <div style={{ color: "#475569", marginBottom: 2 }}>{label}</div>
              <div style={{ color: "#94a3b8", fontFamily: "ui-monospace, monospace", wordBreak: "break-all" }}>
                {value || "—"}
              </div>
            </div>
          ))}
        </div>
      </SECTION>

    </div>
  )
}