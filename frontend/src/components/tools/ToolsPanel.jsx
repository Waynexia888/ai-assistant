import { tools } from "../../data/dashboardData";
import { Icon } from "../common/Icon";
import { ToolActivityCard } from "./ToolActivityCard";
import { ToolCallCard } from "./ToolCallCard";

const executionLogs = [
  ["14:28", "source", "View Sources", "Opened 3 sources"],
  ["14:25", "calendar", "Calendar", "Meeting with John tomorrow"],
  ["14:20", "knowledge", "Knowledge", "AI Agent definitions"],
];

export function ToolsPanel({ isWorkspaceOpen = false, onCloseWorkspace = () => {} }) {
  return (
    <aside className={`tools-panel ${isWorkspaceOpen ? "is-open" : ""}`}>
      <div className="workspace-head">
        <h2>Agent Workspace</h2>
        <button className="workspace-settings" type="button" aria-label="Settings"><Icon name="gear" /></button>
        <button className="workspace-close" type="button" aria-label="Close workspace" onClick={onCloseWorkspace}><Icon name="close" /></button>
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
        <div className="execution-head">
          <h3>Recent Activity</h3>
        </div>
        {executionLogs.map((row) => <ToolActivityCard log={row} key={row.join("")} />)}
        <a className="activity-link">View all activity →</a>
      </section>
    </aside>
  );
}
