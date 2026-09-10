import React, { useEffect, useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Calendar, User } from 'lucide-react';
import { projectService } from '../services/api';

interface OverdueProjectsCardProps {
  compact?: boolean;
}

export default function OverdueProjectsCard({ compact = false }: OverdueProjectsCardProps) {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(!compact);

  useEffect(() => {
    projectService.getOverdue()
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (projects.length === 0) return null;

  const STATUS_LABELS: Record<string, string> = {
    ORCAMENTO: 'Orçamento',
    PROJETADO: 'Aprovado',
    PRODUCAO: 'Produção',
    MONTAGEM: 'Montagem',
    CONCLUIDO: 'Concluído',
  };

  return (
    <div className="glass-panel rounded-lg overflow-hidden border-l-4 border-l-red-600">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between p-4 cursor-pointer hover:bg-red-950/10 transition"
      >
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          <div className="text-left">
            <span className="text-sm font-semibold text-red-500 font-sans">
              {projects.length} projeto{projects.length !== 1 ? 's' : ''} com prazo vencido
            </span>
            {!expanded && (
              <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                Clique para ver detalhes
              </p>
            )}
          </div>
        </div>
        {expanded
          ? <ChevronUp className="w-4 h-4 text-zinc-400 shrink-0" />
          : <ChevronDown className="w-4 h-4 text-zinc-400 shrink-0" />
        }
      </button>

      {expanded && (
        <div className="border-t border-zinc-800 divide-y divide-zinc-900">
          {projects.map(proj => (
            <div key={proj.id} className="px-4 py-3 flex justify-between items-start gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold font-sans text-zinc-900 dark:text-white truncate">
                    {proj.title}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-500/20 text-zinc-600 border border-zinc-400/30 shrink-0">
                    {STATUS_LABELS[proj.status] || proj.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-[11px] text-zinc-500 font-mono">
                  {proj.client_name && (
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" /> {proj.client_name}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(proj.deadline + 'T12:00:00').toLocaleDateString('pt-BR')}
                  </span>
                </div>
              </div>
              <div className="shrink-0 text-right">
                <span className="text-xs font-bold text-red-500 font-mono whitespace-nowrap">
                  {proj.days_overdue} dia{proj.days_overdue !== 1 ? 's' : ''} atrasado
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
