import { Icon } from "../common/Icon";

export function KnowledgeShell({ children, active = "bases" }) {
  return (
    <div className="knowledge-app">
      <aside className="knowledge-sidebar">
        <div className="knowledge-brand">
          <span>{active === "imports" ? <Icon name="knowledge" /> : "K"}</span>
          <strong>Knowledge Center</strong>
        </div>
        <nav className="knowledge-nav">
          <button className={active === "bases" ? "active" : ""} type="button"><Icon name="folder" />Knowledge Bases</button>
          <button className={active === "imports" ? "active" : ""} type="button"><Icon name="clock" />Import History</button>
        </nav>
        {active === "imports" ? (
          <button className="knowledge-help" type="button"><Icon name="help" />Help</button>
        ) : (
          <div className="knowledge-account">
            <span>AD</span>
            <strong>Acme Docs</strong>
            <b>⌄</b>
          </div>
        )}
      </aside>
      <main className="knowledge-main">{children}</main>
    </div>
  );
}
