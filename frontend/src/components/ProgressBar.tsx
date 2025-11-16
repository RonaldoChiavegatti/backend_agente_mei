interface Props {
  value: number;
  color?: 'primary' | 'warning' | 'danger';
}

const colors = {
  primary: 'bg-primary-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500'
};

const ProgressBar = ({ value, color = 'primary' }: Props) => {
  const normalized = Math.min(100, Math.max(0, value));
  return (
    <div className="h-2 w-full rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${colors[color]}`} style={{ width: `${normalized}%` }} />
    </div>
  );
};

export default ProgressBar;
