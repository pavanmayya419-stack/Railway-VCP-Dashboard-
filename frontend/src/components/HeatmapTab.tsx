import { useMemo } from 'react';
import { Flame, BarChart3, PieChart, Trophy } from 'lucide-react';
import type { ScanResult } from '../types';

interface HeatmapTabProps {
    results: ScanResult[] | undefined;
}

function SectorCell({ sector, avgScore, count }: { sector: string; avgScore: number; count: number }) {
    const intensity = Math.min(1, avgScore / 100);
    const bg = avgScore >= 70
        ? `rgba(16,185,129,${intensity * 0.5})`
        : avgScore >= 40
            ? `rgba(245,158,11,${intensity * 0.4})`
            : `rgba(239,68,68,${intensity * 0.35})`;

    return (
        <div
            className="relative rounded-lg p-3 border border-border/20 flex flex-col items-center justify-center gap-1 cursor-default transition-transform hover:scale-[1.03]"
            style={{ background: bg, minHeight: '80px' }}
        >
            <span className="text-[11px] font-semibold text-white/90 text-center leading-tight">{sector}</span>
            <span className="text-lg font-bold text-white">{avgScore.toFixed(0)}</span>
            <span className="text-[9px] text-white/50">{count} stocks</span>
        </div>
    );
}

function ScoreHistogram({ results }: { results: ScanResult[] }) {
    const buckets = useMemo(() => {
        const b: number[] = new Array(10).fill(0);
        results.forEach(r => {
            const idx = Math.min(9, Math.floor((r.score ?? 0) / 10));
            b[idx]++;
        });
        return b;
    }, [results]);

    const maxBucket = Math.max(...buckets, 1);

    return (
        <div className="flex items-end gap-1 h-40">
            {buckets.map((count, i) => {
                const pct = (count / maxBucket) * 100;
                const label = `${i * 10}-${(i + 1) * 10}`;
                const color = i >= 7 ? '#10b981' : i >= 4 ? '#f59e0b' : '#ef4444';
                return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <span className="text-[9px] font-mono text-slate-400">{count}</span>
                        <div
                            className="w-full rounded-t transition-all duration-500"
                            style={{ height: `${pct}%`, minHeight: count > 0 ? '4px' : '0', background: color, opacity: 0.7 }}
                        />
                        <span className="text-[8px] text-slate-500 whitespace-nowrap">{label}</span>
                    </div>
                );
            })}
        </div>
    );
}

function StageBreakdown({ results }: { results: ScanResult[] }) {
    const stages = useMemo(() => {
        const m: Record<number, number> = {};
        results.forEach(r => { m[r.stage] = (m[r.stage] || 0) + 1; });
        return Object.entries(m).sort(([a], [b]) => +a - +b).map(([stage, count]) => ({ stage: +stage, count }));
    }, [results]);

    const total = results.length || 1;
    const colors: Record<number, string> = { 1: '#10b981', 2: '#3b82f6', 3: '#f59e0b', 4: '#ef4444' };

    return (
        <div className="space-y-2">
            {stages.map(s => (
                <div key={s.stage} className="flex items-center gap-3">
                    <span className="text-xs font-bold w-8" style={{ color: colors[s.stage] }}>S{s.stage}</span>
                    <div className="flex-1 h-6 bg-[#1a1a28] rounded-md overflow-hidden">
                        <div
                            className="h-full rounded-md flex items-center px-2 transition-all duration-500"
                            style={{ width: `${(s.count / total) * 100}%`, background: colors[s.stage] + '40' }}
                        >
                            <span className="text-[10px] font-mono text-white/80">{s.count}</span>
                        </div>
                    </div>
                    <span className="text-[10px] text-slate-500 w-10 text-right">{((s.count / total) * 100).toFixed(0)}%</span>
                </div>
            ))}
        </div>
    );
}

export default function HeatmapTab({ results }: HeatmapTabProps) {
    const sectorData = useMemo(() => {
        if (!results) return [];
        const map: Record<string, { total: number; count: number }> = {};
        results.forEach(r => {
            const sec = r.sector || 'Unknown';
            if (!map[sec]) map[sec] = { total: 0, count: 0 };
            map[sec].total += r.score ?? 0;
            map[sec].count++;
        });
        return Object.entries(map)
            .map(([sector, d]) => ({ sector, avgScore: d.total / d.count, count: d.count }))
            .sort((a, b) => b.avgScore - a.avgScore);
    }, [results]);

    const topBreakout = useMemo(() => {
        if (!results) return [];
        return [...results]
            .filter(r => r.score >= 60)
            .sort((a, b) => b.score - a.score)
            .slice(0, 10);
    }, [results]);

    const data = results ?? [];

    return (
        <div className="flex flex-col h-full gap-4 overflow-y-auto custom-scrollbar">
            {/* Header */}
            <div className="flex items-center gap-3 bg-panel/60 border border-border/50 rounded-xl px-4 py-2.5 backdrop-blur-sm">
                <Flame className="w-4 h-4 text-orange-400" />
                <h2 className="text-sm font-bold text-white">Heatmap & Statistics</h2>
                <span className="text-[11px] font-mono bg-orange-500/10 text-orange-400 px-2 py-0.5 rounded-full">
                    {data.length} tickers
                </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Sector Heatmap */}
                <div className="bg-panel/60 border border-border/40 rounded-xl p-5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <PieChart className="w-4 h-4 text-cyan-400" />
                        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Sector Heatmap</h3>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {sectorData.map(s => (
                            <SectorCell key={s.sector} {...s} />
                        ))}
                    </div>
                </div>

                {/* Score Distribution */}
                <div className="bg-panel/60 border border-border/40 rounded-xl p-5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <BarChart3 className="w-4 h-4 text-purple-400" />
                        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">VCP Score Distribution</h3>
                    </div>
                    <ScoreHistogram results={data} />
                </div>

                {/* Stage Breakdown */}
                <div className="bg-panel/60 border border-border/40 rounded-xl p-5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <BarChart3 className="w-4 h-4 text-yellow-400" />
                        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Stage Breakdown</h3>
                    </div>
                    <StageBreakdown results={data} />
                </div>

                {/* Top Breakout Candidates */}
                <div className="bg-panel/60 border border-border/40 rounded-xl p-5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <Trophy className="w-4 h-4 text-amber-400" />
                        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Top Breakout Candidates</h3>
                    </div>
                    <div className="space-y-1.5">
                        {topBreakout.map((r, i) => (
                            <div key={r.ticker} className="flex items-center gap-3 bg-[#12121c] rounded-lg px-3 py-2 border border-border/20">
                                <span className="text-[10px] text-slate-500 w-4">#{i + 1}</span>
                                <span className="text-xs font-bold text-blue-400 flex-1">{r.ticker}</span>
                                <span className="text-[10px] text-slate-400">{r.sector}</span>
                                <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${r.score >= 80 ? 'bg-emerald-500/15 text-emerald-400' : 'bg-blue-500/15 text-blue-400'
                                    }`}>{r.score?.toFixed(1)}</span>
                            </div>
                        ))}
                        {topBreakout.length === 0 && (
                            <p className="text-xs text-slate-500 text-center py-4">No candidates with score ≥ 60</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
