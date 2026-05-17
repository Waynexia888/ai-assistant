import { Icon } from "../common/Icon";

export function ToolCallCard({ icon, label }) {
  return (
    <button className="tool-card">
      <Icon name={icon} />
      <span>{label}</span>
    </button>
  );
}
