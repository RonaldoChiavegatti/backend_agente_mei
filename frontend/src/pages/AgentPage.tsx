import { useState } from 'react';
import Card from '../components/Card';
import MessageBubble from '../components/chat/MessageBubble';
import ChatInput from '../components/chat/ChatInput';
import { ChatMessage } from '../types';
import { sendChatMessage } from '../services/chatService';
import { v4 as uuid } from 'uuid';
import AlertBanner from '../components/AlertBanner';

const AgentPage = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isThinking, setIsThinking] = useState(false);

  const handleSend = async (content: string) => {
    const newMessage: ChatMessage = {
      id: uuid(),
      role: 'user',
      content,
      createdAt: new Date().toISOString()
    };
    setMessages((prev) => [...prev, newMessage]);
    setIsThinking(true);
    try {
      const response = await sendChatMessage({ question: content });
      const assistantMessage: ChatMessage = {
        id: uuid(),
        role: 'assistant',
        content: response.answer ?? 'O agente respondeu, mas não retornou texto.',
        createdAt: new Date().toISOString(),
        usedDocuments: response.used_documents
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError('Não foi possível falar com o agente agora.');
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-slate-800">Agente Contábil</h1>
        <p className="text-slate-500">Pergunte sobre limites, alertas e documentos.</p>
      </div>

      {error && <AlertBanner variant="danger" title="Ops" description={error} />}

      <Card className="h-[600px] flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-4 pr-3">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center text-center text-slate-400 text-sm">
              <p>Comece perguntando: “Quais documentos ainda estão processando?”</p>
            </div>
          )}
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isThinking && <p className="text-sm text-slate-400">O agente está pensando...</p>}
        </div>
        <div className="border-t border-slate-100 pt-4 mt-4">
          <ChatInput onSend={handleSend} />
        </div>
      </Card>
    </div>
  );
};

export default AgentPage;
