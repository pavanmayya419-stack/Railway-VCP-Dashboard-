import { useState } from 'react';
import { Loader2, BarChart3, Eye, EyeOff } from 'lucide-react';
import TVChart from './TVChart';

interface ChartAnalysisTabProps {
    chartData: any;
    loadingChart: boolean;
    selectedTicker: string | null;
    chartHeight: number;
    tickers: string[];
    onSelectTicker: (t: string) => void;
}

function RadarScore({ label, value, max = 100, color }: { label: string; value: number; max?: number; color: string }) {
    const pct = Math.min(100, (value / max) * 100);
    return (
        <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 w-16 truncate">{label}</span>
            <div className="flex-1 h-1.5 bg-[#1a1a28] rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span className="text-[11px] font-mono font-semibold w-8 text-right" style={{ color }}>{value.toFixed(0)}</span>
        </div>
    );
}

function SignalCard({ label, active }: { label: string; active: boolean }) {
    return (
        <div className={`flex items-center gap-2  px-3 py-2 rounded-lg border text-xs font-semibold transition-all ${active
                ? 'bg-emerald-900/20 border-emerald-700/40 text-emerald-300'
                : 'bg-[#12121c] border-border/30 text-slate-500'
            }`}>
            <div className={`w-2 h-2 rounded-full ${active ? 'bg-emerald-400 shadow-sm shadow-emerald-400/40 animate-pulse' : 'bg-slate-600'}`} />
            {label}
        </div>
    );
}

function ContractionCard({ idx, contraction }: { idx: number; contraction: any }) {
    const colors = ['#60a5fa', '#fbbf24', '#a78bfa', '#34d399'];
    const c = colors[idx % colors.length];
    return (
        <div className="bg-[#12121c] border border-border/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold" style={{ background: c + '20', color: c }}>
                    C{idx + 1}
                </div>
                <span className="text-[11px] text-slate-400">Contraction {idx + 1}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div>
                    <span className="text-slate-500">Range</span>
                    <p className="font-mono font-bold text-slate-200">{contraction.range_pct?.toFixed(1) ?? '—'}%</p>
                </div>
                <div>
                    <span className="text-slate-500">Duration</span>
                    <p className="font-mono font-bold text-slate-200">{contraction.duration ?? '—'} bars</p>
                </div>
            </div>
        </div>
    );
}

