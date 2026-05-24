import { Icon } from "../common/Icon";

export function ToolCallCard({ icon, label }) {
  return (
    <button className="tool-card">
      <span className="tool-icon">
        <Icon name={icon} />
      </span>
      <span>
        <strong>{label}</strong>
      </span>
    </button>
  );
}
