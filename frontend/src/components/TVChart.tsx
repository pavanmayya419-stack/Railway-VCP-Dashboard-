import React, { useEffect, useRef, Component } from 'react';
import {
    createChart,
    ColorType,
    CandlestickSeries,
    LineSeries,
    HistogramSeries,
    CrosshairMode,
} from 'lightweight-charts';
import { AlertTriangle } from 'lucide-react';

// ─── Error Boundary ───────────────────────────────────────────────────────────
interface EBState { hasError: boolean; error?: string }
class ChartErrorBoundary extends Component<{ children: React.ReactNode }, EBState> {
    constructor(props: any) { super(props); this.state = { hasError: false }; }
    static getDerivedStateFromError(e: Error) { return { hasError: true, error: e.message }; }
    render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                    <AlertTriangle className="w-8 h-8 text-amber-500/60" />
                    <p className="text-sm">Chart failed to render</p>
                    <p className="text-[10px] font-mono text-slate-600 max-w-xs text-center">{this.state.error}</p>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        className="text-xs text-primary underline mt-2"
                    >Retry</button>
                </div>
            );
        }
        return this.props.children;
    }
}

// ─── Inner chart component ────────────────────────────────────────────────────
function TVChartInner({ data: apiData }: { data: any }) {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const el = containerRef.current;
        if (!el || !apiData?.data?.length) return;

        const rows: any[] = apiData.data;

        // ── Create chart ─────────────────────────────────────────────────────
        const chart = createChart(el, {
            layout: {
                background: { type: ColorType.Solid, color: '#0a0e1a' },
                textColor: '#94a3b8',
                fontSize: 12,
                fontFamily: 'JetBrains Mono, monospace',
            },
            grid: {
                vertLines: { visible: false },
                horzLines: { color: 'rgba(30,41,59,0.4)' },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { color: 'rgba(59,130,246,0.4)', style: 2 },
                horzLine: { color: 'rgba(59,130,246,0.4)', style: 2 },
            },
            rightPriceScale: {
                borderColor: '#1e1e32',
                scaleMargins: { top: 0.05, bottom: 0.35 },
            },
            timeScale: { borderColor: '#1e1e32', timeVisible: true },
            autoSize: true,
        });

        // ── Candlesticks ──────────────────────────────────────────────────────
        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#4ade80',
            downColor: '#f87171',
            borderVisible: false,
            wickUpColor: '#4ade80',
            wickDownColor: '#f87171',
        });
        candleSeries.setData(rows.map((d: any) => ({
            time: d.time, open: d.open, high: d.high, low: d.low, close: d.close,
        })));

        // ── Moving averages overlaid on main pane (Ribbon) ───────────────────
        const maConfigs: Array<{ key: string; color: string; width: number; style?: number }> = [
            { key: 'ema10', color: '#00BCD499', width: 1 },
            { key: 'ema20', color: '#2196F399', width: 1 },
            { key: 'ema50', color: '#3F51B599', width: 1 },
            { key: 'ema150', color: '#673AB799', width: 1 },
            { key: 'ema200', color: '#9C27B099', width: 1 },
            // Include legacy MAs if EMAs are missing
            { key: 'ma50', color: '#f59e0b99', width: 1 },
            { key: 'ma200', color: '#a78bfa99', width: 1 },
        ];
        for (const { key, color, width } of maConfigs) {
            const maData = rows.filter((d: any) => d[key] != null && d[key] !== 0)
                .map((d: any) => ({ time: d.time, value: d[key] }));
            if (maData.length > 5) {
                const s = chart.addSeries(LineSeries, { color, lineWidth: width as any, crosshairMarkerVisible: false });
                s.setData(maData);
            }
        }

        // ── Volume histogram (inline, bottom of main pane) ───────────────────
        chart.applyOptions({
            rightPriceScale: { scaleMargins: { top: 0.05, bottom: 0.3 } },
        });
        const volData = rows.filter((d: any) => d.volume != null && d.volume > 0)
            .map((d: any) => ({
                time: d.time,
                value: d.volume,
                color: d.close >= d.open ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)',
            }));
        if (volData.length) {
            const volSeries = chart.addSeries(HistogramSeries, {
                priceScaleId: '',
                priceFormat: { type: 'volume' },
            });
            volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
            volSeries.setData(volData);
        }

        // ── VCP Rolling Score (separate with '' priceScaleId trick) ──────────
        const scoreData = rows.map((d: any) => {
            const v = d.rolling_score ?? 0;
            const color = v >= 70 ? '#00e676' : v >= 50 ? '#ffd600' : '#607d8b';
            return { time: d.time, value: v, color };
        });
        const scoreSeries = chart.addSeries(HistogramSeries, {
            priceScaleId: 'score_scale',
            priceFormat: { type: 'price', precision: 0, minMove: 1 },
        });
        scoreSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.7, bottom: 0.1 },
            visible: false,
        });
        scoreSeries.setData(scoreData);

        // ── RSI line ─────────────────────────────────────────────────────────
        const rsiData = rows.filter((d: any) => d.rsi != null && d.rsi !== 0)
            .map((d: any) => ({ time: d.time, value: d.rsi }));
        if (rsiData.length > 10) {
            const rsiSeries = chart.addSeries(LineSeries, {
                priceScaleId: 'rsi_scale',
                color: '#a78bfa',
                lineWidth: 2 as any,
            });
            rsiSeries.priceScale().applyOptions({
                scaleMargins: { top: 0.87, bottom: 0 },
                visible: false,
            });
            rsiSeries.setData(rsiData);

            // RSI reference lines
            for (const [level, color] of [[70, 'rgba(248,113,113,0.35)'], [30, 'rgba(74,222,128,0.35)']] as const) {
                const refS = chart.addSeries(LineSeries, {
                    priceScaleId: 'rsi_scale', color, lineWidth: 1 as any, lineStyle: 2,
                    crosshairMarkerVisible: false,
                });
                refS.setData(rsiData.map((d: any) => ({ time: d.time, value: level })));
            }
        }

        // ── Markers ───────────────────────────────────────────────────────────
        const markers: any[] = [];

        // Contractions
        if (Array.isArray(apiData.contractions)) {
            const ctColors = ['#60a5fa', '#fbbf24', '#a78bfa', '#34d399', '#fb7185'];
            apiData.contractions.forEach((ct: any, i: number) => {
                const hi = rows[ct.high_idx];
                const lo = rows[ct.low_idx];
                const c = ctColors[i % ctColors.length];
                if (hi) markers.push({ time: hi.time, position: 'aboveBar', shape: 'arrowDown', color: c, text: `C${i + 1}` });
                if (lo) markers.push({ time: lo.time, position: 'belowBar', shape: 'arrowUp', color: c, text: `L${i + 1}` });
            });
        }

        // Signals from data rows
        rows.forEach((d: any) => {
            const time = d.time;

            // Squeeze
            if (d.squeeze === 1) {
                markers.push({ time, position: 'belowBar', shape: 'circle', color: 'rgba(255,82,82,0.8)', size: 0.1 });
            }

            // Tier 1/2/3
            if (d.tier_enc === 1) markers.push({ time, position: 'belowBar', shape: 'labelUp', color: '#FFD700', text: 'T1' });
            if (d.tier_enc === 2) markers.push({ time, position: 'belowBar', shape: 'labelUp', color: '#2196F3', text: 'T2' });
            if (d.tier_enc === 3) markers.push({ time, position: 'belowBar', shape: 'labelUp', color: '#9E9E9E', text: 'T3' });

            // PDH (Diamonds are often small, making them bigger or using arrow)
            if (d.pdh_brk === 1) markers.push({ time, position: 'aboveBar', shape: 'diamond', color: '#00E676' });

            // VCP Buy Signal (derived from score and volume surge in Pine)
            const isVcpBuy = (d.rolling_score >= 70 && d.vol_ratio > 1.2 && d.close > d.open);
            if (isVcpBuy) {
                markers.push({ time, position: 'belowBar', shape: 'triangleUp', color: '#00E676', text: 'VCP' });
            }
        });

        if (markers.length) {
            markers.sort((a, b) => (new Date(a.time).getTime() - new Date(b.time).getTime()));
            // Safely set markers if the method exists
            if (typeof (candleSeries as any).setMarkers === 'function') {
                (candleSeries as any).setMarkers(markers);
            }
        }

        chart.timeScale().fitContent();

        // ── Resize observer ───────────────────────────────────────────────────
        const ro = new ResizeObserver(() => {
            if (el) chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
        });
        ro.observe(el);

        return () => { ro.disconnect(); chart.remove(); };
    }, [apiData]);

    if (!apiData?.data?.length) {
        return (
            <div className="flex items-center justify-center h-full text-slate-500 text-sm">
                No data available
            </div>
        );
    }

    return <div ref={containerRef} className="w-full h-full min-h-[300px]" />;
}

// ─── Public export with error boundary ───────────────────────────────────────
export default function TVChart({ data }: { data: any }) {
    return (
        <ChartErrorBoundary>
            <TVChartInner data={data} />
        </ChartErrorBoundary>
    );
}
