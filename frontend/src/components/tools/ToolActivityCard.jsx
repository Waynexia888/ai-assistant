import { Icon } from "../common/Icon";

export function ToolActivityCard({ log }) {
  return (
    <div className="log-row">
      <time>{log[0]}</time>
      <Icon name={log[1]} />
      <strong>{log[2]}</strong>
      <span>{log[3]}</span>
      <em><Icon name="check" /></em>
    </div>
  );
}
