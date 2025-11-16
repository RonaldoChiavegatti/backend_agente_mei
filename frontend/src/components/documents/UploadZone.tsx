import { useCallback, useState } from 'react';
import clsx from 'clsx';
import Button from '../Button';

interface Props {
  onUpload: (file: File) => Promise<void>;
}

const UploadZone = ({ onUpload }: Props) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      setError(null);
      setIsUploading(true);
      try {
        await onUpload(file);
      } catch (err) {
        setError('Não foi possível enviar o documento. Tente novamente.');
      } finally {
        setIsUploading(false);
      }
    },
    [onUpload]
  );

  const handleDrag = (event: React.DragEvent<HTMLLabelElement>, dragging: boolean) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(dragging);
    if (dragging && event.dataTransfer?.items[0] && event.dataTransfer.items[0].kind !== 'file') {
      setError('Apenas arquivos são aceitos.');
    }
  };

  return (
    <label
      onDrop={(event) => {
        handleDrag(event, false);
        handleFiles(event.dataTransfer.files);
      }}
      onDragOver={(event) => handleDrag(event, true)}
      onDragLeave={(event) => handleDrag(event, false)}
      className={clsx(
        'border-2 border-dashed rounded-2xl p-6 flex flex-col items-center gap-3 text-center cursor-pointer transition-colors',
        isDragging ? 'border-primary-400 bg-primary-50' : 'border-slate-200 bg-white'
      )}
    >
      <p className="font-semibold text-slate-700">Arraste seu PDF ou imagem</p>
      <p className="text-sm text-slate-500">Arquivos suportados: PDF, JPG, JPEG, PNG</p>
      <input
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        className="hidden"
        onChange={(event) => handleFiles(event.target.files)}
      />
      <Button type="button" variant="secondary" isLoading={isUploading}>
        {isUploading ? 'Enviando...' : 'Selecionar arquivo'}
      </Button>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </label>
  );
};

export default UploadZone;
