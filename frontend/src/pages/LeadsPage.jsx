import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { fetchLeadJobs, fetchJobLeads } from "../api";

export default function LeadsPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(jobId || "");
  const [leads, setLeads] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchLeadJobs()
      .then((j) => {
        setJobs(j);
        if (!selectedJobId && j.length > 0) setSelectedJobId(j[0].job_id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedJobId) return;
    setError("");
    setLeads(null);
    fetchJobLeads(selectedJobId)
      .then((data) => setLeads(data.leads))
      .catch((e) => setError(e.message));
  }, [selectedJobId]);

  return (
    <div className="card wide-card">
      <h1>Step 2 — Review Leads</h1>
      <p className="subtitle">Pick a scrape batch to use for the campaign.</p>

      {error && <div className="error">{error}</div>}

      {jobs.length === 0 && !error && (
        <p className="empty-note">
          No scraped leads yet — go back to Step 1 and run a scrape first.
        </p>
      )}

      {jobs.length > 0 && (
        <div className="field">
          <label>Scrape batch</label>
          <select value={selectedJobId} onChange={(e) => setSelectedJobId(e.target.value)}>
            {jobs.map((j) => (
              <option key={j.job_id} value={j.job_id}>
                {j.platform} — {j.city} — {j.count} leads
                {j.scraped_at ? ` — ${new Date(j.scraped_at).toLocaleString()}` : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {leads && (
        <>
          <div className="leads-table-wrap">
            <table className="leads-table">
              <thead>
                <tr>
                  <th>Seller</th>
                  <th>Contact</th>
                  <th>Platform</th>
                  <th>City</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l, i) => (
                  <tr key={i}>
                    <td>{l.seller_name || "—"}</td>
                    <td>{l.contact || "—"}</td>
                    <td>{l.platform}</td>
                    <td>{l.city}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="button-row">
            <Link className="btn-secondary" to="/">← Back to Scrape</Link>
            <button
              className="btn-primary"
              onClick={() => navigate(`/launch/${selectedJobId}`)}
              disabled={leads.length === 0}
            >
              Launch Campaign →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
