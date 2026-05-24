import { Header } from "../layout/Header";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function ChatWindow() {
  return (
    <main className="chat-panel">
      <Header />
      <MessageList />
      <MessageInput />
    </main>
  );
}
