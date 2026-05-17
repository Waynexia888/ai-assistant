import { ChatWindow } from "../components/chat/ChatWindow";
import { MainLayout } from "../components/layout/MainLayout";

export function ChatPage() {
  return <MainLayout chat={<ChatWindow />} />;
}
