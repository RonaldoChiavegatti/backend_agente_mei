import clsx from 'clsx';
import { HTMLAttributes } from 'react';

const Card = ({ className, ...rest }: HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('bg-white rounded-2xl border border-slate-100 shadow-card p-6', className)} {...rest} />
);

export default Card;
