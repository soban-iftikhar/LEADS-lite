const API_BASE = "http://127.0.0.1:8000/api";
const WS_BASE = "ws://127.0.0.1:8000/api";

export async function fetchCities() {
  const res = await fetch(`${API_BASE}/cities`);
  const data = await res.json();
  return data.cities;
}

export async function startScrape(platform, city, count) {
  const res = await fetch(`${API_BASE}/scrape/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform, city, count }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start scrape");
  }
  return res.json();
}

export function connectJobSocket(jobId, onUpdate) {
  const ws = new WebSocket(`${WS_BASE}/ws/jobs/${jobId}`);
  ws.onmessage = (event) => {
    onUpdate(JSON.parse(event.data));
  };
  return ws;
}

export function cancelScrape(jobId) {
  return fetch(`${API_BASE}/scrape/${jobId}/cancel`, { method: "POST" });
}

export function exportUrl(jobId) {
  return `${API_BASE}/scrape/${jobId}/export`;
}
