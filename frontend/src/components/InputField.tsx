import { InputHTMLAttributes } from 'react';
import clsx from 'clsx';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

const InputField = ({ label, error, className, ...rest }: Props) => {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium text-slate-600">{label}</span>
      <input
        className={clsx(
          'rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-400 transition',
          error ? 'border-red-400' : 'border-slate-200',
          className
        )}
        {...rest}
      />
      {error && <span className="text-xs text-red-500">{error}</span>}
    </label>
  );
};

export default InputField;
