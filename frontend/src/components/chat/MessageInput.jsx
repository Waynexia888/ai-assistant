import { Icon } from "../common/Icon";

export function MessageInput({
  inputValue = "",
  onInputChange = () => {},
  onSendMessage = () => {},
  disabled=false,
  placeholder="Type a message... (Shift + Enter for new line, Enter to send)",
}) {
  function handleKeyDown(e) {
    // Shift + Enter for new line, Enter to send
    if (e.key === "Enter" && e.shiftKey) {
      return; // Allow new line
    }
    
    // Enter to send
    if (e.key === "Enter") {
      e.preventDefault();
      if (!inputValue.trim() || disabled) {
        return;
      }
      onSendMessage();
    }
  }

  function handleSendClick() {
    if (!inputValue.trim() || disabled) {
      return;
    }
    onSendMessage();
  }

  return (
    <div className="composer">
      <textarea
        className="composer-input"
        value={inputValue}
        onChange={(e) => onInputChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={3}
      />
      <div className="composer-bottom">
        <div>
          <button type="button" disabled={disabled}>
            <Icon name="paperclip" />
          </button>
          <button type="button" disabled={disabled}>
            <Icon name="camera" />
          </button>
          <button type="button" disabled={disabled}>
            <Icon name="box" />
          </button>
        </div>
        <div>
          <button type="button" disabled={disabled}>
            <Icon name="image" />
          </button>
          <button 
            type="button"
            className="send"
            onClick={handleSendClick}
            disabled={!inputValue.trim() || disabled}
          >
            <Icon name="send" />
          </button>
        </div>
      </div>
    </div>
  );
}
