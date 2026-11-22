export function cn(...classes) {
  return classes.filter(Boolean).join(" ")
}

export function formatDate(dateStr) {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleString()
}

export function timeAgo(dateStr) {
  if (!dateStr) return ""
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}