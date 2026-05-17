import { useState } from "react";

import { Header } from "../layout/Header";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import {createUserMessage, createAssistantMessage} from "../../utils/messageUtils";

import {sendChatMessage} from "../../api/chatApi";

export function ChatWindow() {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState("default"); 

  async function handleSendMessage() {
    const text = inputValue.trim();
    if (!text || loading) {
      return;
    }

    const userMessage = createUserMessage(text);

    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInputValue("");
    setLoading(true);

    try {
      const aiResponse = await sendChatMessage(text, sessionId);
      const assistantMessage = createAssistantMessage(aiResponse);

      setMessages((prevMessages) => [...prevMessages, assistantMessage]);
    } catch (error) {
      console.error("Failed to send chat message:", error);

      const errorMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "Sorry, something went wrong. Please check your backend server and try again.",
        createdAt: new Date().toISOString(),
        isError: true,
      };

      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="chat-panel">
      <Header />
      <MessageList messages={messages} loading={loading} />
      <MessageInput
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSendMessage={handleSendMessage}
        disabled={loading}
      />
    </main>
  );
}
