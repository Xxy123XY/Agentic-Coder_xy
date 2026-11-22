import axios from "axios"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL + "/api/v1",
  headers: { "Content-Type": "application/json" },
})

// Trigger pipeline for a GitHub issue
export const solveIssue = (repoFullName, issueNumber) =>
  api.post("/issues/solve", {
    repo_full_name: repoFullName,
    issue_number: Number(issueNumber),
  }).then(r => r.data)

// List all jobs
export const listJobs = () =>
  api.get("/jobs").then(r => r.data)

// Get single job detail
export const getJob = (jobId) =>
  api.get(`/jobs/${jobId}`).then(r => r.data)

// Approve or reject a paused job
export const approveJob = (jobId, decision) =>
  api.post(`/jobs/${jobId}/approve`, {
    job_id: jobId,
    decision,
  }).then(r => r.data)