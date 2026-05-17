import { ChatWindow } from "../components/chat/ChatWindow";
import { MainLayout } from "../components/layout/MainLayout";
import { ToolsPanel } from "../components/tools/ToolsPanel";
import { KnowledgeWorkspace } from "../components/rag/KnowledgeWorkspace";

export function AgentDashboard() {
  return (
    <MainLayout
      chat={<ChatWindow />}
      tools={<ToolsPanel />}
      workspace={<KnowledgeWorkspace />}
    />
  );
}
