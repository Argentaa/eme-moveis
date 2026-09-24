/**
 * Painel do DRE (Demonstrativo de Resultado do Exercicio).
 *
 * Dono do proprio estado (ano, periodo, carregamento, export); a apresentacao
 * fica no ReportPanel, compartilhado com o Dashboard da producao. Antes este
 * componente renderizava a tabela inteira, o que faria a segunda tela
 * duplicar o mesmo bloco.
 *
 * Os helpers de apresentacao sao reexportados daqui porque o ReportsView ja
 * os importava deste arquivo.
 */
import React, { useEffect, useState } from 'react';
import { reportService, getApiErrorMessage } from '../services/api';
import { ReportResult } from '../types';
import ReportPanel, { TONE_CLASSES, inputClass, FilterField } from './ReportPanel';

export { TONE_CLASSES, inputClass, FilterField };

export default function DrePanel() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [period, setPeriod] = useState('mensal');
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setError('');
    reportService
      .getReport('dre', { year: String(year), period })
      .then((r) => { if (ativo) setReport(r); })
      .catch((err) => {
        if (ativo) setError(getApiErrorMessage(err, 'Erro ao carregar o DRE. Tente novamente.'));
      })
      .finally(() => { if (ativo) setLoading(false); });
    return () => { ativo = false; };
  }, [year, period]);

  const exportar = async (formato: 'pdf' | 'xlsx') => {
    setExporting(formato);
    setError('');
    try {
      await reportService.exportReport('dre', formato, { year: String(year), period });
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao exportar o DRE.'));
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
      loadingLabel="Calculando DRE..."
      error={error}
    >
      <FilterField label="Ano">
        <select value={year} onChange={e => setYear(Number(e.target.value))} className={inputClass}>
          {[year - 1, year, year + 1].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </FilterField>
      <FilterField label="Período">
        <select value={period} onChange={e => setPeriod(e.target.value)} className={inputClass}>
          <option value="mensal">Mensal</option>
          <option value="trimestral">Trimestral</option>
          <option value="semestral">Semestral</option>
          <option value="anual">Anual</option>
        </select>
      </FilterField>
    </ReportPanel>
  );
}
