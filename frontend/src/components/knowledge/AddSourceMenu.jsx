import { Icon } from "../common/Icon";

const sourceItems = [
  ["file", "Upload File"],
  ["globe", "Add URL"],
  ["source", "Paste Text"],
  ["link", "Connect GitHub"],
  ["knowledge", "Connect Notion"],
];

export function AddSourceMenu({ compact = false }) {
  return (
    <div className={`kb-source ${compact ? "compact" : ""}`}>
      <button className="kb-source-trigger" type="button"><Icon name="plus" />Add Source<span>⌄</span></button>
      {!compact && (
        <div className="kb-source-menu">
          {sourceItems.map(([icon, label], index) => (
            <button className={index === 0 ? "active" : ""} type="button" key={label}>
              <Icon name={icon} />{label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
