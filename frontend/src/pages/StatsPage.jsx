import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { connectCampaignSocket, fetchCampaignMessages } from "../api";

const STATUS_LABELS = [
  { key: "sent", label: "Sent" },
  { key: "delivered", label: "Delivered" },
  { key: "read", label: "Seen" },
  { key: "failed", label: "Failed" },
  { key: "skipped", label: "Skipped" },
  { key: "queued", label: "Queued" },
];

export default function StatsPage() {
  const { campaignId } = useParams();
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const wsRef = useRef(null);

  useEffect(() => {
    wsRef.current = connectCampaignSocket(campaignId, setStatus);
    return () => wsRef.current?.close();
  }, [campaignId]);

  useEffect(() => {
    if (status?.status === "completed") {
      fetchCampaignMessages(campaignId).then(setMessages).catch((e) => setError(e.message));
    }
  }, [status?.status, campaignId]);

  if (!status) {
    return (
      <div className="card">
        <h1>Step 4 — Campaign Stats</h1>
        <p className="subtitle">Connecting…</p>
      </div>
    );
  }

  const { counts, total } = status;

  return (
    <div className="card wide-card">
      <h1>Step 4 — Campaign Stats</h1>

      {error && <div className="error">{error}</div>}

      <div className={`status-badge status-${status.status}`}>{status.status}</div>

      <div className="stats-grid">
        {STATUS_LABELS.map(({ key, label }) => (
          <div className="stat-box" key={key}>
            <div className="stat-value">{counts[key] || 0}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
        <div className="stat-box stat-total">
          <div className="stat-value">{total}</div>
          <div className="stat-label">Total</div>
        </div>
      </div>

      {status.status === "completed" && messages.length > 0 && (
        <div className="leads-table-wrap">
          <table className="leads-table">
            <thead>
              <tr>
                <th>Seller</th>
                <th>Contact</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {messages.map((m, i) => (
                <tr key={i}>
                  <td>{m.seller_name || "—"}</td>
                  <td>{m.contact || "—"}</td>
                  <td>
                    <span className={`status-pill status-pill-${m.status}`}>{m.status}</span>
                    {m.error && <span className="pill-error"> — {m.error}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="button-row">
        <Link className="btn-secondary" to="/">Start a New Scrape</Link>
      </div>
    </div>
  );
}
