import { DocumentItem } from '../../types';
import { formatDate, currencyFormatter } from '../../utils/formatters';
import clsx from 'clsx';

interface Props {
  documents: DocumentItem[];
  isLoading?: boolean;
  onSelect: (document: DocumentItem) => void;
  onRefresh?: () => void;
}

const statusStyles: Record<DocumentItem['status'], string> = {
  processing: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700'
};

const DocumentsTable = ({ documents, isLoading, onSelect, onRefresh }: Props) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <div>
          <h3 className="text-lg font-semibold text-slate-800">Seus documentos</h3>
          <p className="text-sm text-slate-500">Clique em um item para ver os detalhes extraídos</p>
        </div>
        {onRefresh && (
          <button onClick={onRefresh} className="text-sm font-medium text-primary-600 hover:text-primary-700">
            Atualizar
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="text-slate-500 border-b border-slate-100">
              <th className="px-6 py-3 font-medium">Arquivo</th>
              <th className="px-6 py-3 font-medium">Data</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Valor</th>
              <th className="px-6 py-3 font-medium">Tipo</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-6 py-6 text-center text-slate-400">
                  Carregando documentos...
                </td>
              </tr>
            )}
            {!isLoading && documents.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-6 text-center text-slate-400">
                  Nenhum documento encontrado.
                </td>
              </tr>
            )}
            {documents.map((doc) => (
              <tr
                key={doc.id}
                onClick={() => onSelect(doc)}
                className="cursor-pointer border-b border-slate-50 hover:bg-slate-50"
              >
                <td className="px-6 py-4 font-semibold text-slate-700">{doc.file_name}</td>
                <td className="px-6 py-4 text-slate-500">{formatDate(doc.uploaded_at)}</td>
                <td className="px-6 py-4">
                  <span className={clsx('px-2 py-1 rounded-full text-xs font-semibold', statusStyles[doc.status])}>
                    {doc.status === 'processing' && 'Processando'}
                    {doc.status === 'completed' && 'Concluído'}
                    {doc.status === 'error' && 'Erro'}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-600">
                  {doc.amount ? currencyFormatter.format(doc.amount) : '—'}
                </td>
                <td className="px-6 py-4 text-slate-600">{doc.document_type ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DocumentsTable;
