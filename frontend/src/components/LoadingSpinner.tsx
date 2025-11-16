import clsx from 'clsx';

interface Props {
  label?: string;
  size?: 'sm' | 'md';
}

export const LoadingSpinner = ({ label, size = 'md' }: Props) => {
  return (
    <div className="flex items-center gap-3 text-primary-600">
      <span
        className={clsx('inline-block animate-spin rounded-full border-2 border-primary-500 border-t-transparent', {
          'w-4 h-4': size === 'sm',
          'w-6 h-6': size === 'md'
        })}
      />
      {label && <span className="text-sm font-medium text-slate-500">{label}</span>}
    </div>
  );
};
