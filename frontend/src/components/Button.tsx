import { ButtonHTMLAttributes } from 'react';
import clsx from 'clsx';
import { LoadingSpinner } from './LoadingSpinner';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
}

const Button = ({ children, className, isLoading, disabled, variant = 'primary', ...rest }: ButtonProps) => {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all disabled:opacity-60 disabled:cursor-not-allowed',
        {
          primary: 'bg-primary-600 text-white hover:bg-primary-700',
          secondary: 'bg-white text-primary-600 border border-primary-200 hover:bg-primary-50',
          ghost: 'text-slate-500 hover:text-primary-600'
        }[variant],
        className
      )}
      disabled={disabled || isLoading}
      {...rest}
    >
      {isLoading && <LoadingSpinner size="sm" />}
      {children}
    </button>
  );
};

export default Button;
