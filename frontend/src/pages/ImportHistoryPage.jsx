import { Icon } from "../components/common/Icon";
import { KnowledgeShell } from "../components/knowledge/KnowledgeShell";

const filters = [
  ["All", ""],
  ["Completed", "green"],
  ["Processing", "blue"],
  ["Failed", "red"],
];

const imports = [
  {
    id: "IMP-2024-0001",
    type: "URL",
    icon: "link",
    tone: "blue",
    source: "example.com/article-1",
    meta: "+ 2 more",
    base: "Product Docs",
    status: "Completed",
    statusTone: "completed",
    chunks: "126",
    error: "-",
    submitted: ["May 16, 2024", "10:24 AM"],
  },
  {
    id: "IMP-2024-0002",
    type: "PDF",
    icon: "file",
    tone: "red",
    source: "AI Agent Guide.pdf",
    meta: "2.4 MB",
    base: "Product Docs",
    status: "Completed",
    statusTone: "completed",
    chunks: "84",
    error: "-",
    submitted: ["May 15, 2024", "3:41 PM"],
  },
  {
    id: "IMP-2024-0003",
    type: "Paste Text",
    icon: "news",
    tone: "purple",
    source: "Pasted content",
    meta: "1,248 characters",
    base: "Product Docs",
    status: "Completed",
    statusTone: "completed",
    chunks: "32",
    error: "-",
    submitted: ["May 15, 2024", "11:02 AM"],
  },
  {
    id: "IMP-2024-0004",
    type: "URL",
    icon: "link",
    tone: "blue",
    source: "docs.example.com/guide",
    meta: "+ 1 more",
    base: "Technical Docs",
    status: "Processing",
    statusTone: "processing",
    chunks: "-",
    error: "-",
    submitted: ["May 16, 2024", "12:18 PM"],
  },
  {
    id: "IMP-2024-0005",
    type: "PDF",
    icon: "file",
    tone: "red",
    source: "architecture-overview.pdf",
    meta: "5.1 MB",
    base: "Technical Docs",
    status: "Completed",
    statusTone: "completed",
    chunks: "210",
    error: "-",
    submitted: ["May 14, 2024", "4:22 PM"],
  },
  {
    id: "IMP-2024-0006",
    type: "URL",
    icon: "link",
    tone: "blue",
    source: "help.example.com/faq",
    meta: "+ 3 more",
    base: "Research Papers",
    status: "Failed",
    statusTone: "failed",
    chunks: "-",
    error: "Crawl timeout",
    submitted: ["May 14, 2024", "9:17 AM"],
  },
];

function StatusBadge({ tone, label }) {
  return (
    <mark className={`import-status ${tone}`}>
      {tone === "completed" ? <Icon name="check" /> : tone === "failed" ? <Icon name="close" /> : <span />}
      {label}
    </mark>
  );
}

export function ImportHistoryPage() {
  return (
    <KnowledgeShell active="imports">
      <section className="import-history">
        <div className="import-head">
          <div>
            <h1>Import History</h1>
            <p>View and track all document import activities across your knowledge bases.</p>
          </div>
          <label className="import-search">
            <Icon name="search" />
            <span>Search imports...</span>
          </label>
        </div>

        <div className="import-filters">
          <div className="import-filter-left">
            {filters.map(([label, tone]) => (
              <button className={label === "All" ? "active" : ""} type="button" key={label}>
                {tone && <i className={tone} />}
                {label}
              </button>
            ))}
            <button type="button">Type <span>⌄</span></button>
          </div>
          <button className="import-time" type="button"><Icon name="calendar" />All time <span>⌄</span></button>
        </div>

        <div className="import-table-wrap">
          <table className="import-table">
            <colgroup>
              <col className="import-col-id" />
              <col className="import-col-type" />
              <col className="import-col-source" />
              <col className="import-col-base" />
              <col className="import-col-status" />
              <col className="import-col-chunks" />
              <col className="import-col-error" />
              <col className="import-col-submitted" />
            </colgroup>
            <thead>
              <tr>
                <th scope="col">ID</th>
                <th scope="col">Type</th>
                <th scope="col">Source</th>
                <th scope="col">Knowledge Base</th>
                <th scope="col">Status</th>
                <th scope="col">Chunks</th>
                <th scope="col">Error</th>
                <th scope="col">Submitted At</th>
              </tr>
            </thead>
            <tbody>
              {imports.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.id}</strong></td>
                  <td>
                    <div className="import-type">
                      <span className={item.tone}><Icon name={item.icon} /></span>
                      <b>{item.type}</b>
                    </div>
                  </td>
                  <td>
                    <div className="import-source">
                      <b>{item.source}</b>
                      <small>{item.meta}</small>
                    </div>
                  </td>
                  <td><div className="import-base"><Icon name="folder" />{item.base}</div></td>
                  <td><StatusBadge tone={item.statusTone} label={item.status} /></td>
                  <td><span>{item.chunks}</span></td>
                  <td><em className={item.statusTone === "failed" ? "failed" : ""}>{item.error}</em></td>
                  <td><time>{item.submitted[0]}<br />{item.submitted[1]}</time></td>
                </tr>
              ))}
            </tbody>
          </table>
          <footer>
            <span>Showing 1 to 6 of 6 imports</span>
            <div>
              <button type="button">‹</button>
              <button className="active" type="button">1</button>
              <button type="button">›</button>
            </div>
          </footer>
        </div>
      </section>
    </KnowledgeShell>
  );
}
