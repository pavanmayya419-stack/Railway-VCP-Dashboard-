import { useState, useRef, useEffect } from 'react';
import { Loader2, ArrowUp, ArrowDown, Filter, Search, ChevronDown } from 'lucide-react';
import ChartTooltip from './ChartTooltip';

// ─── Signal helpers ───────────────────────────────────────────────────────────
const SIGNAL_LABEL_TO_KEY: Record<string, string> = {
    'TL Break': 'tl_breakout',
    'Pivot BX': 'pivot_breakout',
    '20DMA BX': 'dma20_break',
    'Vol↑': 'volume_surge',
    'Price↑': 'price_surge',
};
const SIGNAL_OPTIONS = Object.keys(SIGNAL_LABEL_TO_KEY);

function activeSignals(signals: any): string[] {
    if (!signals) return [];
    if (Array.isArray(signals)) return signals;
    return SIGNAL_OPTIONS.filter(label => !!signals[SIGNAL_LABEL_TO_KEY[label]]);
}

// ─── Constants & formatting ───────────────────────────────────────────────────
const STAGE_COLORS: Record<number, string> = {
    1: 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/60',
    2: 'bg-blue-900/40 text-blue-400 border border-blue-800/60',
    3: 'bg-amber-900/40 text-amber-400 border border-amber-800/60',
    4: 'bg-red-900/40 text-red-400 border border-red-800/60',
};

function pctColor(v: number) {
    if (v > 0) return 'text-emerald-400';
    if (v < 0) return 'text-red-400';
    return 'text-slate-400';
}
function scoreGradient(s: number) {
    if (s >= 80) return 'bg-emerald-500/20 text-emerald-300';
    if (s >= 60) return 'bg-blue-500/20 text-blue-300';
    if (s >= 40) return 'bg-amber-500/20 text-amber-300';
    return 'bg-red-500/20 text-red-300';
}

// ─── Column definitions ───────────────────────────────────────────────────────
// We map display headers to their backend keys for sorting
const COLUMNS = [
    { label: 'TICKER', sortKey: 'ticker' },
    { label: 'SECTOR', sortKey: 'sector' },
    { label: 'CAP', sortKey: 'cap' },
    { label: 'STG', sortKey: 'stage', hasFilter: true },
    { label: 'PRICE', sortKey: 'last_price' },
    { label: 'SCORE', sortKey: 'score' },
    { label: 'CHECK', sortKey: 'checklist' },
    { label: 'RSI', sortKey: 'rsi', hasFilter: true },
    { label: 'VOL R', sortKey: 'vol_ratio', hasFilter: true },
    { label: '%OFFHI', sortKey: 'pct_off_high', hasFilter: true },
    { label: '1D', sortKey: 'r1' },
    { label: '5D', sortKey: 'r5' },
    { label: '3M', sortKey: 'r63' },
    { label: '6M', sortKey: 'r126' },
    { label: 'RS', sortKey: 'rs' },
    { label: 'TIGHT', sortKey: 'tight' },
    { label: 'WBASE', sortKey: 'wbase' },
    { label: 'TREND', sortKey: 'trend_template', hasFilter: true },
    { label: 'LOW%', sortKey: 'dist_low', hasFilter: true },
    { label: 'SIGNALS', sortKey: null, hasFilter: true },
];

// ─── Component ────────────────────────────────────────────────────────────────
interface ScannerTabProps {
    results: any[] | undefined;
    loading: boolean;
    selectedTicker: string | null;
    onSelectTicker: (t: string) => void;
}

