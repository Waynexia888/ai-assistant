import { CitationGraph } from "./CitationGraph";
import { DocumentPreviewPanel } from "./DocumentPreviewPanel";
import { DocumentSearchPanel } from "./DocumentSearchPanel";
import { KnowledgeBasePanel } from "./KnowledgeBasePanel";

export function KnowledgeWorkspace() {
  return (
    <section className="bottom-workspace">
      <KnowledgeBasePanel />
      <DocumentSearchPanel />
      <DocumentPreviewPanel />
      <CitationGraph />
    </section>
  );
}
