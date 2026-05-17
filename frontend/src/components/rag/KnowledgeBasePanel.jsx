import { knowledgeBases } from "../../data/dashboardData";
import { Icon } from "../common/Icon";
import { SourceDropdown } from "./SourceDropdown";

export function KnowledgeBasePanel() {
  return (
    <section className="knowledge-panel">
      <div className="panel-head">
        <h3>Knowledge Base</h3>
        <SourceDropdown />
      </div>
      <div className="kb-layout">
        <div className="kb-list">
          <span>Knowledge Bases</span>
          {knowledgeBases.map(([name, desc, count], index) => (
            <div className={`kb-item ${index === 0 ? "active" : ""}`} key={name}>
              <Icon name="folder" />
              <div><strong>{name}</strong><small>{desc}</small></div>
              {count && <b>{count}</b>}
              {count && <i>↻</i>}
            </div>
          ))}
          <footer>Total 4 bases <strong>960 files</strong></footer>
        </div>
      </div>
    </section>
  );
}
