"""
VCP Scanner Dashboard with ML Intelligence Tab
Demonstrates integration of the ML Intelligence Tab into the existing VCP scanner.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="VCP Scanner Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import existing infrastructure
from data_manager import list_cached_dates, load_scan_cache
from engine import DETECTOR, fetch_data, compute_indicators

# Import ML Intelligence Tab
from ml_intelligence_tab import render_ml_tab

# ==============================================================================
# CSS STYLING
# ==============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* Global styles */
.stApp {
    background-color: #0a0e1a;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #111827 0%, #0a0e1a 100%);
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 12px 16px;
}
.metric-label {
    font-size: 11px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 600;
    color: #f9fafb;
}
.metric-delta {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
}

/* Section headers */
.section-hdr {
    font-size: 14px;
    font-weight: 600;
    color: #f9fafb;
    margin: 16px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1f2937;
}

/* Chips */
.chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 4px;
}
.chip-green { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
.chip-blue { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.chip-yellow { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.chip-red { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.chip-indigo { background: rgba(129, 140, 248, 0.15); color: #818cf8; }
.chip-gray { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }

/* Stage badges */
.stage-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}
.s1 { background: rgba(74, 222, 128, 0.2); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
.s2 { background: rgba(96, 165, 250, 0.2); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.3); }
.s3 { background: rgba(251, 191, 36, 0.2); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }
.s4 { background: rgba(248, 113, 113, 0.2); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }

/* Signal table */
.signal-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.signal-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid #1f2937;
    color: #6b7280;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}
.signal-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #1f2937;
}
.signal-table tr:hover {
    background: rgba(59, 130, 246, 0.05);
}

/* Deltas */
.delta-up { color: #4ade80; }
.delta-down { color: #f87171; }
.delta-neu { color: #94a3b8; }

/* Alert banner */
.alert-banner {
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
}
.alert-banner.error {
    background: rgba(248, 113, 113, 0.1);
    border-color: rgba(248, 113, 113, 0.3);
}
.alert-banner.success {
    background: rgba(74, 222, 128, 0.1);
    border-color: rgba(74, 222, 128, 0.3);
}

/* Progress bars */
.score-bar-outer {
    width: 100%;
    height: 6px;
    background: #1f2937;
    border-radius: 3px;
    overflow: hidden;
}
.score-bar-inner {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
}

/* Filter labels */
.filter-label {
    font-size: 11px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: #374151;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #4b5563;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SIDEBAR
# ==============================================================================

with st.sidebar:
    st.markdown("""
    <div style='display:flex; align-items:center; gap:12px; margin-bottom:24px'>
        <div style='width:40px; height:40px; background:linear-gradient(135deg, #4f46e5, #7c3aed); border-radius:8px; display:flex; align-items:center; justify-content:center'>
            <span style='font-size:20px'>📊</span>
        </div>
        <div>
            <div style='font-size:16px; font-weight:700; color:#f9fafb'>VCP Scanner Pro</div>
            <div style='font-size:11px; color:#6b7280'>ML-Powered Analysis</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Market selection
    st.markdown("<div class='filter-label'>Market</div>", unsafe_allow_html=True)
    market_key = st.radio(
        "Select market",
        ["US", "IN"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Min score
    st.markdown("<div class='filter-label'>Minimum VCP Score</div>", unsafe_allow_html=True)
    min_score = st.slider(
        "Min score",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        label_visibility="collapsed"
    )
    
    # Date selection
    cached_dates = list_cached_dates(market_key)
    if cached_dates:
        st.markdown("<div class='filter-label'>Scan Date</div>", unsafe_allow_html=True)
        scan_date = st.selectbox(
            "Select date",
            options=cached_dates[:20],  # Show most recent 20
            label_visibility="collapsed"
        )
    else:
        scan_date = None
        st.warning("No cached dates available")
    
    # Action buttons
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🔄 Load Scan Data", use_container_width=True):
        if scan_date:
            with st.spinner("Loading scan results..."):
                results = load_scan_cache(market_key, scan_date)
                st.session_state.results = results
                st.session_state.market_key = market_key
                st.session_state.scan_date = scan_date
                st.success(f"Loaded {len(results)} results")
        else:
            st.error("No scan date selected")

# ==============================================================================
# MAIN CONTENT
# ==============================================================================

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = []
if "market_key" not in st.session_state:
    st.session_state.market_key = market_key

# Header
results_count = len(st.session_state.results)
st.markdown(f"""
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:24px'>
    <div>
        <h1 style='margin:0; font-size:24px; font-weight:700; color:#f9fafb'>VCP Scanner Dashboard</h1>
        <p style='margin:4px 0 0; font-size:13px; color:#6b7280'>
            Market: <span style='color:#60a5fa; font-weight:600'>{market_key}</span> • 
            Results: <span style='color:#60a5fa; font-weight:600'>{results_count}</span> • 
            Min Score: <span style='color:#60a5fa; font-weight:600'>{min_score}</span>
        </p>
    </div>
    <div>
        {f"<span class='chip chip-green'>Live Data</span>" if results_count > 0 else "<span class='chip chip-gray'>No Data</span>"}
    </div>
</div>
""", unsafe_allow_html=True)

# Main tabs
tab_scanner, tab_chart, tab_heatmap, tab_ml = st.tabs([
    "🔍 Scanner", 
    "📈 Chart Analysis", 
    "🔥 Heatmap",
    "🤖 ML Intelligence"  # The new ML tab
])

with tab_scanner:
    if st.session_state.results:
        # Filter results by min score
        filtered = [r for r in st.session_state.results if r.get("score", 0) >= min_score]
        
        # Show metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Total Results</div>
                <div class='metric-value'>{len(filtered)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_score = sum(r.get("score", 0) for r in filtered) / len(filtered) if filtered else 0
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Avg VCP Score</div>
                <div class='metric-value'>{avg_score:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            stage2_count = sum(1 for r in filtered if r.get("stage") == 2)
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Stage 2 Setups</div>
                <div class='metric-value'>{stage2_count}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            high_score_count = sum(1 for r in filtered if r.get("score", 0) >= 80)
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>High Score (80+)</div>
                <div class='metric-value'>{high_score_count}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Results table
        st.markdown("<div class='section-hdr'>Scan Results</div>", unsafe_allow_html=True)
        
        table_data = []
        for r in filtered:
            signals = r.get("signals", {})
            signal_tags = []
            if signals.get("volume_surge"):
                signal_tags.append("<span class='chip chip-green'>Vol↑</span>")
            if signals.get("tl_breakout"):
                signal_tags.append("<span class='chip chip-blue'>TL</span>")
            if signals.get("pivot_breakout"):
                signal_tags.append("<span class='chip chip-yellow'>Pivot</span>")
            
            stage = r.get("stage", 1)
            stage_class = f"s{stage}"
            
            table_data.append({
                "Ticker": r.get("ticker", ""),
                "Stage": f"<span class='stage-badge {stage_class}'>S{stage}</span>",
                "Score": f"<span style='font-family:JetBrains Mono; font-weight:600; color:#{('4ade80' if r.get('score', 0) >= 70 else 'fbbf24' if r.get('score', 0) >= 50 else 'f87171')}'>{r.get('score', 0):.1f}</span>",
                "RSI": f"<span style='font-family:JetBrains Mono'>{r.get('rsi', 0):.0f}</span>",
                "Vol": f"<span style='font-family:JetBrains Mono'>{r.get('vol_r', 0):.1f}×</span>",
                "Signals": " ".join(signal_tags),
                "Sector": r.get("sector", "—")
            })
        
        if table_data:
            df_display = pd.DataFrame(table_data)
            st.markdown(df_display.to_html(escape=False, index=False, classes='signal-table'), unsafe_allow_html=True)
        else:
            st.info("No results match the current filters")
    else:
        st.info("No scan results loaded. Click 'Load Scan Data' in the sidebar.")

with tab_chart:
    st.markdown("<div class='section-hdr'>Chart Analysis</div>", unsafe_allow_html=True)
    st.info("Select a ticker from the Scanner tab to view detailed chart analysis")
    
    if st.session_state.results:
        ticker = st.selectbox(
            "Select ticker",
            options=[r.get("ticker", "") for r in st.session_state.results],
            key="chart_ticker"
        )
        if ticker:
            st.write(f"Showing analysis for: {ticker}")
            # Chart would be rendered here using existing TVChart component

with tab_heatmap:
    st.markdown("<div class='section-hdr'>Sector Heatmap</div>", unsafe_allow_html=True)
    
    if st.session_state.results:
        # Simple sector aggregation
        from collections import defaultdict
        sector_scores = defaultdict(list)
        for r in st.session_state.results:
            sector = r.get("sector", "Unknown")
            score = r.get("score", 0)
            sector_scores[sector].append(score)
        
        sector_data = []
        for sector, scores in sector_scores.items():
            avg_score = sum(scores) / len(scores)
            sector_data.append({
                "Sector": sector,
                "Avg Score": f"{avg_score:.1f}",
                "Count": len(scores),
                "Top Setup": max(scores)
            })
        
        if sector_data:
            df_sectors = pd.DataFrame(sector_data).sort_values("Avg Score", ascending=False)
            st.dataframe(df_sectors, use_container_width=True, hide_index=True)
    else:
        st.info("Load scan data to see sector heatmap")

# ==============================================================================
# ML INTELLIGENCE TAB - INTEGRATION
# ==============================================================================

with tab_ml:
    # This is where the ML Intelligence Tab is integrated
    render_ml_tab(
        results=st.session_state.results,
        market_key=st.session_state.market_key,
        min_score=min_score
    )
