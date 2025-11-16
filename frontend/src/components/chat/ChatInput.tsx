import { useState } from 'react';
import Button from '../Button';

interface Props {
  onSend: (message: string) => Promise<void>;
}

const ChatInput = ({ onSend }: Props) => {
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!message.trim()) return;
    setIsSending(true);
    setError(null);
    try {
      await onSend(message.trim());
      setMessage('');
    } catch (err) {
      setError('Não foi possível enviar. Tente novamente.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <textarea
        className="w-full min-h-[120px] rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:border-primary-300 focus:ring-2 focus:ring-primary-100"
        placeholder="Quais são os novos prazos do DAS?"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
      />
      {error && <p className="text-sm text-red-500">{error}</p>}
      <div className="flex justify-end">
        <Button type="submit" isLoading={isSending} disabled={!message.trim()}>
          Enviar
        </Button>
      </div>
    </form>
  );
};

export default ChatInput;
