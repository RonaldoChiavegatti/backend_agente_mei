import clsx from 'clsx';
import { ChatMessage } from '../../types';

interface Props {
  message: ChatMessage;
}

const MessageBubble = ({ message }: Props) => {
  const isUser = message.role === 'user';
  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm',
          isUser ? 'bg-primary-600 text-white rounded-br-sm' : 'bg-white border border-slate-100 rounded-bl-sm'
        )}
      >
        <p className="whitespace-pre-line leading-relaxed">{message.content}</p>
        {message.usedDocuments && message.usedDocuments.length > 0 && (
          <p className="mt-2 text-xs opacity-80">Baseado em: {message.usedDocuments.join(', ')}</p>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
