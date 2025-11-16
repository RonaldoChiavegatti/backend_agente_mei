export const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL'
});

export const formatDate = (value?: string) => {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('pt-BR');
};

export const formatMonth = (value: string) => {
  try {
    const date = new Date(value);
    return date.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  } catch (error) {
    return value;
  }
};