export default function ScannerTab({ results, loading, selectedTicker, onSelectTicker }: ScannerTabProps) {
    // Sorting state
    const [sortBy, setSortBy] = useState<string>('score');
    const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

    // Filtering state
    const [stages, setStages] = useState<number[]>([1, 2, 3, 4]);
    const [rsiMin, setRsiMin] = useState<number>(0);
    const [rsiMax, setRsiMax] = useState<number>(100);
    const [minVolRatio, setMinVolRatio] = useState<number>(0);
    const [maxPctOffHigh, setMaxPctOffHigh] = useState<number>(100);
    const [signalFilters, setSignalFilters] = useState<string[]>([]);

    // Hover & Sticky Tooltip state
    const [hoveredTicker, setHoveredTicker] = useState<string | null>(null);
    const [stickyTicker, setStickyTicker] = useState<string | null>(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
    const hoverTimerRef = useRef<any>(null);

    // UI state for active filter popover
    const [activeFilterCol, setActiveFilterCol] = useState<string | null>(null);
    const filterRef = useRef<HTMLDivElement>(null);

    // Close filter popover on clicking outside
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
                setActiveFilterCol(null);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    <div className="text-center">
                        <span className="text-sm text-slate-400 block">Processing 800+ stocks through VCP engine...</span>
                        <span className="text-[10px] text-slate-500 block mt-1">Live Fyers data scan typically takes 15-30 seconds</span>
                    </div>
                </div>
            </div>
        );
    }

    // ── Filter Data ─────────────────────────────────────────────────────────
    let rows = (results ?? []).filter((r: any) => {
        if (!stages.includes(r.stage)) return false;
        const rsi = r.rsi ?? 50;
        if (rsi < rsiMin || rsi > rsiMax) return false;
        if ((r.vol_ratio ?? 0) < minVolRatio) return false;
        if ((r.pct_off_high ?? 100) > maxPctOffHigh) return false;
        if (signalFilters.length > 0) {
            const active = activeSignals(r.signals);
            if (!signalFilters.some(s => active.includes(s))) return false;
        }
        return true;
    });

    // ── Sort Data ───────────────────────────────────────────────────────────
    if (sortBy) {
        rows = [...rows].sort((a: any, b: any) => {
            const av = a[sortBy] ?? 0, bv = b[sortBy] ?? 0;
            const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
            return sortOrder === 'desc' ? -cmp : cmp;
        });
    }

    // ── Toggles ─────────────────────────────────────────────────────────────
    const toggleSort = (colKey: string | null) => {
        if (!colKey) return;
        if (sortBy === colKey) {
            setSortOrder(o => o === 'desc' ? 'asc' : 'desc');
        } else {
            setSortBy(colKey);
            setSortOrder('desc'); // Default to desc for a newly selected column
        }
    };

    const hasActiveFilter = (label: string) => {
        if (label === 'STG' && stages.length < 4) return true;
        if (label === 'RSI' && (rsiMin > 0 || rsiMax < 100)) return true;
        if (label === 'VOL R' && minVolRatio > 0) return true;
        if (label === '%OFFHI' && maxPctOffHigh < 100) return true;
        if (label === 'TREND' && stages.length < 4) return false; // Placeholder logic
        if (label === 'SIGNALS' && signalFilters.length > 0) return true;
        return false;
    };

    const handleMouseEnter = (e: React.MouseEvent, ticker: string) => {
        if (stickyTicker) return; // If something is pinned, don't show hover previews
        const x = e.clientX;
        const y = e.clientY;
        // Small delay before showing to avoid flashing on rapid movement
        if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
        hoverTimerRef.current = setTimeout(() => {
            setHoveredTicker(ticker);
            setTooltipPos({ x, y });
        }, 150);
    };

    const handleMouseLeave = () => {
        if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
        setHoveredTicker(null);
    };

    const handleTickerClick = (e: React.MouseEvent, ticker: string) => {
        e.stopPropagation(); // Avoid row click
        setStickyTicker(ticker === stickyTicker ? null : ticker);
        setHoveredTicker(null);
        setTooltipPos({ x: e.clientX, y: e.clientY });
        onSelectTicker(ticker);
    };

    return (
        <div className="flex flex-col h-full gap-3 relative">
            <div className="flex items-center justify-between bg-panel/60 border border-border/50 rounded-xl px-4 py-2.5 backdrop-blur-sm flex-shrink-0">
                <div className="flex items-center gap-3">
                    <h2 className="text-sm font-bold text-white flex items-center gap-2">
                        <Search className="w-4 h-4 text-primary" /> Scanner Results
                    </h2>
                    <span className="text-[11px] font-mono bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                        {rows.length} matches
                    </span>
                </div>
            </div>

            <div className="flex-1 overflow-auto rounded-xl border border-border/40 bg-panel/40 backdrop-blur-sm custom-scrollbar min-h-0 relative">
                <table className="w-full text-[11px]" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
                    <thead className="sticky top-0 z-10">
                        <tr className="bg-[#12121c] border-b border-border/60 shadow-sm relative">
                            {COLUMNS.map(col => {
                                const isSorted = sortBy === col.sortKey;
                                const filtered = hasActiveFilter(col.label);

                                return (
                                    <th key={col.label} className="px-2 py-2.5 text-[9px] uppercase tracking-wider text-slate-500 font-semibold text-left whitespace-nowrap bg-[#12121c] relative z-20">
                                        <div className="flex items-center gap-1">
                                            {/* Clickable Header for Sorting */}
                                            <div
                                                className={`cursor-pointer hover:text-slate-300 flex items-center gap-1 transition-colors ${col.sortKey ? '' : 'pointer-events-none'}`}
                                                onClick={() => toggleSort(col.sortKey)}
                                            >
                                                <span className={isSorted ? 'text-indigo-400 font-bold' : ''}>
                                                    {col.label}
                                                </span>
                                                {isSorted && (
                                                    sortOrder === 'desc' ? <ArrowDown className="w-3 h-3 text-indigo-400" /> : <ArrowUp className="w-3 h-3 text-indigo-400" />
                                                )}
                                            </div>

                                            {/* Filter Icon button (like Excel chevron) */}
                                            {col.hasFilter && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); setActiveFilterCol(activeFilterCol === col.label ? null : col.label); }}
                                                    className={`ml-1 p-0.5 rounded transition-all ${filtered ? 'text-blue-400 bg-blue-900/30' : 'text-slate-600 hover:bg-slate-800 hover:text-slate-300'}`}
                                                >
                                                    {filtered ? <Filter className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                                                </button>
                                            )}

                                            {/* Absolute Popover Menu for this specific column */}
                                            {activeFilterCol === col.label && (
                                                <div
                                                    ref={filterRef}
                                                    className="absolute top-full left-0 mt-1 w-48 bg-[#1a1a28] border border-border/80 rounded-lg shadow-xl p-3 z-50 animate-slide-down"
                                                    onClick={(e) => e.stopPropagation()} // Prevent closing when interacting with inputs
                                                >
                                                    <div className="text-[10px] font-mono text-slate-400 mb-2 border-b border-border/50 pb-1">Filter {col.label}</div>

                                                    {/* STAGE FILTER */}
                                                    {col.label === 'STG' && (
                                                        <div className="flex flex-col gap-1.5">
                                                            {[1, 2, 3, 4].map(s => (
                                                                <label key={s} className="flex items-center gap-2 cursor-pointer text-sm">
                                                                    <input
                                                                        type="checkbox"
                                                                        className="sidebar-checkbox"
                                                                        checked={stages.includes(s)}
                                                                        onChange={() => setStages(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])}
                                                                    />
                                                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${STAGE_COLORS[s]}`}>S{s}</span>
                                                                </label>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* RSI FILTER */}
                                                    {col.label === 'RSI' && (
                                                        <div className="flex flex-col gap-2">
                                                            <div>
                                                                <div className="text-[10px] text-slate-400 mb-1">Min: {rsiMin}</div>
                                                                <input type="range" min={0} max={100} value={rsiMin} onChange={e => setRsiMin(+e.target.value)} className="sidebar-slider w-full" />
                                                            </div>
                                                            <div>
                                                                <div className="text-[10px] text-slate-400 mb-1">Max: {rsiMax}</div>
                                                                <input type="range" min={0} max={100} value={rsiMax} onChange={e => setRsiMax(+e.target.value)} className="sidebar-slider w-full" />
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* VOL R FILTER */}
                                                    {col.label === 'VOL R' && (
                                                        <div className="flex flex-col gap-2">
                                                            <div className="text-[10px] text-slate-400 mb-1">Min Volume Ratio: {minVolRatio.toFixed(1)}</div>
                                                            <input type="range" min={0} max={5} step={0.1} value={minVolRatio} onChange={e => setMinVolRatio(+e.target.value)} className="sidebar-slider w-full" />
                                                        </div>
                                                    )}

                                                    {/* %OFFHI FILTER */}
                                                    {col.label === '%OFFHI' && (
                                                        <div className="flex flex-col gap-2">
                                                            <div className="text-[10px] text-slate-400 mb-1">Max % Off High: {maxPctOffHigh}%</div>
                                                            <input type="range" min={0} max={100} value={maxPctOffHigh} onChange={e => setMaxPctOffHigh(+e.target.value)} className="sidebar-slider w-full" />
                                                        </div>
                                                    )}

                                                    {/* SIGNALS FILTER */}
                                                    {col.label === 'SIGNALS' && (
                                                        <div className="flex flex-col gap-1.5">
                                                            {SIGNAL_OPTIONS.map(s => (
                                                                <label key={s} className="flex items-center gap-2 cursor-pointer text-sm">
                                                                    <input
                                                                        type="checkbox"
                                                                        className="sidebar-checkbox"
                                                                        checked={signalFilters.includes(s)}
                                                                        onChange={() => setSignalFilters(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])}
                                                                    />
                                                                    <span className="text-slate-300 text-[10px]">{s}</span>
                                                                </label>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </th>
                                );
                            })}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((r: any) => {
                            const sigs = activeSignals(r.signals);
                            return (
                                <tr key={r.ticker}
                                    onClick={() => onSelectTicker(r.ticker)}
                                    className={`border-b border-border/20 hover:bg-[#1a1a28]/80 cursor-pointer transition-all
                    ${selectedTicker === r.ticker
                                            ? 'bg-primary/5 border-l-2 border-l-primary'
                                            : 'border-l-2 border-l-transparent'}`}
                                >
                                    <td
                                        className="px-2 py-2 font-bold text-blue-400 whitespace-nowrap relative group"
                                        onMouseEnter={(e) => handleMouseEnter(e, r.ticker)}
                                        onMouseLeave={handleMouseLeave}
                                        onClick={(e) => handleTickerClick(e, r.ticker)}
                                    >
                                        <span className={`hover:underline decoration-blue-400/30 underline-offset-4 ${stickyTicker === r.ticker ? 'underline decoration-blue-400 border-b-2 border-blue-400/20 pb-0.5' : ''}`}>
                                            {r.ticker}
                                        </span>
                                    </td>
                                    <td className="px-2 py-2 text-slate-600 whitespace-nowrap max-w-[80px] truncate text-[10px]">{r.sector || 'n/a'}</td>
                                    <td className="px-2 py-2 text-slate-600 whitespace-nowrap text-[10px]">{r.cap || 'n/a'}</td>
                                    <td className="px-2 py-2">
                                        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${STAGE_COLORS[r.stage] || 'bg-slate-800 text-slate-400'}`}>
                                            S{r.stage}
                                        </span>
                                    </td>
                                    <td className="px-2 py-2 font-mono text-slate-200">
                                        {r.ticker?.endsWith('.NS') ? '₹' : '$'}{r.last_price?.toFixed(2) ?? '—'}
                                    </td>
                                    <td className="px-2 py-2">
                                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${scoreGradient(r.score ?? 0)}`}>
                                            {r.score?.toFixed(1) ?? '—'}
                                        </span>
                                    </td>
                                    <td className="px-2 py-2 font-mono text-slate-300">
                                        {r.checklist_str || (r.checklist != null ? `${r.checklist}/7` : '—')}
                                    </td>
                                    <td className="px-2 py-2 font-mono text-slate-300">{r.rsi?.toFixed(0) ?? '—'}</td>
                                    <td className="px-2 py-2 font-mono text-slate-300">{r.vol_ratio?.toFixed(2) ?? '—'}</td>
                                    <td className="px-2 py-2 font-mono text-slate-300">{r.pct_off_high?.toFixed(1) ?? '—'}%</td>
                                    <td className={`px-2 py-2 font-mono ${pctColor(r.r1 ?? 0)}`}>{r.r1?.toFixed(1) ?? '—'}%</td>
                                    <td className={`px-2 py-2 font-mono ${pctColor(r.r5 ?? 0)}`}>{r.r5?.toFixed(1) ?? '—'}%</td>
                                    <td className={`px-2 py-2 font-mono ${pctColor(r.r63 ?? 0)}`}>{r.r63?.toFixed(1) ?? '—'}%</td>
                                    <td className={`px-2 py-2 font-mono ${pctColor(r.r126 ?? 0)}`}>{r.r126?.toFixed(1) ?? '—'}%</td>
                                    <td className="px-2 py-2 font-mono text-slate-300">{r.rs?.toFixed(0) ?? '—'}</td>
                                    <td className="px-2 py-2 font-mono text-slate-300">{r.scores?.tightness?.toFixed(1) ?? '—'}</td>
                                    <td className="px-2 py-2 font-mono text-slate-300">{r.scores?.wbase?.toFixed(0) ?? '—'}</td>
                                    <td className="px-2 py-2">
                                        <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-bold ${r.trend_template ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-500'}`}>
                                            {r.trend_template ? 'YES' : 'NO'}
                                        </span>
                                    </td>
                                    <td className="px-2 py-2 font-mono text-slate-300">
                                        {r.dist_low?.toFixed(1) ?? '—'}%
                                    </td>
                                    <td className="px-2 py-2">
                                        <div className="flex gap-1 flex-wrap">
                                            {sigs.map((s, i) => (
                                                <span key={i} className="bg-indigo-500/15 text-indigo-300 text-[9px] px-1.5 py-0.5 rounded-full font-semibold whitespace-nowrap">
                                                    {s}
                                                </span>
                                            ))}
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>

                {rows.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16 text-slate-500">
                        <Search className="w-8 h-8 mb-2 opacity-30" />
                        <p className="text-sm">No results match current filters.</p>
                    </div>
                )}
            </div>

            {/* Hover/Sticky Tooltip */}
            {(hoveredTicker || stickyTicker) && (
                <ChartTooltip
                    ticker={stickyTicker || hoveredTicker || ''}
                    visible={true}
                    x={tooltipPos.x}
                    y={tooltipPos.y}
                    isSticky={!!stickyTicker}
                    onClose={() => setStickyTicker(null)}
                />
            )}
        </div>
    );
}
