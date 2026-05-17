import { tools } from "../../data/dashboardData";
import { Icon } from "../common/Icon";
import { ToolActivityCard } from "./ToolActivityCard";
import { ToolCallCard } from "./ToolCallCard";

const executionLogs = [
  ["14:28", "Web Search", "Latest AI Agent research"],
  ["14:25", "Calendar", "Meeting with John (tomorrow 3 PM)"],
  ["14:20", "Knowledge", "AI Agent definitions"],
];

export function ToolsPanel() {
  return (
    <aside className="tools-panel">
      <div className="tools-title">
        <h2>Agent Tools</h2>
        <button><Icon name="gear" /></button>
      </div>
      {tools.map((group) => (
        <section className="tool-section" key={group.title}>
          <h3>{group.title}</h3>
          <div className="tool-grid">
            {group.items.map(([icon, label]) => (
              <ToolCallCard icon={icon} label={label} key={label} />
            ))}
          </div>
        </section>
      ))}
      <section className="execution">
        <h3>Tool Activity</h3>
        {executionLogs.map((row) => <ToolActivityCard log={row} key={row.join("")} />)}
        <a>View all activity <span>→</span></a>
      </section>
    </aside>
  );
}
