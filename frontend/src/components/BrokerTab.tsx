import { Shield, CheckCircle2, Globe, Database, Info } from 'lucide-react';

export default function BrokerTab() {
    return (
        <div className="flex flex-col gap-6 p-1 h-full overflow-hidden">
            <div className="flex items-center justify-between mb-2">
                <div>
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Shield className="text-indigo-400" />
                        Data Provider Settings
                    </h2>
                    <p className="text-slate-400 text-sm">Monitor your market data source and connection status.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* YFinance Card */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 flex flex-col gap-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-[80px] -mr-16 -mt-16 group-hover:bg-indigo-500/10 transition-colors" />

                    <div className="flex items-start justify-between relative z-10">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-indigo-500/20 rounded-xl flex items-center justify-center border border-indigo-500/30">
                                <Globe className="text-indigo-400 w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">Yahoo Finance (Live)</h3>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/20">
                                        <CheckCircle2 size={12} /> Connected
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-4 relative z-10">
                        <div className="bg-slate-950/50 rounded-lg p-4 border border-slate-800/50">
                            <div className="flex items-center gap-3 text-slate-300 text-sm mb-1">
                                <Database size={16} className="text-indigo-400" />
                                <span>Status</span>
                            </div>
                            <div className="text-white font-medium pl-7 text-sm">
                                Unlimited Public API Mode
                            </div>
                            <p className="text-[10px] text-slate-500 mt-2 pl-7 uppercase tracking-wider">No authentication token required for YFinance data.</p>
                        </div>
                    </div>

                    <div className="flex flex-col gap-3 relative z-10">
                        <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-lg p-4 text-xs text-indigo-200 leading-relaxed">
                            <p>All US and Indian (NSE/BSE) market data is currently being fetched directly from Yahoo Finance. This includes historical daily bars and live price updates.</p>
                        </div>
                    </div>
                </div>

                {/* Info Card */}
                <div className="bg-slate-900/30 border border-slate-800/50 border-dashed rounded-xl p-6 flex flex-col justify-center items-center text-center gap-4">
                    <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center text-slate-500">
                        <Info size={32} />
                    </div>
                    <div>
                        <h3 className="text-white font-semibold">Deployment Info</h3>
                        <p className="text-slate-500 text-sm mt-2 max-w-xs mx-auto">
                            The application is currently configured for autonomous operation without broker dependencies.
                            Scanning and live simulation use the internal YFinance engine.
                        </p>
                    </div>
                </div>

            </div>
        </div>
    );
}
