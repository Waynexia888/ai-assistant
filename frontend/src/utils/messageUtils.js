export function createUserMessage(content) {
  return {
    id: crypto.randomUUID(),
    role: "user",
    content,
    createdAt: new Date().toISOString(),
  };
}

export function createAssistantMessage(data) {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content: data.answer,
    createdAt: new Date().toISOString(),
  };
}
