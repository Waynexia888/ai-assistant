import { Icon } from "../common/Icon";

export function Header() {
  return (
    <header className="chat-header">
      <div>
        <h1>What is an Agent and how does it work?</h1>
        <button><Icon name="pin" /></button>
      </div>
      <nav>
        <button><Icon name="upload" /></button>
        <button><Icon name="star" /></button>
        <button><Icon name="more" /></button>
      </nav>
    </header>
  );
}
