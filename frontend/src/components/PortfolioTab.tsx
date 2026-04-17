import { useState, useRef, useMemo } from 'react';
import { Loader2, Briefcase, Upload, RefreshCw, AlertTriangle } from 'lucide-react';
import type { PortfolioPosition, PortfolioSummary } from '../types';
import PositionCard from './PositionCard';

interface PortfolioTabProps {
    onScanHoldings: (holdings: any[]) => void;
    portfolioResult: any;
    loading: boolean;
}

export default function PortfolioTab({ onScanHoldings, portfolioResult, loading }: PortfolioTabProps) {
    const fileRef = useRef<HTMLInputElement>(null);
    const [filter, setFilter] = useState<'active' | 'closed' | 'all'>('active');

    const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (ev) => {
            const text = ev.target?.result as string;
            const lines = text.trim().split('\n');
            if (lines.length < 2) return;
            const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
            const rows = lines.slice(1).map(line => {
                const vals = line.split(',');
                const row: any = {};
                headers.forEach((h, i) => { row[h] = vals[i]?.trim() ?? ''; });
                return row;
            });
            onScanHoldings(rows);
        };
        reader.readAsText(file);
    };

    // Transform API results into UI positions
    const positions: PortfolioPosition[] = useMemo(() => {
        if (!portfolioResult?.holdings) return [];

        return (portfolioResult.holdings ?? []).map((h: any) => {
            return {
                ticker: h.ticker,
                company_name: h.name || h.ticker.replace('.NS', '').replace('&', '_'),
                status: h.status || (h.vcp_score >= 60 ? '5MA Safe' : 'Monitoring'),
                holding_days: h.holding_days || Math.floor(Math.random() * 10) + 1,
                pnl_pct: h.avg_cost ? ((h.ltp - h.avg_cost) / h.avg_cost) * 100 : 0,
                pnl_value: h.open_pnl || (h.ltp - (h.avg_cost || h.ltp)) * h.quantity,
                pnl_absolute_label: (h.open_pnl || 0) >= 1000 ? `+${((h.open_pnl || 0) / 1000).toFixed(1)}k` : `${(h.open_pnl || 0) >= 0 ? '+' : ''}${(h.open_pnl || 0).toFixed(0)}`,
                entry_price: h.avg_cost || 0,
                current_price: h.ltp,
                is_active: true,
                stage: h.stage,
                vcp_score: h.vcp_score,
                quantity: h.quantity,
                avg_cost: h.avg_cost
            };
        });
    }, [portfolioResult]);

    const summary: PortfolioSummary = useMemo(() => {
        const count = positions.length;
        const invested = positions.reduce((acc, p) => acc + (p.avg_cost * p.quantity), 0);
        const currentVal = positions.reduce((acc, p) => acc + (p.current_price * p.quantity), 0);
        const totalPnl = currentVal - invested;
        const totalPnlPct = invested > 0 ? (totalPnl / invested) * 100 : 0;

        return {
            position_count: count,
            invested_amount: invested,
            invested_label: invested >= 100000 ? `${(invested / 100000).toFixed(1)}L` : `${(invested / 1000).toFixed(0)}k`,
            days_pnl_value: totalPnl * 0.15, // Mock day pnl
            days_pnl_pct: 1.5,
            total_pnl_value: totalPnl,
            total_pnl_pct: totalPnlPct,
            open_risk_pct: 0.8,
            open_risk_value: invested * 0.008,
            locked_profit_value: totalPnl * 0.4
        };
    }, [positions]);

    const filteredPositions = positions.filter(p => {
        if (filter === 'active') return p.is_active;
        if (filter === 'closed') return !p.is_active;
        return true;
    });

    if (!portfolioResult && !loading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center gap-6 animate-slide-down">
                <div className="w-20 h-20 bg-panel/40 rounded-full flex items-center justify-center border border-border/20 shadow-2xl">
                    <Briefcase className="w-10 h-10 text-indigo-500/50" />
                </div>
                <div className="text-center">
                    <h2 className="text-xl font-bold text-white mb-2">Portfolio Management</h2>
                    <p className="text-slate-400 max-w-sm mb-6">Upload your Zerodha holdings CSV to analyze your performance and VCP scores.</p>
                    <input ref={fileRef} type="file" accept=".csv" onChange={handleUpload} className="hidden" />
                    <button
                        onClick={() => fileRef.current?.click()}
                        className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold shadow-lg shadow-indigo-600/20 transition-all flex items-center gap-2 mx-auto"
                    >
                        <Upload size={18} /> Import CSV
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full gap-6 overflow-hidden animate-slide-down">
            {/* Top Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div className="bg-panel/40 border border-border/40 p-4 rounded-2xl backdrop-blur-md">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Positions</div>
                    <div className="text-2xl font-black text-indigo-400">{summary.position_count}</div>
                    <div className="text-[11px] font-medium text-slate-500">₹{summary.invested_label} invested</div>
                </div>
                <div className="bg-panel/40 border border-border/40 p-4 rounded-2xl backdrop-blur-md bg-gradient-to-br from-emerald-500/5 to-transparent">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Day's P&L</div>
                    <div className="text-2xl font-black text-emerald-400">+{summary.days_pnl_pct}%</div>
                    <div className="text-[11px] font-medium text-emerald-500/70">+₹{(summary.days_pnl_value / 1000).toFixed(1)}k</div>
                </div>
                <div className="bg-panel/40 border border-border/40 p-4 rounded-2xl backdrop-blur-md">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Total P&L</div>
                    <div className={`text-2xl font-black ${summary.total_pnl_value >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {summary.total_pnl_value >= 0 ? '+' : ''}₹{(summary.total_pnl_value / 1000).toFixed(1)}k
                    </div>
                    <div className="text-[11px] font-medium text-slate-500">{summary.total_pnl_pct.toFixed(2)}% return</div>
                </div>
                <div className="bg-panel/40 border border-border/40 p-4 rounded-2xl backdrop-blur-md">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Open Risk</div>
                    <div className="text-2xl font-black text-white">{summary.open_risk_pct}%</div>
                    <div className="text-[11px] font-medium text-slate-500">₹{(summary.open_risk_value / 1000).toFixed(1)}k at risk</div>
                </div>
                <div className="bg-panel/40 border border-border/40 p-4 rounded-2xl backdrop-blur-md">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Locked Profit</div>
                    <div className="text-2xl font-black text-indigo-300">₹{(summary.locked_profit_value / 1000).toFixed(1)}k</div>
                    <div className="text-[11px] font-medium text-slate-500">if all SL hit</div>
                </div>
            </div>

            {/* Filter & Actions Tool Bar */}
            <div className="flex items-center justify-between">
                <div className="flex items-center bg-panel/30 border border-border/40 rounded-xl p-1 p-0.5">
                    {(['active', 'closed', 'all'] as const).map(t => (
                        <button
                            key={t}
                            onClick={() => setFilter(t)}
                            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${filter === t ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => fileRef.current?.click()}
                        className="p-2 bg-panel/40 border border-border/40 text-slate-300 rounded-xl hover:border-indigo-500/50 transition-all flex items-center gap-2 text-xs font-bold"
                    >
                        <RefreshCw size={14} /> Refresh All
                    </button>
                    <input ref={fileRef} type="file" accept=".csv" onChange={handleUpload} className="hidden" />
                </div>
            </div>

            {/* Positions Grid */}
            <div className="flex-1 overflow-y-auto custom-scrollbar pr-1">
                {loading ? (
                    <div className="h-full flex items-center justify-center">
                        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
                    </div>
                ) : filteredPositions.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 pb-10">
                        {filteredPositions.map(pos => (
                            <PositionCard key={pos.ticker} position={pos} />
                        ))}
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
                        <AlertTriangle size={32} />
                        <span>No {filter} positions found.</span>
                    </div>
                )}
            </div>
        </div>
    );
}
