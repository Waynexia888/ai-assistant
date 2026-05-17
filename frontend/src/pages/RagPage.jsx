import { KnowledgeWorkspace } from "../components/rag/KnowledgeWorkspace";
import { MainLayout } from "../components/layout/MainLayout";

export function RagPage() {
  return <MainLayout workspace={<KnowledgeWorkspace />} />;
}
