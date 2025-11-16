import apiClient from './apiClient';

interface ChatPayload {
  question: string;
}

interface ChatResponse {
  answer: string;
  used_documents?: string[];
}

export const sendChatMessage = async (payload: ChatPayload) => {
  const { data } = await apiClient.post<ChatResponse>('/agent/chat', payload);
  return data;
};
