import { useEffect, useState } from "react";
import { fetchChatMessages, sendChatMessage } from "../../api/chatApi";
import { Header } from "../layout/Header";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

const CURRENT_SESSION_ID_KEY = "currentSessionId";

export function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedSessionId = localStorage.getItem(CURRENT_SESSION_ID_KEY);

    if (!savedSessionId) {
      return;
    }

    async function restoreCurrentSession() {
      try {
        const result = await fetchChatMessages(savedSessionId);

        if (!result.success) {
          throw new Error(result.message || "Unable to restore chat session.");
        }

        setSessionId(savedSessionId);
        setMessages(result.data ?? []);
      } catch (restoreError) {
        localStorage.removeItem(CURRENT_SESSION_ID_KEY);
        setSessionId("");

        const status = restoreError.response?.status;
        if (status && status !== 404) {
          setError(
            restoreError.response?.data?.message
              || restoreError.message
              || "Unable to restore chat session."
          );
        }
      }
    }

    restoreCurrentSession();
  }, []);

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

      const returnedSessionId = responseData.sessionId ?? sessionId;

      if (returnedSessionId) {
        setSessionId(returnedSessionId);
        localStorage.setItem(CURRENT_SESSION_ID_KEY, returnedSessionId);
      }

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
