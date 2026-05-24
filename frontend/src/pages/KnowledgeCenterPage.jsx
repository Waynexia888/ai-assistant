import { AddSourceMenu } from "../components/knowledge/AddSourceMenu";
import { KnowledgeShell } from "../components/knowledge/KnowledgeShell";
import { Icon } from "../components/common/Icon";

const bases = [
  ["Product Docs", "Official product documentation, guides, and FAQs for our AI assistant.", "128 sources", "24,532 chunks", "Updated 2 hours ago", "blue", "folder"],
  ["Technical Docs", "API references, SDK guides, and technical specifications for developers.", "96 sources", "18,741 chunks", "Updated 1 day ago", "green", "folder"],
  ["Research Papers", "Curated research papers and studies related to AI, ML, and LLMs.", "214 sources", "52,893 chunks", "Updated 3 days ago", "purple", "file"],
  ["Meeting Notes", "Internal meeting notes, decisions, and project updates across teams.", "72 sources", "9,362 chunks", "Updated 5 days ago", "orange", "news"],
];

export function KnowledgeCenterPage() {
  return (
    <KnowledgeShell>
      <section className="knowledge-center">
        <div className="knowledge-page-head">
          <div>
            <h1>Knowledge Center</h1>
            <p>Browse and manage the knowledge sources your AI assistant uses.</p>
          </div>
          <AddSourceMenu />
        </div>
        <div className="kb-card-list">
          {bases.map(([name, desc, sources, chunks, updated, tone, icon]) => (
            <article className="kb-base-card" key={name}>
              <span className={`kb-base-icon ${tone}`}><Icon name={icon} /></span>
              <div>
                <h2>{name}</h2>
                <p>{desc}</p>
                <footer>
                  <span><Icon name="file" />{sources}</span>
                  <b>·</b>
                  <span><Icon name="box" />{chunks}</span>
                  <b>·</b>
                  <span><Icon name="clock" />{updated}</span>
                </footer>
              </div>
              <button type="button">›</button>
            </article>
          ))}
        </div>
      </section>
    </KnowledgeShell>
  );
}
