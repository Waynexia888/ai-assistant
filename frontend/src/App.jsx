import { AgentDashboard } from "./pages/AgentDashboard";
import { ImportHistoryPage } from "./pages/ImportHistoryPage";
import { KnowledgeBaseDetailPage } from "./pages/KnowledgeBaseDetailPage";
import { KnowledgeCenterPage } from "./pages/KnowledgeCenterPage";

export function App() {
  if (window.location.pathname === "/1") {
    return <KnowledgeCenterPage />;
  }

  if (window.location.pathname === "/2") {
    return <KnowledgeBaseDetailPage />;
  }

  if (window.location.pathname === "/3") {
    return <ImportHistoryPage />;
  }

  return <AgentDashboard />;
}
