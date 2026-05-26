import { Navigate, Route, Routes } from "react-router-dom";
import { AgentDashboard } from "./pages/AgentDashboard";
import { ImportHistoryPage } from "./pages/ImportHistoryPage";
import { KnowledgeBaseDetailPage } from "./pages/KnowledgeBaseDetailPage";
import { KnowledgeCenterPage } from "./pages/KnowledgeCenterPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<AgentDashboard />} />
      <Route path="/chat" element={<AgentDashboard />} />
      <Route path="/knowledge" element={<KnowledgeCenterPage />} />
      <Route path="/knowledge/:id" element={<KnowledgeBaseDetailPage />} />
      <Route path="/imports" element={<ImportHistoryPage />} />

      <Route path="/1" element={<Navigate to="/knowledge" replace />} />
      <Route path="/2" element={<Navigate to="/knowledge/default" replace />} />
      <Route path="/3" element={<Navigate to="/imports" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
