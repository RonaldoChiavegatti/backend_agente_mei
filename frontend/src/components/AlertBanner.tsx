import { HTMLAttributes } from 'react';
import clsx from 'clsx';

interface Props extends HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'warning' | 'danger';
  title: string;
  description?: string;
}

const variants = {
  info: 'bg-primary-50 text-primary-700 border-primary-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger: 'bg-red-50 text-red-700 border-red-200'
};

const AlertBanner = ({ variant = 'info', title, description, className, ...rest }: Props) => (
  <div className={clsx('rounded-2xl border p-4', variants[variant], className)} {...rest}>
    <p className="font-semibold">{title}</p>
    {description && <p className="text-sm mt-1">{description}</p>}
  </div>
);

export default AlertBanner;
