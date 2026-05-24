export const historyGroups = [
  {
    label: "Today",
    items: [
      ["What is an Agent and how does it work?", "14:30", true],
      ["Summarize this document for me", "11:20"],
      ["Check today's schedule", "09:15"],
    ],
  },
  {
    label: "Yesterday",
    items: [
      ["LangChain vs. LlamaIndex", "20:45"],
      ["How to write better prompts", "17:30"],
    ],
  },
  {
    label: "Earlier",
    items: [
      ["RAG best practices", "09/20"],
      ["Vector database comparison", "09/19"],
    ],
  },
];

export const tools = [
  {
    title: "Knowledge",
    items: [
      ["knowledge", "Knowledge Base"],
      ["search", "Document Search"],
      ["source", "View Sources"],
    ],
  },
  {
    title: "Actions",
    items: [
      ["calendar", "Calendar"],
      ["todo", "Tasks"],
      ["mail", "Email"],
    ],
  },
  {
    title: "Live Lookup",
    items: [
      ["globe", "Web Search"],
      ["weather", "Weather"],
      ["news", "News"],
    ],
  },
];

export const knowledgeBases = [
  ["Product Docs", "PDF, DOCX, TXT", ""],
  ["Technical Docs", "PDF, MD, TXT", ""],
  ["Research Papers", "PDF", "512"],
  ["Meeting Notes", "DOCX, TXT", "64"],
];

export const searchResults = [
  ["AI Agent is an intelligent system that senses and acts...", "Product Docs · page 12 · relevance: 98%", "PDF"],
  ["Building Agent apps with LangChain", "Technical Docs · page 45 · relevance: 96%", "MD"],
  ["ReAct: Synergizing Reasoning and Acting in Language Models", "Research Papers · page 7 · relevance: 94%", "PDF"],
];

export const graphNodes = [
  { text: "LangChain\nAgents", x: 76, y: 18, color: "green" },
  { text: "AutoGPT\nPaper", x: 91, y: 31, color: "green" },
  { text: "Multi-Agent\nSystems", x: 86, y: 73, color: "green" },
  { text: "Tool Learning\nSurvey", x: 22, y: 78, color: "purple" },
  { text: "ReAct\nPaper", x: 19, y: 33, color: "purple" },
];
