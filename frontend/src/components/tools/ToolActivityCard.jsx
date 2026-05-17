export function ToolActivityCard({ log }) {
  return (
    <div className="log-row">
      <time>{log[0]}</time>
      <strong>{log[1]}</strong>
      <span>{log[2]}</span>
      <em>Done</em>
    </div>
  );
}
