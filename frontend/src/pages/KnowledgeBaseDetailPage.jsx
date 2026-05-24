import { AddSourceMenu } from "../components/knowledge/AddSourceMenu";
import { KnowledgeShell } from "../components/knowledge/KnowledgeShell";
import { Icon } from "../components/common/Icon";

const sources = [
  ["file", "product-guide.pdf", "PDF", "Completed", "42", "Today 14:20", "red"],
  ["link", "agent-module-url", "URL", "Completed", "18", "Today 12:10", "blue"],
  ["file", "release-notes.md", "MD", "Completed", "22", "Yesterday 18:30", "blue"],
  ["news", "pasted-text-2026-05-19", "Text", "Completed", "9", "Yesterday 16:10", "gray"],
  ["link", "bad-url.com", "URL", "Failed", "0", "Yesterday 15:02", "red"],
];

export function KnowledgeBaseDetailPage() {
  return (
    <KnowledgeShell>
      <section className="knowledge-detail">
        <nav className="kb-breadcrumb">
          <Icon name="home" />
          <span>›</span>
          <span>Knowledge Center</span>
          <span>/</span>
          <strong>Product Docs</strong>
        </nav>
        <div className="detail-head">
          <span className="kb-base-icon blue"><Icon name="folder" /></span>
          <div>
            <h1>Product Docs</h1>
            <p>Official product documentation, guides, and reference materials.</p>
            <small>Created May 19, 2026 <b>·</b> 5 sources <b>·</b> 111 chunks</small>
          </div>
          <AddSourceMenu compact />
        </div>
        <div className="kb-toolbar">
          <label><Icon name="search" /><span>Search sources...</span></label>
          <button type="button"><Icon name="filter" />All Types<span>⌄</span></button>
        </div>
        <article className="source-table">
          <header>
            <span>Source Name</span>
            <span>Type</span>
            <span>Status</span>
            <span>Chunks</span>
            <span>Updated⌄</span>
            <span />
          </header>
          {sources.map(([icon, name, type, status, chunks, updated, tone]) => (
            <div className="source-table-row" key={name}>
              <span className={`source-kind ${tone}`}><Icon name={icon} /></span>
              <strong>{name}</strong>
              <em className={`type ${type.toLowerCase()}`}>{type}</em>
              <mark className={status === "Failed" ? "failed" : "completed"}>{status}</mark>
              <span>{chunks}</span>
              <time>{updated}</time>
              <button type="button"><Icon name="more" /></button>
            </div>
          ))}
          <footer>
            <span>Showing 1 to 5 of 5 sources</span>
            <div>
              <button type="button" disabled>‹</button>
              <button className="active" type="button">1</button>
              <button type="button" disabled>›</button>
            </div>
          </footer>
        </article>
      </section>
    </KnowledgeShell>
  );
}
