import { Icon } from "../common/Icon";

const sourceItems = [
  ["file", "Upload File"],
  ["globe", "Add URL"],
  ["source", "Paste Text"],
  ["link", "Connect GitHub"],
  ["knowledge", "Connect Notion"],
];

export function SourceDropdown() {
  return (
    <div className="source-picker">
      <button className="source-trigger"><Icon name="plus" />Add Source<span>⌄</span></button>
      <div className="source-menu">
        {sourceItems.map(([icon, item], index) => (
          <button className={index === 0 ? "active" : ""} key={item}><Icon name={icon} />{item}</button>
        ))}
      </div>
    </div>
  );
}
