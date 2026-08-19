import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCities, startScrape, connectJobSocket, cancelScrape, exportUrl } from "../api";

const PLATFORMS = [
  { value: "zameen", label: "Zameen.com" },
  { value: "olx", label: "OLX Pakistan" },
];

function formatTime(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}m ${s}s`;
}

export default function ScrapePage() {
  const [cities, setCities] = useState([]);
  const [platform, setPlatform] = useState("zameen");
  const [city, setCity] = useState("");
  const [count, setCount] = useState(50);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const wsRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCities()
      .then((c) => {
        setCities(c);
        setCity(c[0] || "");
      })
      .catch(() => setError("Could not reach backend. Is it running on port 8000?"));
  }, []);

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  const handleStart = async () => {
    setError("");
    try {
      const { job_id } = await startScrape(platform, city, Number(count));
      setJob({
        job_id,
        platform,
        city,
        limit: Number(count),
        count: 0,
        status: "running",
        elapsed_seconds: 0,
      });
      wsRef.current?.close();
      wsRef.current = connectJobSocket(job_id, (state) => setJob(state));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleCancel = () => {
    if (job) cancelScrape(job.job_id);
  };

  const isRunning = job?.status === "running";
  const isDone = job && job.status !== "running";
  const progressPct = job ? Math.min(100, Math.round((job.count / job.limit) * 100)) : 0;

  return (
    <div className="card">
      <h1>Step 1 — Scrape Leads</h1>
      <p className="subtitle">Pull seller name + contact from one platform, fast.</p>

      {error && <div className="error">{error}</div>}

      <div className="field">
        <label>Platform</label>
        <select value={platform} onChange={(e) => setPlatform(e.target.value)} disabled={isRunning}>
          {PLATFORMS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>City</label>
        <select value={city} onChange={(e) => setCity(e.target.value)} disabled={isRunning}>
          {cities.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label>Number of leads</label>
        <input
          type="number"
          min="1"
          max="500"
          value={count}
          onChange={(e) => setCount(e.target.value)}
          disabled={isRunning}
        />
      </div>

      {!job || isDone ? (
        <button className="btn-primary" onClick={handleStart} disabled={!city}>
          Start Scraping
        </button>
      ) : (
        <button className="btn-secondary" onClick={handleCancel}>
          Stop
        </button>
      )}

      {job && (
        <div className="progress-section">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <div className="progress-meta">
            <span>{job.count} / {job.limit} leads</span>
            <span>{formatTime(job.elapsed_seconds)}</span>
          </div>
          <div className={`status-badge status-${job.status}`}>{job.status}</div>

          {isDone && job.count > 0 && (
            <div className="button-row">
              <a className="btn-secondary" href={exportUrl(job.job_id)}>
                Export CSV
              </a>
              <button className="btn-primary" onClick={() => navigate(`/leads/${job.job_id}`)}>
                Review Leads →
              </button>
            </div>
          )}
          {isDone && job.status !== "crashed" && job.count === 0 && (
            <p className="empty-note">No leads collected — check backend logs for this job.</p>
          )}

          {job.status === "crashed" && (
            <div className="crash-box">
              <p className="crash-title">Scraper crashed before finishing.</p>
              {job.log_tail && <pre className="crash-log">{job.log_tail}</pre>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
