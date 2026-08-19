import { useLocation } from "react-router-dom";

const STEPS = [
  { match: (p) => p === "/", label: "1. Scrape" },
  { match: (p) => p.startsWith("/leads"), label: "2. Review Leads" },
  { match: (p) => p.startsWith("/launch"), label: "3. Launch Campaign" },
  { match: (p) => p.startsWith("/stats"), label: "4. Stats" },
];

export default function StepNav() {
  const location = useLocation();
  const activeIndex = STEPS.findIndex((s) => s.match(location.pathname));

  return (
    <div className="step-nav">
      {STEPS.map((step, i) => (
        <div
          key={step.label}
          className={`step-nav-item ${i === activeIndex ? "step-nav-active" : ""} ${i < activeIndex ? "step-nav-done" : ""}`}
        >
          {step.label}
        </div>
      ))}
    </div>
  );
}
