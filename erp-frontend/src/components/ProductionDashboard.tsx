/**
 * Dashboard da producao — cards de resumo + tabela de /api/reports/production.
 *
 * Nao ha endpoint de dashboard proprio: o relatorio de producao ja traz o
 * `summary` que a spec pede. Reusa o ReportPanel para nao duplicar a tabela.
 */
import { useEffect, useState } from 'react';
import { reportService, getApiErrorMessage } from '../services/api';
import { ReportResult } from '../types';
import ReportPanel from './ReportPanel';

export default function ProductionDashboard() {
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    reportService
      .getReport('production', {})
      .then(r => { if (ativo) setReport(r); })
      .catch(err => {
        if (ativo) setError(getApiErrorMessage(err, 'Erro ao carregar o dashboard da produção.'));
      })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, []);

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setExporting(formato);
    setError('');
    try {
      await reportService.exportReport('production', formato, {});
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao exportar o relatório de produção.'));
    } finally {
      setExporting(null);
    }
  };

  return (
    <ReportPanel
      report={report}
      loading={loading}
      exporting={exporting}
      onExport={exportar}
      loadingLabel="Calculando indicadores..."
      error={error}
    />
  );
}
