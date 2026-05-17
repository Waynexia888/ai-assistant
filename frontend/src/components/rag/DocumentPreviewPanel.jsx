import { Icon } from "../common/Icon";

export function DocumentPreviewPanel() {
  return (
    <section className="preview-panel">
      <div className="panel-head center"><h3>Document Preview</h3></div>
      <div className="doc-window">
        <header>
          <strong><Icon name="file" />AI Agent: Survey and Open Problems</strong>
          <nav><Icon name="search" /><span className="zoom-level">100%</span><span className="chevron">⌄</span><Icon name="more" /></nav>
        </header>
        <div className="doc-body">
          <aside>
            <strong>Contents</strong>
            {["1. Introduction", "2. Background", "  2.1 Definition of Agent", "  2.2 Types of Agents", "3. Agent Architectures", "4. Applications", "5. Open Problems", "6. Conclusion"].map((item) => <span key={item}>{item}</span>)}
          </aside>
          <article>
            <h4>2.1 Definition of Agent</h4>
            <p>An agent is an entity that perceives its environment through sensors and acts upon that environment through actuators. Modern AI agents leverage large language models for <mark>reasoning</mark> and <mark>decision-making</mark>.</p>
            <div className="mini-diagram">
              <div>Agent<br />(LLM)</div>
              <span>Perception</span><span>Action</span>
              <small>Environment</small><small>Tools</small>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
