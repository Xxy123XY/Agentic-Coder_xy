import { useEffect, useState } from "react"
import { listJobs } from "../lib/api"
import SolveIssueForm from "../components/SolveIssueForm"
import JobCard from "../components/JobCard"

export default function Dashboard() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    try {
      const data = await listJobs()
      setJobs(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [])

  const counts = {
    running: jobs.filter(j => j.status === "running").length,
    awaiting: jobs.filter(j => j.status === "awaiting_review").length,
    completed: jobs.filter(j => j.status === "completed").length,
    failed: jobs.filter(j => j.status === "failed").length,
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[
          { label: "Running",  value: counts.running,   color: "#60a5fa" },
          { label: "Review",   value: counts.awaiting,  color: "#fbbf24" },
          { label: "Done",     value: counts.completed, color: "#4ade80" },
          { label: "Failed",   value: counts.failed,    color: "#f87171" },
        ].map(stat => (
          <div key={stat.label} style={{
            background: "#0f0f17",
            border: "1px solid #1e293b",
            borderRadius: 10,
            padding: "14px 16px",
          }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: stat.color, fontVariantNumeric: "tabular-nums" }}>
              {stat.value}
            </div>
            <div style={{ fontSize: 11, color: "#475569", marginTop: 2, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      <SolveIssueForm />

      {/* Jobs list */}
      <div>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginBottom: 12,
        }}>
          <span style={{ fontSize: 12, color: "#475569", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 }}>
            Recent Jobs
          </span>
          <button
            onClick={refresh}
            style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", padding: 4 }}
            title="Refresh"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "48px 0", color: "#475569", fontSize: 13 }}>
            Loading jobs...
          </div>
        ) : jobs.length === 0 ? (
          <div style={{
            border: "1px dashed #1e293b",
            borderRadius: 10, padding: "48px 0",
            textAlign: "center", color: "#475569", fontSize: 13,
          }}>
            No jobs yet. Run the pipeline above to get started.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {jobs.map(job => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}