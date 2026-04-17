import { useState, useMemo } from 'react';
import { BookOpen, Plus, Trash2, Edit2, TrendingUp, TrendingDown, Calendar, Target, DollarSign, Save, X } from 'lucide-react';

interface Trade {
    id: string;
    ticker: string;
    entryDate: string;
    exitDate: string;
    entryPrice: number;
    exitPrice: number;
    quantity: number;
    type: 'long' | 'short';
    status: 'open' | 'closed';
    notes: string;
    setup: string;
}

const STORAGE_KEY = 'vcp_trade_journal';

function loadTrades(): Trade[] {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

function saveTrades(trades: Trade[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trades));
}

export default function TradeJournalTab() {
    const [trades, setTrades] = useState<Trade[]>(loadTrades);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all');

    const [form, setForm] = useState({
        ticker: '',
        entryDate: '',
        exitDate: '',
        entryPrice: 0,
        exitPrice: 0,
        quantity: 0,
        type: 'long' as 'long' | 'short',
        status: 'open' as 'open' | 'closed',
        notes: '',
        setup: 'VCP Breakout'
    });

    const stats = useMemo(() => {
        const closed = trades.filter(t => t.status === 'closed');
        if (closed.length === 0) return { trades: 0, wins: 0, winRate: 0, pnl: 0, avgWin: 0, avgLoss: 0, rr: 0 };
        
        const wins = closed.filter(t => {
            const pnl = t.type === 'long' 
                ? (t.exitPrice - t.entryPrice) * t.quantity
                : (t.entryPrice - t.exitPrice) * t.quantity;
            return pnl > 0;
        });
        
        const totalPnl = closed.reduce((sum, t) => {
            return sum + (t.type === 'long' 
                ? (t.exitPrice - t.entryPrice) * t.quantity
                : (t.entryPrice - t.exitPrice) * t.quantity);
        }, 0);

        const winsArr = closed.filter(t => {
            const pnl = t.type === 'long' 
                ? (t.exitPrice - t.entryPrice) * t.quantity
                : (t.entryPrice - t.exitPrice) * t.quantity;
            return pnl > 0;
        });
        const lossesArr = closed.filter(t => {
            const pnl = t.type === 'long' 
                ? (t.exitPrice - t.entryPrice) * t.quantity
                : (t.entryPrice - t.exitPrice) * t.quantity;
            return pnl <= 0;
        });

        const avgWin = winsArr.length > 0 ? winsArr.reduce((s, t) => s + ((t.type === 'long' ? (t.exitPrice - t.entryPrice) : (t.entryPrice - t.exitPrice)) * t.quantity), 0) / winsArr.length : 0;
        const avgLoss = lossesArr.length > 0 ? Math.abs(lossesArr.reduce((s, t) => s + ((t.type === 'long' ? (t.exitPrice - t.entryPrice) : (t.entryPrice - t.exitPrice)) * t.quantity), 0) / lossesArr.length) : 0;

        return {
            trades: closed.length,
            wins: wins.length,
            winRate: (wins.length / closed.length) * 100,
            pnl: totalPnl,
            avgWin,
            avgLoss,
            rr: avgLoss > 0 ? avgWin / avgLoss : 0
        };
    }, [trades]);

    const filteredTrades = useMemo(() => {
        if (filter === 'all') return trades;
        return trades.filter(t => t.status === filter);
    }, [trades, filter]);

    const handleSave = () => {
        const newTrade: Trade = {
            ...form,
            id: editingId || Date.now().toString()
        };
        
        let updated: Trade[];
        if (editingId) {
            updated = trades.map(t => t.id === editingId ? newTrade : t);
        } else {
            updated = [...trades, newTrade];
        }
        
        setTrades(updated);
        saveTrades(updated);
        resetForm();
    };

    const resetForm = () => {
        setForm({
            ticker: '',
            entryDate: '',
            exitDate: '',
            entryPrice: 0,
            exitPrice: 0,
            quantity: 0,
            type: 'long',
            status: 'open',
            notes: '',
            setup: 'VCP Breakout'
        });
        setShowForm(false);
        setEditingId(null);
    };

    const handleEdit = (trade: Trade) => {
        setForm(trade);
        setEditingId(trade.id);
        setShowForm(true);
    };

    const handleDelete = (id: string) => {
        const updated = trades.filter(t => t.id !== id);
        setTrades(updated);
        saveTrades(updated);
    };

    const getPnl = (trade: Trade) => {
        if (trade.status === 'open') return 0;
        return trade.type === 'long' 
            ? (trade.exitPrice - trade.entryPrice) * trade.quantity
            : (trade.entryPrice - trade.exitPrice) * trade.quantity;
    };

    return (
        <div className="p-4 space-y-4 overflow-y-auto h-full">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5">
                    <BookOpen className="w-4 h-4 text-cyan-400" />
                    <h2 className="text-sm font-bold text-white">Trade Journal</h2>
                    <span className="text-[11px] font-mono bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded-full">
                        {trades.length} trades
                    </span>
                </div>
                <button
                    onClick={() => setShowForm(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-sm font-medium"
                >
                    <Plus className="w-4 h-4" /> Add Trade
                </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
                    <div className="text-[10px] uppercase text-slate-500 mb-1">Win Rate</div>
                    <div className={`text-xl font-bold ${stats.winRate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                        {stats.winRate.toFixed(1)}%
                    </div>
                </div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
                    <div className="text-[10px] uppercase text-slate-500 mb-1">Total P&L</div>
                    <div className={`text-xl font-bold ${stats.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ¥{stats.pnl.toFixed(0)}
                    </div>
                </div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
                    <div className="text-[10px] uppercase text-slate-500 mb-1">Avg Win</div>
                    <div className="text-xl font-bold text-green-400">¥{stats.avgWin.toFixed(0)}</div>
                </div>
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-center">
                    <div className="text-[10px] uppercase text-slate-500 mb-1">Risk/Reward</div>
                    <div className={`text-xl font-bold ${stats.rr >= 2 ? 'text-green-400' : stats.rr >= 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                        1:{stats.rr.toFixed(1)}
                    </div>
                </div>
            </div>

            {/* Filter */}
            <div className="flex gap-2">
                {(['all', 'open', 'closed'] as const).map(f => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                            filter === f ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                    >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                ))}
            </div>

            {/* Trade Form Modal */}
            {showForm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-white">{editingId ? 'Edit Trade' : 'New Trade'}</h3>
                            <button onClick={resetForm} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Ticker</label>
                                <input
                                    type="text"
                                    value={form.ticker}
                                    onChange={e => setForm({...form, ticker: e.target.value.toUpperCase()})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                    placeholder="RELIANCE"
                                />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Type</label>
                                <select
                                    value={form.type}
                                    onChange={e => setForm({...form, type: e.target.value as 'long' | 'short'})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                >
                                    <option value="long">Long</option>
                                    <option value="short">Short</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Entry Date</label>
                                <input
                                    type="date"
                                    value={form.entryDate}
                                    onChange={e => setForm({...form, entryDate: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Entry Price</label>
                                <input
                                    type="number"
                                    value={form.entryPrice || ''}
                                    onChange={e => setForm({...form, entryPrice: Number(e.target.value)})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Quantity</label>
                                <input
                                    type="number"
                                    value={form.quantity || ''}
                                    onChange={e => setForm({...form, quantity: Number(e.target.value)})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Status</label>
                                <select
                                    value={form.status}
                                    onChange={e => setForm({...form, status: e.target.value as 'open' | 'closed'})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                >
                                    <option value="open">Open</option>
                                    <option value="closed">Closed</option>
                                </select>
                            </div>
                            {form.status === 'closed' && (
                                <>
                                    <div>
                                        <label className="text-[10px] uppercase text-slate-500 block mb-1">Exit Date</label>
                                        <input
                                            type="date"
                                            value={form.exitDate}
                                            onChange={e => setForm({...form, exitDate: e.target.value})}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-[10px] uppercase text-slate-500 block mb-1">Exit Price</label>
                                        <input
                                            type="number"
                                            value={form.exitPrice || ''}
                                            onChange={e => setForm({...form, exitPrice: Number(e.target.value)})}
                                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                        />
                                    </div>
                                </>
                            )}
                            <div className="col-span-2">
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Setup</label>
                                <input
                                    type="text"
                                    value={form.setup}
                                    onChange={e => setForm({...form, setup: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                                    placeholder="VCP Breakout"
                                />
                            </div>
                            <div className="col-span-2">
                                <label className="text-[10px] uppercase text-slate-500 block mb-1">Notes</label>
                                <textarea
                                    value={form.notes}
                                    onChange={e => setForm({...form, notes: e.target.value})}
                                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white h-20"
                                    placeholder="Trade notes..."
                                />
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={handleSave}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-sm font-medium"
                            >
                                <Save className="w-4 h-4" /> Save Trade
                            </button>
                            <button
                                onClick={resetForm}
                                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Trades List */}
            <div className="space-y-2">
                {filteredTrades.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">
                        No trades yet. Add your first trade!
                    </div>
                ) : (
                    filteredTrades.map(trade => {
                        const pnl = getPnl(trade);
                        return (
                            <div key={trade.id} className="bg-slate-800/30 border border-slate-700/40 rounded-xl p-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-2 h-8 rounded-full ${trade.type === 'long' ? 'bg-green-500' : 'bg-red-500'}`} />
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="font-bold text-white">{trade.ticker}</span>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${trade.type === 'long' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                    {trade.type.toUpperCase()}
                                                </span>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full ${trade.status === 'open' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-600/20 text-slate-400'}`}>
                                                    {trade.status.toUpperCase()}
                                                </span>
                                            </div>
                                            <div className="text-xs text-slate-500 mt-1">
                                                {trade.entryDate} @ ¥{trade.entryPrice} × {trade.quantity}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        {trade.status === 'closed' && (
                                            <div className={`text-right ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                <div className="font-bold">¥{pnl.toFixed(0)}</div>
                                                <div className="text-[10px] text-slate-500">{trade.exitDate}</div>
                                            </div>
                                        )}
                                        <div className="flex gap-1">
                                            <button onClick={() => handleEdit(trade)} className="p-2 text-slate-400 hover:text-white">
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button onClick={() => handleDelete(trade.id)} className="p-2 text-slate-400 hover:text-red-400">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                {trade.notes && (
                                    <div className="mt-2 text-xs text-slate-500 pl-5">{trade.notes}</div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
