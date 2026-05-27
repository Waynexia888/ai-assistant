import axios from "axios";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export async function sendChatMessage({ message, sessionId = "" }) {
  const payload = {
    message,
  };

  if (sessionId) {
    payload.sessionId = sessionId;
  }

  const response = await axios.post(`${API_BASE_URL}/chat`, payload);
  return response.data;
}
