import React, { useEffect, useState } from 'react';

/**
 * Sub-abas de um módulo do ERP.
 *
 * Convenção do projeto: cada módulo declara a lista completa de abas pedidas
 * pelo cliente, marcando `ready: true` nas que já têm tela. As demais mostram
 * um estado vazio honesto (nunca dado inventado).
 */
export interface ModuleTab {
  id: string;
  label: string;
  /** false = aba ainda sem tela implementada */
  ready?: boolean;
}

interface ModuleTabsProps {
  tabs: ModuleTab[];
  active: string;
  onChange: (id: string) => void;
}

export default function ModuleTabs({ tabs, active, onChange }: ModuleTabsProps) {
  return (
    <div className="flex flex-wrap gap-x-2 gap-y-1 border-b border-zinc-800" role="tablist">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`px-3 py-2.5 text-xs sm:text-sm font-mono uppercase tracking-wide transition cursor-pointer border-b-2 whitespace-nowrap ${
              isActive
                ? 'text-white border-red-600'
                : 'text-zinc-500 border-transparent hover:text-zinc-300'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Estado vazio para abas que ainda não têm tela.
 * Explicito de proposito: o cliente ve o mapa completo sem ver dado falso.
 */
export function ModuleTabPlaceholder({ label }: { label: string }) {
  return (
    <div className="glass-panel p-10 rounded-lg flex flex-col items-center justify-center text-center gap-2">
      <p className="text-sm text-zinc-300 font-mono">{label}</p>
      <p className="text-xs text-zinc-500 font-mono max-w-md">
        Em desenvolvimento. Esta aba ainda não tem tela — nada aqui é dado real.
      </p>
    </div>
  );
}

/**
 * Renderiza o estado vazio quando a aba ativa ainda não tem tela.
 * Uso: <ActiveTabPlaceholder tabs={TABS} active={activeTab} />
 */
export function ActiveTabPlaceholder({ tabs, active }: { tabs: ModuleTab[]; active: string }) {
  const tab = tabs.find((t) => t.id === active);
  if (!tab || tab.ready) return null;
  return <ModuleTabPlaceholder label={tab.label} />;
}

/**
 * Lembra a sub-aba ativa por módulo, para o reload não voltar para a primeira.
 * Mesmo padrao do `eme_tab` usado no nivel de modulo (App.tsx).
 */
export function useModuleTab(moduleKey: string, tabs: ModuleTab[], fallback: string) {
  const storageKey = `eme_module_tab_${moduleKey}`;

  const [active, setActive] = useState<string>(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored && tabs.some((t) => t.id === stored)) return stored;
    } catch {
      /* localStorage indisponivel: cai no fallback */
    }
    return fallback;
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, active);
    } catch {
      /* ignora quota/modo privado */
    }
  }, [storageKey, active]);

  return [active, setActive] as const;
}
