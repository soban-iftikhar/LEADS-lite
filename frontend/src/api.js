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

// ---- leads (step 2) ----

export async function fetchLeadJobs() {
  const res = await fetch(`${API_BASE}/leads/jobs`);
  if (!res.ok) throw new Error("Failed to load past scrape jobs");
  const data = await res.json();
  return data.jobs;
}

export async function fetchJobLeads(jobId) {
  const res = await fetch(`${API_BASE}/leads/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to load leads for this job");
  return res.json();
}

// ---- campaigns (step 3 + 4) ----

export async function fetchTemplatePreview() {
  const res = await fetch(`${API_BASE}/campaigns/template-preview`);
  if (!res.ok) throw new Error("Failed to load template preview");
  return res.json();
}

export async function createCampaign(jobId) {
  const res = await fetch(`${API_BASE}/campaigns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create campaign");
  }
  return res.json();
}

export async function launchCampaign(campaignId) {
  const res = await fetch(`${API_BASE}/campaigns/${campaignId}/launch`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to launch campaign");
  }
  return res.json();
}

export async function fetchCampaignStatus(campaignId) {
  const res = await fetch(`${API_BASE}/campaigns/${campaignId}/status`);
  if (!res.ok) throw new Error("Failed to load campaign status");
  return res.json();
}

export async function fetchCampaignMessages(campaignId) {
  const res = await fetch(`${API_BASE}/campaigns/${campaignId}/messages`);
  if (!res.ok) throw new Error("Failed to load campaign messages");
  const data = await res.json();
  return data.messages;
}

export function connectCampaignSocket(campaignId, onUpdate) {
  const ws = new WebSocket(`${WS_BASE}/ws/campaigns/${campaignId}`);
  ws.onmessage = (event) => {
    onUpdate(JSON.parse(event.data));
  };
  return ws;
}
