import { BrowserRouter, Routes, Route } from "react-router-dom";
import StepNav from "./components/StepNav";
import ScrapePage from "./pages/ScrapePage";
import LeadsPage from "./pages/LeadsPage";
import LaunchPage from "./pages/LaunchPage";
import StatsPage from "./pages/StatsPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="page">
        <StepNav />
        <Routes>
          <Route path="/" element={<ScrapePage />} />
          <Route path="/leads/:jobId?" element={<LeadsPage />} />
          <Route path="/launch/:jobId" element={<LaunchPage />} />
          <Route path="/stats/:campaignId" element={<StatsPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
