import { Icon } from "../common/Icon";

function UserMessage() {
  return (
    <div className="user-msg">
      <div className="bubble">Do you know about aliens? Do you think they really exist?</div>
      <img src="https://i.pravatar.cc/80?img=12" alt="User avatar" />
      <time>09:21</time>
    </div>
  );
}

function AssistantMessage() {
  return (
    <div className="assistant-row">
      <div className="assistant-avatar">
        <Icon name="bot" />
      </div>

      <article className="answer-card">
        <p>The question of whether aliens exist has long been a lively topic in science and public discussion. There is no definitive direct evidence for extraterrestrial life yet, but the size and diversity of the universe make many scientists consider it plausible.</p>

        <ul>
          <li><strong>Exploration:</strong> Researchers look for signs of life by studying Mars, icy moons such as Europa and Titan, and possible radio signals from distant systems.</li>
          <li><strong>No direct proof yet:</strong> Discoveries such as exoplanets and atmospheric biosignature candidates are exciting, but none proves life beyond Earth.</li>
          <li><strong>Future potential:</strong> As instruments improve, new observations may give us a clearer answer.</li>
        </ul>

        <p>What do you think about the possibility of life beyond Earth?</p>

        <time>09:21</time>

        <div className="answer-actions">
          <div className="source-summary">
            <span>Sources used</span>
            <b>·</b>
            <strong>3</strong>
            <button type="button">View sources</button>
          </div>

          <div className="answer-icon-row">
            <button type="button" aria-label="Copy response"><Icon name="copy" /></button>
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

export function MessageList() {
  return (
    <section className="messages">
      <UserMessage />
      <AssistantMessage />
    </section>
  );
}
