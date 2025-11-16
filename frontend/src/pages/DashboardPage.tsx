import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/Card';
import ProgressBar from '../components/ProgressBar';
import AlertBanner from '../components/AlertBanner';
import Button from '../components/Button';
import { currencyFormatter } from '../utils/formatters';
import { DashboardSummary } from '../types';
import { fetchDashboardSummary } from '../services/dashboardService';
import { useAuth } from '../context/AuthContext';

const ANNUAL_LIMIT = 81000;
const MONTHLY_REFERENCE = 6750;

const DashboardPage = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  const loadSummary = async () => {
    try {
      setError(null);
      const data = await fetchDashboardSummary();
      setSummary(data);
    } catch (err) {
      setError('Não foi possível carregar os dados do dashboard.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const annualPercentage = summary ? (summary.annual_revenue / ANNUAL_LIMIT) * 100 : 0;
  const monthlyPercentage = summary ? (summary.monthly_revenue / MONTHLY_REFERENCE) * 100 : 0;

  const shouldWarnAnnual = annualPercentage > 90 && annualPercentage < 100;
  const shouldAlertAnnual = annualPercentage >= 100;
  const shouldWarnMonthly = summary && summary.monthly_revenue > MONTHLY_REFERENCE;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold text-slate-800">Olá, {summary?.full_name ?? user?.full_name ?? 'MEI'} 👋</h1>
        <p className="text-slate-500">Aqui está o resumo do seu MEI.</p>
      </div>

      {error && <AlertBanner variant="danger" title="Algo deu errado" description={error} />}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-slate-500">Faturamento anual</p>
              <p className="text-2xl font-semibold text-slate-800">
                {summary ? currencyFormatter.format(summary.annual_revenue) : '—'}
                <span className="text-base text-slate-400 font-normal"> / {currencyFormatter.format(ANNUAL_LIMIT)}</span>
              </p>
            </div>
            <span className="text-sm font-medium text-primary-600">{annualPercentage.toFixed(0)}%</span>
          </div>
          <ProgressBar value={annualPercentage} color={shouldAlertAnnual ? 'danger' : shouldWarnAnnual ? 'warning' : 'primary'} />
          <p className="text-xs text-slate-400 mt-2">Limite anual do MEI (R$ 81.000,00)</p>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-slate-500">Faturamento mensal</p>
              <p className="text-2xl font-semibold text-slate-800">
                {summary ? currencyFormatter.format(summary.monthly_revenue) : '—'}
                <span className="text-base text-slate-400 font-normal"> / {currencyFormatter.format(MONTHLY_REFERENCE)}</span>
              </p>
            </div>
            <span className="text-sm font-medium text-primary-600">{monthlyPercentage.toFixed(0)}%</span>
          </div>
          <ProgressBar value={monthlyPercentage} color={shouldWarnMonthly ? 'warning' : 'primary'} />
          <p className="text-xs text-slate-400 mt-2">Referência mensal flexível (R$ 6.750,00)</p>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="flex flex-col gap-3">
          <p className="text-sm text-slate-500">Consultas este mês</p>
          <p className="text-3xl font-semibold text-primary-600">{summary?.token_usage ?? 0}</p>
          <p className="text-sm text-slate-400">Limite baseado no seu plano.</p>
        </Card>
        <Card className="flex flex-col gap-3">
          <p className="text-sm text-slate-500">Documentos enviados</p>
          <p className="text-3xl font-semibold text-primary-600">{summary?.documents_total ?? 0}</p>
          <p className="text-sm text-slate-400">Últimos 30 dias.</p>
        </Card>
      </div>

      {(shouldWarnAnnual || shouldAlertAnnual || shouldWarnMonthly) && (
        <AlertBanner
          variant={shouldAlertAnnual ? 'danger' : 'warning'}
          title={
            shouldAlertAnnual
              ? 'Você ultrapassou o limite anual do MEI'
              : shouldWarnAnnual
              ? 'Atenção: você está perto do limite anual'
              : 'Faturamento mensal acima da referência'
          }
          description={
            shouldAlertAnnual
              ? 'Considere migrar para outro regime tributário.'
              : shouldWarnAnnual
              ? 'Faltam menos de 10% para atingir o teto. Revise os próximos passos.'
              : 'Você pode ultrapassar o limite mensal, mas monitore o total anual para não exceder o MEI.'
          }
        />
      )}

      <Card className="flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-slate-800">Precisa de algo rápido?</h3>
          <p className="text-sm text-slate-500">Acesse as áreas mais usadas em um clique.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => navigate('/documents')} variant="secondary">
            Enviar documento
          </Button>
          <Button onClick={() => navigate('/agent')}>Falar com agente</Button>
        </div>
      </Card>

      {isLoading && <p className="text-sm text-slate-400">Carregando dados...</p>}
    </div>
  );
};

export default DashboardPage;
