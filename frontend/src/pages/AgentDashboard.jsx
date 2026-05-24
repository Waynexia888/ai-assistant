import { ChatWindow } from "../components/chat/ChatWindow";
import { MainLayout } from "../components/layout/MainLayout";
import { ToolsPanel } from "../components/tools/ToolsPanel";

export function AgentDashboard() {
  return (
    <MainLayout
      chat={<ChatWindow />}
      tools={<ToolsPanel />}
    />
  );
}
