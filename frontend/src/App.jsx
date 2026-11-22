import { BrowserRouter, Routes, Route, Link } from "react-router-dom"
import Dashboard from "./pages/Dashboard"
import JobDetail from "./pages/JobDetail"

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <header style={{
          borderBottom: "1px solid #1e293b",
          background: "#0f0f17",
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}>
          <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 700, color: "#fff",
            }}>M</div>
            <div>
              <div style={{ fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.02em" }}>
                Multi-Agent Orchestrator
              </div>
              <div style={{ fontSize: 11, color: "#64748b", marginTop: 1 }}>
                Autonomous GitHub issue resolution
              </div>
            </div>
          </Link>
        </header>

        <main style={{ flex: 1, maxWidth: 900, margin: "0 auto", width: "100%", padding: "32px 24px" }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/jobs/:id" element={<JobDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}