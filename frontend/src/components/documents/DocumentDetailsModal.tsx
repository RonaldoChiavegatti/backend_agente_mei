import { useEffect, useState } from 'react';
import { DocumentDetails } from '../../types';
import Button from '../Button';
import InputField from '../InputField';
import { currencyFormatter, formatDate } from '../../utils/formatters';

interface Props {
  document: DocumentDetails | null;
  onClose: () => void;
  onSave: (changes: Partial<DocumentDetails>) => Promise<void>;
}

const DocumentDetailsModal = ({ document, onClose, onSave }: Props) => {
  const [form, setForm] = useState({
    amount: document?.amount?.toString() ?? '',
    document_date: document?.document_date ?? '',
    document_type: document?.document_type ?? ''
  });
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (document) {
      setForm({
        amount: document.amount?.toString() ?? '',
        document_date: document.document_date ?? '',
        document_type: document.document_type ?? ''
      });
    }
  }, [document]);

  if (!document) return null;

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setFeedback(null);
    try {
      await onSave({
        amount: form.amount ? Number(form.amount) : undefined,
        document_date: form.document_date,
        document_type: form.document_type
      });
      setFeedback('Alterações salvas com sucesso!');
    } catch (error) {
      setFeedback('Não foi possível salvar. Tente novamente.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-3xl shadow-2xl max-w-xl w-full p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-800">{document.file_name}</h2>
            <p className="text-sm text-slate-500">Enviado em {formatDate(document.uploaded_at)}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-2xl">
            ×
          </button>
        </div>

        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-slate-500">Status atual</p>
            <p className="font-semibold text-slate-700">
              {document.status === 'processing' && 'Processando'}
              {document.status === 'completed' && 'Concluído'}
              {document.status === 'error' && 'Erro'}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Valor reconhecido</p>
            <p className="font-semibold text-slate-700">
              {document.amount ? currencyFormatter.format(document.amount) : '—'}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Tipo</p>
            <p className="font-semibold text-slate-700">{document.document_type ?? '—'}</p>
          </div>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <InputField
            label="Valor (R$)"
            name="amount"
            type="number"
            step="0.01"
            value={form.amount}
            onChange={handleChange}
          />
          <InputField label="Data do documento" name="document_date" type="date" value={form.document_date} onChange={handleChange} />
          <InputField label="Tipo" name="document_type" value={form.document_type} onChange={handleChange} />
          {feedback && <p className="text-sm text-slate-500">{feedback}</p>}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={onClose}>
              Fechar
            </Button>
            <Button type="submit" isLoading={isSaving}>
              Salvar alterações
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DocumentDetailsModal;
