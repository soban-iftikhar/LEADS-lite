import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { fetchTemplatePreview, createCampaign, launchCampaign } from "../api";

export default function LaunchPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [preview, setPreview] = useState("");
  const [campaign, setCampaign] = useState(null);
  const [error, setError] = useState("");
  const [launching, setLaunching] = useState(false);

  useEffect(() => {
    fetchTemplatePreview()
      .then((d) => setPreview(d.body_preview))
      .catch((e) => setError(e.message));
  }, []);

  const handleCreate = async () => {
    setError("");
    try {
      const result = await createCampaign(jobId);
      setCampaign(result);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleLaunch = async () => {
    if (!campaign) return;
    setError("");
    setLaunching(true);
    try {
      await launchCampaign(campaign.campaign_id);
      navigate(`/stats/${campaign.campaign_id}`);
    } catch (e) {
      setError(e.message);
      setLaunching(false);
    }
  };

  return (
    <div className="card">
      <h1>Step 3 — Launch Campaign</h1>
      <p className="subtitle">Preview the template, then send.</p>

      {error && <div className="error">{error}</div>}

      <div className="field">
        <label>Message preview</label>
        <div className="template-preview">{preview.replace("{seller_name}", "Ahmed")}</div>
      </div>

      {!campaign ? (
        <button className="btn-primary" onClick={handleCreate}>
          Prepare Campaign
        </button>
      ) : (
        <div className="campaign-summary">
          <p>
            <strong>{campaign.total}</strong> leads ready to message.
          </p>
          <div className="button-row">
            <Link className="btn-secondary" to={`/leads/${jobId}`}>← Back to Leads</Link>
            <button className="btn-primary" onClick={handleLaunch} disabled={launching}>
              {launching ? "Launching…" : "Send Campaign →"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
