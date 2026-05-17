import { graphNodes, knowledgeBases, searchResults } from "../data/dashboardData";

export function useRag() {
  return { graphNodes, knowledgeBases, searchResults };
}
