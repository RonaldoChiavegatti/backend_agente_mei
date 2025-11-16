import { useEffect, useMemo, useState } from 'react';
import Card from '../components/Card';
import UploadZone from '../components/documents/UploadZone';
import DocumentsTable from '../components/documents/DocumentsTable';
import DocumentDetailsModal from '../components/documents/DocumentDetailsModal';
import { DocumentDetails, DocumentItem } from '../types';
import { fetchDocumentDetails, fetchDocuments, updateDocument, uploadDocument } from '../services/documentsService';
import AlertBanner from '../components/AlertBanner';
import useInterval from '../hooks/useInterval';

const DocumentsPage = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<DocumentDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      setError(null);
      const data = await fetchDocuments();
      setDocuments(data);
    } catch (err) {
      setError('Não foi possível carregar seus documentos.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  useInterval(() => {
    const hasProcessing = documents.some((doc) => doc.status === 'processing');
    if (hasProcessing) {
      loadDocuments();
    }
  }, 15000);

  const handleUpload = async (file: File) => {
    await uploadDocument(file);
    await loadDocuments();
  };

  const handleSelect = async (doc: DocumentItem) => {
    const details = await fetchDocumentDetails(doc.id);
    setSelected(details);
  };

  const handleSave = async (changes: Partial<DocumentDetails>) => {
    if (!selected) return;
    const updated = await updateDocument(selected.id, changes);
    setSelected(updated);
    setDocuments((prev) => prev.map((doc) => (doc.id === updated.id ? { ...doc, ...updated } : doc)));
  };

  const processingCount = useMemo(() => documents.filter((doc) => doc.status === 'processing').length, [documents]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-slate-800">Documentos</h1>
        <p className="text-slate-500">Envie notas e acompanhe o processamento.</p>
      </div>

      {error && <AlertBanner variant="danger" title="Não foi possível carregar" description={error} />}

      <Card>
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">Enviar novo documento</h2>
            <p className="text-sm text-slate-500">Arraste ou selecione seus arquivos.</p>
          </div>
          <UploadZone onUpload={handleUpload} />
          {processingCount > 0 && (
            <AlertBanner
              variant="warning"
              title="Processando..."
              description={`${processingCount} documento(s) ainda estão sendo lidos. Atualize a lista em alguns minutos.`}
            />
          )}
        </div>
      </Card>

      <DocumentsTable documents={documents} isLoading={isLoading} onSelect={handleSelect} onRefresh={loadDocuments} />

      {selected && <DocumentDetailsModal document={selected} onClose={() => setSelected(null)} onSave={handleSave} />}
    </div>
  );
};

export default DocumentsPage;
