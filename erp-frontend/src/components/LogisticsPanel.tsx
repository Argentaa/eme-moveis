/**
 * Calendario logistico — pedidos de compra pela data esperada de entrega.
 *
 * Ordenado do mais atrasado para o mais distante, com o atraso destacado: e o
 * que o cliente cobra da transportadora. Transportadora e rastreio sao
 * editaveis aqui mesmo, sem abrir o pedido.
 */
import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Loader2, Package, Pencil, Truck } from 'lucide-react';
import { purchaseService, getApiErrorMessage } from '../services/api';
import { PurchaseOrder } from '../types';

const fmt = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

function dataBR(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 10).split('-').reverse().join('/') : '—';
}

/** Dias entre hoje e a data esperada: positivo = ja passou (atrasado). */
function diasDeAtraso(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const alvo = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(alvo.getTime())) return null;
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  return Math.round((hoje.getTime() - alvo.getTime()) / 86400000);
}

/** Pedido ja recebido/cancelado nao entra no calendario de cobranca. */
const ENCERRADOS = ['RECEBIDA', 'CANCELADA'];

export default function LogisticsPanel() {
  const [pedidos, setPedidos] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [form, setForm] = useState({ carrier: '', tracking: '' });
  const [salvando, setSalvando] = useState(false);

  const carregar = () => {
    setLoading(true);
    setError('');
    purchaseService
      .list()
      .then(setPedidos)
      .catch(err => setError(getApiErrorMessage(err, 'Erro ao carregar o calendário logístico.')))
      .finally(() => setLoading(false));
  };

  useEffect(carregar, []);

  const visiveis = useMemo(
    () =>
      pedidos
        .filter(p => !ENCERRADOS.includes(p.status))
        .sort((a, b) => {
          // sem data esperada vai para o fim: nao da para cobrar prazo que nao existe
          if (!a.expected_date) return 1;
          if (!b.expected_date) return -1;
          return a.expected_date < b.expected_date ? -1 : 1;
        }),
    [pedidos],
  );

  const atrasados = visiveis.filter(p => {
    const d = diasDeAtraso(p.expected_date);
    return d !== null && d > 0;
  }).length;

  const abrirEdicao = (p: PurchaseOrder) => {
    setEditandoId(p.id);
    setForm({ carrier: p.carrier || '', tracking: p.tracking || '' });
  };

  const salvar = async (id: string) => {
    setSalvando(true);
    setError('');
    try {
      const atualizado = await purchaseService.update(id, {
        carrier: form.carrier, tracking: form.tracking,
      });
      setPedidos(ps => ps.map(p => (p.id === id ? atualizado : p)));
      setEditandoId(null);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Erro ao salvar os dados logísticos.'));
    } finally {
      setSalvando(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-8 h-8 text-red-600 animate-spin mb-4" />
        <p className="text-zinc-400 font-mono text-xs">Carregando calendário logístico...</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="glass-panel p-5 rounded-lg border-l-4 border-l-red-650">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
              Entregas atrasadas
            </span>
          </div>
          <p className="text-2xl font-bold font-sans text-rose-500 mt-2">{atrasados}</p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">pedido(s) com prazo vencido</p>
        </div>
        <div className="glass-panel p-5 rounded-lg">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-zinc-400" />
            <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
              Em acompanhamento
            </span>
          </div>
          <p className="text-2xl font-bold font-sans text-white mt-2">{visiveis.length}</p>
          <p className="text-[11px] text-zinc-500 font-mono mt-1">
            recebidos e cancelados saem daqui
          </p>
        </div>
      </div>

      {error && (
        <div className="glass-panel p-4 rounded-lg border-l-4 border-l-red-600">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      <div className="glass-panel rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="text-xs uppercase font-mono text-zinc-500 bg-zinc-950/70 border-b border-zinc-905">
              <tr>
                <th className="py-3 px-5 font-normal">Pedido</th>
                <th className="py-3 px-5 font-normal">Fornecedor</th>
                <th className="py-3 px-5 font-normal">Previsão</th>
                <th className="py-3 px-5 font-normal">Situação</th>
                <th className="py-3 px-5 font-normal">Transportadora</th>
                <th className="py-3 px-5 font-normal">Rastreio</th>
                <th className="py-3 px-5 font-normal text-right">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {visiveis.map(p => {
                const dias = diasDeAtraso(p.expected_date);
                const atrasado = dias !== null && dias > 0;
                const editando = editandoId === p.id;
                return (
                  <tr key={p.id} className={atrasado ? 'bg-red-950/10' : 'hover:bg-zinc-900/40'}>
                    <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                      {p.number}
                      <span className="block text-[10px] text-zinc-500">{p.status}</span>
                    </td>
                    <td className="py-3 px-5 font-sans text-xs">{p.supplier_name || '—'}</td>
                    <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                      {dataBR(p.expected_date)}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs whitespace-nowrap">
                      {dias === null ? (
                        <span className="text-zinc-500">sem previsão</span>
                      ) : atrasado ? (
                        <span className="text-rose-500">{dias} dia(s) em atraso</span>
                      ) : dias === 0 ? (
                        <span className="text-amber-400">chega hoje</span>
                      ) : (
                        <span className="text-zinc-400">em {Math.abs(dias)} dia(s)</span>
                      )}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs">
                      {editando ? (
                        <input type="text" value={form.carrier} placeholder="Transportadora"
                          onChange={e => setForm({ ...form, carrier: e.target.value })}
                          className="w-36 bg-zinc-900 border border-zinc-805 text-white rounded px-2 py-1 text-xs font-mono focus:outline-none" />
                      ) : (
                        <span className="flex items-center gap-1 text-zinc-300">
                          {p.carrier ? <><Truck className="w-3 h-3 text-zinc-500" />{p.carrier}</> : '—'}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs">
                      {editando ? (
                        <div className="flex items-center gap-1">
                          <input type="text" value={form.tracking} placeholder="Código"
                            onChange={e => setForm({ ...form, tracking: e.target.value })}
                            className="w-28 bg-zinc-900 border border-zinc-805 text-white rounded px-2 py-1 text-xs font-mono focus:outline-none" />
                          <button onClick={() => salvar(p.id)} disabled={salvando}
                            className="px-2 py-1 bg-emerald-950/40 border border-emerald-900/40 text-emerald-400 rounded text-[10px] font-mono uppercase cursor-pointer disabled:opacity-60">
                            ok
                          </button>
                          <button onClick={() => setEditandoId(null)}
                            className="px-2 py-1 bg-zinc-900 border border-zinc-800 text-zinc-400 rounded text-[10px] font-mono uppercase cursor-pointer">
                            x
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <span className="text-zinc-400">{p.tracking || '—'}</span>
                          <button onClick={() => abrirEdicao(p)} title="Editar transportadora e rastreio"
                            className="p-1 text-zinc-500 hover:text-white transition cursor-pointer">
                            <Pencil className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-5 font-mono text-xs text-right whitespace-nowrap">
                      {fmt(Number(p.total))}
                    </td>
                  </tr>
                );
              })}
              {visiveis.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-zinc-500 font-mono">
                    Nenhum pedido em acompanhamento.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