export default function ChartAnalysisTab({
    chartData, loadingChart, selectedTicker, chartHeight, tickers, onSelectTicker
}: ChartAnalysisTabProps) {
    const [buyLevel, setBuyLevel] = useState(70);
    const [watchLevel, setWatchLevel] = useState(50);
    const [squeezeBg, setSqueezeBg] = useState(true);
    const [peakLabels, setPeakLabels] = useState(true);
    const [allScores, setAllScores] = useState(false);

    return (
        <div className="flex flex-col h-full gap-3">
            {/* Controls bar */}
            <div className="flex flex-wrap items-center gap-4 bg-panel/60 border border-border/50 rounded-xl px-4 py-2.5 backdrop-blur-sm">
                <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-primary" />
                    <span className="text-sm font-bold text-white">Chart Analysis</span>
                </div>

                {/* Ticker selector */}
                <select
                    value={selectedTicker || ''}
                    onChange={e => onSelectTicker(e.target.value)}
                    className="sidebar-select text-xs min-w-[120px]"
                >
                    <option value="">Select ticker</option>
                    {tickers.map(t => <option key={t} value={t}>{t}</option>)}
                </select>

                <div className="h-6 w-px bg-border/50" />

                {/* Buy Level */}
                <div className="flex items-center gap-2 text-[11px]">
                    <span className="text-slate-500">Buy</span>
                    <input type="range" min={40} max={90} value={buyLevel} onChange={e => setBuyLevel(+e.target.value)} className="sidebar-slider w-20" />
                    <span className="font-mono text-emerald-400 w-6">{buyLevel}</span>
                </div>

                {/* Watch Level */}
                <div className="flex items-center gap-2 text-[11px]">
                    <span className="text-slate-500">Watch</span>
                    <input type="range" min={30} max={60} value={watchLevel} onChange={e => setWatchLevel(+e.target.value)} className="sidebar-slider w-20" />
                    <span className="font-mono text-amber-400 w-6">{watchLevel}</span>
                </div>

                <div className="h-6 w-px bg-border/50" />

                {/* Toggles */}
                <button onClick={() => setSqueezeBg(!squeezeBg)} className={`chart-toggle ${squeezeBg ? 'chart-toggle-on' : ''}`}>
                    {squeezeBg ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />} Squeeze
                </button>
                <button onClick={() => setPeakLabels(!peakLabels)} className={`chart-toggle ${peakLabels ? 'chart-toggle-on' : ''}`}>
                    {peakLabels ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />} Peaks
                </button>
                <button onClick={() => setAllScores(!allScores)} className={`chart-toggle ${allScores ? 'chart-toggle-on' : ''}`}>
                    {allScores ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />} All Scores
                </button>
            </div>

            {/* Main content */}
            <div className="flex-1 flex gap-3 min-h-0">
                {/* Chart */}
                <div className="flex-1 bg-panel/40 border border-border/40 rounded-xl overflow-hidden flex flex-col">
                    {loadingChart ? (
                        <div className="flex-1 flex items-center justify-center">
                            <Loader2 className="w-8 h-8 animate-spin text-primary" />
                        </div>
                    ) : chartData ? (
                        <>
                            <div className="flex items-center justify-between px-4 py-2 border-b border-border/30">
                                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                    {selectedTicker}
                                    {chartData.stage && (
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${{
                                                1: 'bg-emerald-900/40 text-emerald-400', 2: 'bg-blue-900/40 text-blue-400',
                                                3: 'bg-amber-900/40 text-amber-400', 4: 'bg-red-900/40 text-red-400'
                                            }[chartData.stage as number] || ''
                                            }`}>
                                            Stage {chartData.stage}
                                        </span>
                                    )}
                                </h3>
                                <span className="text-xs font-mono text-slate-400">{chartData.checklist_str}</span>
                            </div>
                            <div className="flex-1" style={{ minHeight: `${chartHeight}px` }}>
                                <TVChart data={chartData} />
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
                            Select a ticker to view chart
                        </div>
                    )}
                </div>

                {/* Right info panel */}
                {chartData && (
                    <div className="w-72 flex flex-col gap-3 overflow-y-auto custom-scrollbar">
                        {/* Score Radar */}
                        <div className="bg-panel/60 border border-border/40 rounded-xl p-4 backdrop-blur-sm">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Score Components</h4>
                            <div className="space-y-2.5">
                                {chartData.scores && Object.entries(chartData.scores).map(([key, val]) => (
                                    <RadarScore
                                        key={key}
                                        label={key.replace(/_/g, ' ')}
                                        value={val as number}
                                        color={
                                            (val as number) >= 70 ? '#10b981' :
                                                (val as number) >= 40 ? '#f59e0b' : '#ef4444'
                                        }
                                    />
                                ))}
                            </div>
                            <div className="mt-4 pt-3 border-t border-border/30 text-center">
                                <span className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                                    {chartData.score?.toFixed(1)}
                                </span>
                                <p className="text-[10px] text-slate-500 mt-0.5">TOTAL VCP SCORE</p>
                            </div>
                        </div>

                        {/* Contractions */}
                        {chartData.contractions && chartData.contractions.length > 0 && (
                            <div className="bg-panel/60 border border-border/40 rounded-xl p-4 backdrop-blur-sm">
                                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Contractions</h4>
                                <div className="space-y-2">
                                    {chartData.contractions.map((c: any, i: number) => (
                                        <ContractionCard key={i} idx={i} contraction={c} />
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Signals */}
                        <div className="bg-panel/60 border border-border/40 rounded-xl p-4 backdrop-blur-sm">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Signal Status</h4>
                            <div className="space-y-1.5">
                                {[
                                    { label: 'TL Breakout', key: 'tl_breakout' },
                                    { label: 'Pivot Breakout', key: 'pivot_breakout' },
                                    { label: '20DMA Breakout', key: 'dma20_break' },
                                    { label: 'Volume Surge', key: 'volume_surge' },
                                    { label: 'Price Surge', key: 'price_surge' },
                                ].map(({ label, key }) => (
                                    <SignalCard
                                        key={key}
                                        label={label}
                                        active={chartData.signals?.[key] ?? false}
                                    />
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
