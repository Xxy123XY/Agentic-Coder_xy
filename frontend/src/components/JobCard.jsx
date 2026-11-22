import { useNavigate } from "react-router-dom"
import StatusBadge from "./StatusBadge"
import { timeAgo } from "../lib/utils"

export default function JobCard({ job }) {
  const navigate = useNavigate()

  return (
    <div
      onClick={() => navigate("/jobs/" + job.id)}
      style={{
        background: "#0f0f17",
        border: "1px solid #1e293b",
        borderRadius: 10,
        padding: "16px 20px",
        cursor: "pointer",
        transition: "border-color 0.15s",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 12,
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "#334155"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "#1e293b"}
    >
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 13, color: "#f1f5f9" }}>
          {job.repo_full_name}
          <span style={{ color: "#475569", marginLeft: 6 }}>{"#" + job.issue_number}</span>
        </div>
        <div style={{ fontSize: 12, color: "#475569", marginTop: 4 }}>
          {"Created " + timeAgo(job.created_at)}
          {job.retry_count > 0 && (
            <span style={{ color: "#f59e0b", marginLeft: 8 }}>
              {job.retry_count + " retries"}
            </span>
          )}
        </div>
        {job.pr_url && (
          <a
            href={job.pr_url}
            target="_blank"
            rel="noreferrer"
            onClick={function(e) { e.stopPropagation() }}
            style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              marginTop: 8, fontSize: 12, color: "#818cf8",
              textDecoration: "none",
            }}
            onMouseEnter={e => e.currentTarget.style.textDecoration = "underline"}
            onMouseLeave={e => e.currentTarget.style.textDecoration = "none"}
          >
            View PR
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15,3 21,3 21,9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>
        )}
      </div>
      <StatusBadge status={job.status} />
    </div>
  )
}