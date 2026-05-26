import { useEffect, useRef } from "react";
import { Icon } from "../common/Icon";

function formatMessageTime(createdAt) {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(createdAt));
}

function UserMessage({ message }) {
  return (
    <div className="user-msg">
      <div className="bubble">{message.content}</div>
      <img src="https://i.pravatar.cc/80?img=12" alt="User avatar" />
      <time>{formatMessageTime(message.createdAt)}</time>
    </div>
  );
}

function AssistantMessage({ message }) {
  return (
    <div className="assistant-row">
      <div className="assistant-avatar">
        <Icon name="bot" />
      </div>

      <article className="answer-card">
        <p>{message.content}</p>
        <time>{formatMessageTime(message.createdAt)}</time>

        <div className="answer-actions">
          <div className="answer-icon-row">
            <button
              type="button"
              aria-label="Copy response"
              onClick={() => navigator.clipboard?.writeText(message.content)}
            >
              <Icon name="copy" />
            </button>
            <button type="button" aria-label="Like response"><Icon name="thumbs" /></button>
            <button type="button" aria-label="Dislike response"><Icon name="dislike" /></button>
            <button type="button" aria-label="Share response"><Icon name="upload" /></button>
            <button type="button" aria-label="Regenerate response"><Icon name="refresh" /></button>
            <button type="button" aria-label="More response actions"><Icon name="more" /></button>
          </div>
        </div>
      </article>
    </div>
  );
}

function LoadingMessage() {
  return (
    <div className="assistant-row loading-row">
      <div className="assistant-avatar">
        <Icon name="bot" />
      </div>
      <article className="answer-card loading-card">
        <p>Thinking...</p>
      </article>
    </div>
  );
}

export function MessageList({ messages = [], isLoading = false, error = "" }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading, error]);

  return (
    <section className="messages">
      {messages.length === 0 && !isLoading && (
        <div className="empty-chat">
          <div className="assistant-avatar">
            <Icon name="bot" />
          </div>
          <div>
            <strong>Start a conversation</strong>
            <p>Send a message to get a response from the assistant.</p>
          </div>
        </div>
      )}

      {messages.map((message) => (
        message.role === "user"
          ? <UserMessage key={message.id} message={message} />
          : <AssistantMessage key={message.id} message={message} />
      ))}

      {isLoading && <LoadingMessage />}

      {error && (
        <div className="chat-error" role="alert">
          {error}
        </div>
      )}

      <div ref={bottomRef} />
    </section>
  );
}
