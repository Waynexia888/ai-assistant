import { Fragment } from "react";
import { graphNodes } from "../../data/dashboardData";
import { Icon } from "../common/Icon";

export function CitationGraph() {
  return (
    <section className="graph-panel">
      <div className="panel-head">
        <h3>Citation Graph</h3>
        <button><Icon name="expand" />Full Screen</button>
      </div>
      <div className="graph-tabs"><span>View mode:</span><button>Graph</button><button>Timeline</button></div>
      <div className="graph">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none">
          <line x1="50" y1="50" x2="76" y2="18" />
          <line x1="50" y1="50" x2="91" y2="31" />
          <line x1="50" y1="50" x2="86" y2="73" />
          <line x1="50" y1="50" x2="22" y2="78" />
          <line x1="50" y1="50" x2="19" y2="33" />
        </svg>
        <div className="center-node">AI Agent<br />Survey</div>
        {graphNodes.map((node) => (
          <div className={`graph-node ${node.color}`} style={{ left: `${node.x}%`, top: `${node.y}%` }} key={node.text}>
            {node.text.split("\n").map((line) => <Fragment key={line}>{line}<br /></Fragment>)}
          </div>
        ))}
        <span className="edge-label e1">cites</span>
        <span className="edge-label e2">extends</span>
        <span className="edge-label e3">discusses</span>
      </div>
      <footer className="legend">
        <span><b className="blue"></b>Current Doc</span>
        <span><b className="purple"></b>Paper</span>
        <span><b className="green"></b>Framework / Tool</span>
        <span><b className="gray"></b>Concept⌄</span>
        <div>Relation type: <i></i>cites <i></i>related to <i></i>extends <i></i>discusses</div>
      </footer>
    </section>
  );
}
