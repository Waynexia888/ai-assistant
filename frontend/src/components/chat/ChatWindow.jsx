import { useState } from "react";
import { sendChatMessage } from "../../api/chatApi";
import { Header } from "../layout/Header";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [sessionId, setSessionId] = useState("default");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  async function handleSendMessage() {
    const message = inputValue.trim();

    if (!message || isSending) {
      return;
    }

    const sentAt = new Date().toISOString();
    setInputValue("");
    setError("");
    setIsSending(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        createdAt: sentAt,
      },
    ]);

    try {
      const result = await sendChatMessage({ sessionId, message });
      const responseData = result.data ?? {};
      const answer = responseData.answer ?? "";

      if (!result.success) {
        throw new Error(result.message || "Chat request failed.");
      }

      setSessionId(responseData.sessionId ?? sessionId);
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: answer || "No answer returned.",
          createdAt: new Date().toISOString(),
        },
      ]);
    } catch (requestError) {
      const nextError = requestError.response?.data?.message
        || requestError.message
        || "Unable to send message.";

      setError(nextError);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="chat-panel">
      <Header />
      <MessageList messages={messages} isLoading={isSending} error={error} />
      <MessageInput
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSendMessage={handleSendMessage}
        disabled={isSending}
      />
    </main>
  );
}
