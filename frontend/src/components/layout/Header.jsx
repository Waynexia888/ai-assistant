import { Icon } from "../common/Icon";

export function Header() {
  return (
    <header className="chat-header">
      <div className="chat-title-block">
        <div className="chat-title-line">
          <h1>What is an Agent and how does it work?</h1>
        </div>
        <p>The agent automatically selects the right tools and knowledge sources <Icon name="quote" /></p>
      </div>
      <nav>
        <button><Icon name="upload" /></button>
        <button><Icon name="star" /></button>
      </nav>
    </header>
  );
}
