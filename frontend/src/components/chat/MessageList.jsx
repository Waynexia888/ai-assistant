import { useEffect, useRef } from "react";
import { Icon } from "../common/Icon";

function formatMessageTime(createdAt) {
  if (!createdAt) {
    return "";
  }

  return new Date(createdAt).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
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

      <article className={`answer-card ${message.isError ? "error" : ""}`}>
        <p>{message.content}</p>

        <time>{formatMessageTime(message.createdAt)}</time>

        <div className="answer-actions">
          <button type="button">
            <Icon name="source" />
            View Sources
            <span>{message.sources?.length || 0}</span>
          </button>

          <button type="button">
            <Icon name="search" />
            Search References
          </button>

          <button type="button">
            <Icon name="link" />
            Create Mind Map
          </button>

          <button type="button" className="icon-only">
            <Icon name="thumbs" />
          </button>

          <button type="button" className="icon-only">
            <Icon name="dislike" />
          </button>
        </div>
      </article>
    </div>
  );
}

export function MessageList({ messages = [], loading = false }) {
  const listRef = useRef(null);

  useEffect(() => {
    const list = listRef.current;

    if (!list) {
      return;
    }

    list.scrollTop = list.scrollHeight;
  }, [messages, loading]);

  return (
    <section className="messages" ref={listRef}>
      {messages.map((message) => {
        if (message.role === "user") {
          return <UserMessage key={message.id} message={message} />;
        }
        return <AssistantMessage key={message.id} message={message} />;
      })}

      {loading && (
        <div className="assistant-row loading-row">
          <div className="assistant-avatar">
            <Icon name="bot" />
          </div>

          <article className="answer-card loading-card">
            <p>Thinking...</p>
          </article>
        </div>
      )}
    </section>
  );
}
