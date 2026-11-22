import { useEffect, useRef, useState } from "react"

export function useJobEvents(jobId) {
  const [events, setEvents] = useState([])
  const ws = useRef(null)

  useEffect(() => {
    if (!jobId) return

    const url = `${import.meta.env.VITE_WS_URL}/ws/jobs/${jobId}`
    ws.current = new WebSocket(url)

    ws.current.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        setEvents(prev => [...prev, event])
      } catch (_) {}
    }

    ws.current.onerror = () => console.warn("WS error", jobId)

    return () => ws.current?.close()
  }, [jobId])

  return events
}