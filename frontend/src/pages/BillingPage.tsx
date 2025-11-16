import { useEffect, useState } from 'react';
import Card from '../components/Card';
import AlertBanner from '../components/AlertBanner';
import { BillingEntry } from '../types';
import { fetchBillingHistory, fetchBillingSummary } from '../services/billingService';
import { formatDate } from '../utils/formatters';

const BillingPage = () => {
  const [summary, setSummary] = useState<{ total_tokens: number; month_tokens: number } | null>(null);
  const [history, setHistory] = useState<BillingEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const [summaryResponse, historyResponse] = await Promise.all([fetchBillingSummary(), fetchBillingHistory()]);
      setSummary(summaryResponse);
      setHistory(historyResponse);
    } catch (err) {
      setError('Não foi possível buscar o histórico de créditos.');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-slate-800">Faturamento e Créditos</h1>
        <p className="text-slate-500">Acompanhe o uso dos seus tokens.</p>
      </div>

      {error && <AlertBanner variant="danger" title="Não foi possível carregar" description={error} />}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <p className="text-sm text-slate-500">Consultas este mês</p>
          <p className="text-4xl font-semibold text-primary-600">{summary?.month_tokens ?? 0}</p>
          <p className="text-xs text-slate-400">Atualizado em tempo real.</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">Total histórico</p>
          <p className="text-4xl font-semibold text-primary-600">{summary?.total_tokens ?? 0}</p>
          <p className="text-xs text-slate-400">Inclui consultas ao agente e upload de documentos.</p>
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">Histórico</h2>
            <p className="text-sm text-slate-500">Acompanhe todas as movimentações de tokens.</p>
          </div>
          <button onClick={loadData} className="text-sm font-medium text-primary-600">
            Recarregar
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-slate-500">
                <th className="text-left py-3">Data</th>
                <th className="text-left py-3">Tipo</th>
                <th className="text-left py-3">Tokens</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 && (
                <tr>
                  <td colSpan={3} className="text-center py-6 text-slate-400">
                    Nenhum histórico ainda.
                  </td>
                </tr>
              )}
              {history.map((entry) => (
                <tr key={entry.id} className="border-t border-slate-100">
                  <td className="py-3 text-slate-600">{formatDate(entry.date)}</td>
                  <td className="py-3 font-medium text-slate-700">{entry.type}</td>
                  <td className="py-3 text-primary-600 font-semibold">{entry.tokens}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default BillingPage;
