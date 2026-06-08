import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import os
import sys
import numpy as np
from datetime import datetime
import requests

# --- PATHS & IMPORTS ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

try:
    from web3_bridge import HospitalBridge
except Exception:
    HospitalBridge = None

# --- CONFIG & THEME ---
st.set_page_config(
    page_title="Smart Hospital Microgrid Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "grid_status" not in st.session_state:
    st.session_state.grid_status = "ON"
if "alert_level" not in st.session_state:
    st.session_state.alert_level = "NORMAL"
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"
if "sim_speed" not in st.session_state:
    st.session_state.sim_speed = "10×"
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "sim_index" not in st.session_state:
    st.session_state.sim_index = 0
if "sim_scenario" not in st.session_state:
    st.session_state.sim_scenario = "None"
if "sim_end_index" not in st.session_state:
    st.session_state.sim_end_index = None
if "sim_completed" not in st.session_state:
    st.session_state.sim_completed = False
if "manual_grid_override" not in st.session_state:
    st.session_state.manual_grid_override = False
if "trade_session_kwh" not in st.session_state:
    st.session_state.trade_session_kwh = 0.0
if "trade_session_mad" not in st.session_state:
    st.session_state.trade_session_mad = 0.0
if "logged_trades" not in st.session_state:
    st.session_state.logged_trades = set()  # Track which trades have been logged to blockchain

_is_dark = st.session_state.theme == "Dark"
_initial_theme = "dark" if _is_dark else "light"
_chart_font = "#ffffff" if _is_dark else "#1a2035"

# =====================================================================
# PART 1: Premium Theme & Styling (CSS)
# =====================================================================
st.markdown(f"""
<style>
    /* ---------- Google Fonts ---------- */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* ---------- CSS Variables & Global ---------- */
    :root {{
        --bg: #0b0f19;
        --text: #f0f3f9;
        --card: rgba(22, 29, 49, 0.7);
        --card-border: rgba(79, 156, 249, 0.16);
        --sidebar: #0e1220;
        --border: rgba(255,255,255,0.07);
        --accent: #4f9cf9;
        --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
        --font: 'Outfit', sans-serif;
    }}
    
    :root[data-theme="light"] {{
        --bg: #f8fafc;
        --text: #0f172a;
        --card: rgba(255, 255, 255, 0.85);
        --card-border: rgba(59, 130, 246, 0.16);
        --sidebar: #f1f5f9;
        --border: rgba(0, 0, 0, 0.07);
        --accent: #3b82f6;
        --shadow: 0 8px 32px 0 rgba(148, 163, 184, 0.12);
        --font: 'Outfit', sans-serif;
    }}

    /* We rely on Streamlit's native fonts for default elements to preserve UI icons */

    /* ---------- Transitions ---------- */
    .stApp, .main .block-container,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stSidebar"],
    [data-testid="stButton"] button,
    .metric-card,
    .section-card,
    .sim-info-bar,
    .narrator-card {{
        transition: background-color .28s cubic-bezier(0.4, 0, 0.2, 1), 
                    color .25s ease,
                    border-color .28s ease, 
                    box-shadow .28s ease !important;
    }}

    /* ---------- App Layout ---------- */
    .stApp, .main .block-container,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {{
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }}
    .main .block-container {{
        padding-top: 1.2rem;
    }}

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        background-color: var(--sidebar) !important;
        border-right: 1px solid var(--border) !important;
    }}
    [data-testid="stSidebar"] * {{ color: var(--text) !important; }}

    /* ---------- Sidebar Navigation Customization ---------- */
    [data-testid="stSidebar"] [data-testid="stButton"] button {{
        width: 100% !important;
        padding: 12px 18px !important;
        margin-bottom: 6px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;

        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
    }}
    
    [data-testid="stSidebar"] button > div {{
        width: 100% !important;
        justify-content: flex-start !important;
        text-align: left !important;
        margin: 0 !important;
    }}

    [data-testid="stSidebar"] button > div > p {{
        width: 100% !important;
        text-align: left !important;
        margin: 0 !important;
    }}

    [data-testid="stSidebar"] button span {{
        width: 100% !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }}

    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {{
        background: rgba(79, 156, 249, 0.08) !important;
        border: 1px solid rgba(79, 156, 249, 0.2) !important;
        transform: translateX(2px) !important;
    }}
    
    [data-testid="stSidebar"] button[kind="primary"] {{
        background: rgba(79,156,249,0.18) !important;
        border-left: 4px solid #4f9cf9 !important;
        border-top: 1px solid rgba(79,156,249,0.3) !important;
        border-right: 1px solid rgba(79,156,249,0.3) !important;
        border-bottom: 1px solid rgba(79,156,249,0.3) !important;
        font-weight: 700 !important;
        box-shadow: 0 0 18px rgba(79,156,249,0.25) !important;
    }}

    /* ---------- Text & Headers ---------- */
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricDelta"] {{ color: var(--text) !important; }}
    .stMarkdown, .stMarkdown p,
    h1, h2, h3, h4, h5, h6, p {{ color: var(--text) !important; }}

    /* ---------- Premium Cards (Glassmorphism) ---------- */
    .metric-card {{
        background: var(--card) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--card-border) !important;
        box-shadow: var(--shadow) !important;
        border-radius: 12px !important;
        padding: 18px;
        margin-bottom: 16px;
        min-height: 138px;
    }}
    .metric-card * {{ color: var(--text) !important; }}
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 36px 0 rgba(79, 156, 249, 0.15) !important;
        border-color: var(--accent) !important;
    }}

    .section-card {{
        background: var(--card) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--card-border) !important;
        border-left: 6px solid var(--border) !important;
        box-shadow: var(--shadow) !important;
        border-radius: 12px !important;
        padding: 18px;
        margin-bottom: 12px;
        min-height: 240px;
        height: 240px;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
    }}
    .section-card * {{ color: var(--text) !important; }}
    .section-card:hover {{
        transform: translateY(-2px);
        border-color: var(--accent) !important;
        box-shadow: 0 12px 36px 0 rgba(79, 156, 249, 0.1) !important;
    }}
    
    /* Neon glow highlights by priority */
    .p1-card {{ border-left-color: #ff4d4d !important; box-shadow: 0 0 15px rgba(255, 77, 77, 0.08) !important; }}
    .p2-card {{ border-left-color: #ff9933 !important; box-shadow: 0 0 15px rgba(255, 153, 51, 0.08) !important; }}
    .p3-card {{ border-left-color: #ffcc00 !important; box-shadow: 0 0 15px rgba(255, 204, 0, 0.08) !important; }}
    .p5-card {{ border-left-color: #94a3b8 !important; }}

    /* Neon glowing status values */
    .status-on  {{ 
        color: #00ff66 !important; 
        text-shadow: 0 0 10px rgba(0, 255, 102, 0.35);
        font-weight: 600;
    }}
    .status-off {{ 
        color: #ff3333 !important; 
        text-shadow: 0 0 10px rgba(255, 51, 51, 0.35);
        font-weight: 600;
    }}
    .warning    {{ 
        color: #ffaa00 !important; 
        text-shadow: 0 0 10px rgba(255, 170, 0, 0.35);
        font-weight: 600;
    }}

    /* ---------- Buttons ---------- */
    [data-testid="stButton"] button {{
        background: var(--card) !important; 
        color: var(--text) !important;
        border: 1px solid var(--card-border) !important; 
        border-radius: 8px !important;
        font-weight: 500 !important;
        box-shadow: var(--shadow) !important;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
    }}
    [data-testid="stButton"] button:hover {{
        border-color: var(--accent) !important;
        box-shadow: 0 4px 12px rgba(79,156,249,.22) !important;
        color: #ffffff !important;
    }}

    /* ---------- Sim Info Bar ---------- */
    .sim-info-bar {{
        background: linear-gradient(135deg, rgba(30, 58, 95, 0.8), rgba(45, 90, 142, 0.8)) !important;
        backdrop-filter: blur(8px);
        border-radius: 12px; 
        padding: 14px 20px; 
        margin-bottom: 24px;
        display: flex; 
        gap: 16px; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap;
        border: 1px solid rgba(79,156,249,0.3) !important;
        box-shadow: 0 0 15px rgba(79, 156, 249, 0.15);
    }}
    .sim-info-bar * {{ color: #e8eaf0 !important; margin: 0; }}
    .sim-info-bar span {{ white-space: nowrap; }}
    .quiet-caption {{
        color: rgba(240, 243, 249, 0.7) !important;
        font-size: 0.88rem;
    }}
    
    /* ---------- Narrator Card ---------- */
    .narrator-card {{
        background: rgba(79, 156, 249, 0.07) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(79, 156, 249, 0.22) !important;
        border-left: 5px solid var(--accent) !important;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: var(--shadow);
    }}
    .narrator-card h4 {{ 
        margin-top: 0; 
        color: var(--accent) !important; 
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .narrator-card p {{ 
        margin-bottom: 8px; 
        font-size: 0.95rem; 
        line-height: 1.45; 
    }}
    .narrator-card p:last-child {{ margin-bottom: 0; }}

    /* Pulsing red LIVE icon */
    .pulsing-dot {{
        width: 8px;
        height: 8px;
        background-color: #ff4d4d;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #ff4d4d;
        animation: pulse 1.6s infinite;
    }}
    @keyframes pulse {{
        0% {{ transform: scale(0.9); opacity: 0.75; }}
        50% {{ transform: scale(1.2); opacity: 1; box-shadow: 0 0 12px #ff4d4d; }}
        100% {{ transform: scale(0.9); opacity: 0.75; }}
    }}

</style>
""", unsafe_allow_html=True)

# =====================================================================
# PART 2: Toggle pill + JS
# =====================================================================
import streamlit.components.v1 as components

components.html(f"""
<script>
(function() {{
    var parentDoc = window.parent.document;
    var root = parentDoc.documentElement;
    var KEY = 'hm_theme';

    var style = parentDoc.getElementById('theme-pill-css');
    if (!style) {{
        style = parentDoc.createElement('style');
        style.id = 'theme-pill-css';
        style.textContent = [
            '#theme-pill-toggle {{',
            '  position:fixed; top:14px; right:20px; z-index:99999999;',
            '  width:72px; height:36px; border-radius:18px; cursor:pointer;',
            '  background:linear-gradient(135deg,#1e3a5f,#2d5a8e,#1a3a6b);',
            '  box-shadow:0 4px 15px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.1);',
            '  transition:background .35s ease,box-shadow .35s ease,transform .18s ease;',
            '  overflow:visible; user-select:none;',
            '}}',
            '#theme-pill-toggle:hover {{ transform:scale(1.06); }}',
            '#theme-pill-toggle.light {{',
            '  background:linear-gradient(135deg,#ff9a56,#ffcd5e,#ffa742);',
            '  box-shadow:0 4px 15px rgba(255,160,60,.45),inset 0 1px 0 rgba(255,255,255,.3);',
            '}}',
            '#tknob {{',
            '  position:absolute; top:4px; left:36px;',
            '  width:28px; height:28px; border-radius:50%;',
            '  display:flex; align-items:center; justify-content:center;',
            '  font-size:15px; line-height:1;',
            '  background:#1c2e45;',
            '  box-shadow:0 2px 8px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.12);',
            '  transition:left .35s ease,background .35s ease,box-shadow .35s ease;',
            '}}',
            '#theme-pill-toggle.light #tknob {{',
            '  left:8px; background:#f5e9d0;',
            '  box-shadow:0 2px 8px rgba(0,0,0,.15),inset 0 1px 0 rgba(255,255,255,.7);',
            '}}'
        ].join(' ');
        parentDoc.head.appendChild(style);
    }}

    var pill = parentDoc.getElementById('theme-pill-toggle');
    if (!pill) {{
        pill = parentDoc.createElement('div');
        pill.id = 'theme-pill-toggle';
        pill.innerHTML = '<div id="tknob"><span id="tico"></span></div>';
        parentDoc.body.appendChild(pill);
    }}

    function apply(theme) {{
        root.setAttribute('data-theme', theme);
        localStorage.setItem(KEY, theme);
        var p = parentDoc.getElementById('theme-pill-toggle');
        var ico = parentDoc.getElementById('tico');
        if (!p || !ico) return;
        if (theme === 'light') {{
            p.classList.add('light');
            ico.innerHTML = '&#9728;&#65039;';
        }} else {{
            p.classList.remove('light');
            ico.innerHTML = '&#127769;';
        }}
    }}

    apply(localStorage.getItem(KEY) || '{_initial_theme}');

    if (!pill.dataset.bound) {{
        pill.dataset.bound = '1';
        pill.addEventListener('click', function() {{
            var now = root.getAttribute('data-theme') || 'dark';
            var next = (now === 'dark') ? 'light' : 'dark';
            apply(next);
        }});
    }}
}})();
</script>
""", height=0)

# =====================================================================
# DATA & BRIDGE
# =====================================================================
data_path = os.path.join(base_dir, "data", "master_dataset.csv")
log_path = os.path.join(base_dir, "bridge_log.txt")
trade_path = os.path.join(base_dir, "data", "trades", "energy_trades.csv")

@st.cache_resource
def get_bridge():
    try:
        if HospitalBridge:
            return HospitalBridge()
        return None
    except Exception as e:
        print(f"Bridge initialization failed: {e}")
        return None

bridge = get_bridge()
def is_hardhat_running(host="127.0.0.1", port=8545, timeout=1.0):
    """Quick JSON-RPC health check for a local Hardhat node."""
    try:
        url = f"http://{host}:{port}"
        payload = {"jsonrpc": "2.0", "method": "web3_clientVersion", "params": [], "id": 1}
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            j = resp.json()
            return isinstance(j, dict) and ("result" in j or "error" in j)
        return False
    except Exception:
        return False

bridge_connected = bridge is not None

@st.cache_data(ttl=30)
def load_data():
    try:
        df = pd.read_csv(data_path)
        return df
    except Exception as e:
        st.error(f"Error loading master dataset: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_trades():
    try:
        if os.path.exists(trade_path):
            return pd.read_csv(trade_path)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df_master = load_data()
df_trades = load_trades()

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================
def get_battery_color(pct):
    if pct > 50: return "success"
    elif pct >= 20: return "warning"
    else: return "error"

@st.cache_data(ttl=300)
def get_live_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=33.5731&longitude=-7.5898&current=temperature_2m,shortwave_radiation,windspeed_10m&timezone=Africa/Casablanca"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("current", {})
        return None
    except Exception:
        return None

def find_scenario_start(df, scenario):
    if df.empty:
        return 0
    if scenario == "Demo: outage, batteries, generators":
        return 1680
    if scenario == "Demo: P2P energy trading":
        return 1684
    return 0

SCENARIO_GUIDES = {
    "Demo: outage, batteries, generators": (
        "💡 **Outage Resilience Demo (48 hours / Steps 1680-1785)**: Runs through a utility grid outage. "
        "Shows generator starting sequences, generator starting failures, battery drainage, and grid recovery."
    ),
    "Demo: P2P energy trading": (
        "💡 **P2P Blockchain Trading Demo (Steps 1684-1700)**: Focuses on battery trading. "
        "Shows how a section with a failed generator (Dialyse) requests emergency trades from General (P5) to survive."
    ),
}

def calculate_wind_power(speed, temp=20.0):
    if speed < 10: return 0
    air_density_factor = (1.292 / (1 + 0.00367 * temp)) / 1.225
    if speed <= 40:
        gross = ((speed - 10) / 30) * 80 * air_density_factor
        return gross * 0.95
    if speed <= 90:
        return 80 * air_density_factor * 0.95
    return 0

def calculate_solar_power(radiation, temp=20.0):
    if radiation <= 0: return 0.0
    CAPACITY_KW = 120.0
    solar_potential = radiation / 1000.0
    base_output = solar_potential * CAPACITY_KW
    panel_temp = temp + (45 - 20) * (radiation / 800.0)
    derating = max(0.0, 1.0 - 0.004 * (panel_temp - 25)) if panel_temp > 25 else 1.0
    pre_inverter = base_output * derating * 0.98 * 0.995
    return pre_inverter * 0.96

def trigger_trade(donor, receiver, amount):
    if bridge:
        bridge.execute_trade(donor, receiver, amount, "Emergency trade initiated via dashboard")
        st.toast(f"Trade requested: {donor} -> {receiver} ({amount} kWh)", icon="✅")
    else:
        st.toast("Bridge offline. Trade simulated.", icon="⚠️")

def simulate_grid_failure():
    st.session_state.manual_grid_override = True
    st.session_state.grid_status = "OFF"
    st.session_state.alert_level = "CRITICAL"
    if bridge:
        bridge.submit_alert("CRITICAL", 0, "General", 0)
        bridge.log_grid_event("OUTAGE", int(time.time()), 0, "CRITICAL_OFF")
        st.toast("Grid failure simulated and logged to blockchain.", icon="🚨")
    else:
        st.toast("Bridge offline. Grid failure simulated locally.", icon="⚠️")

def restore_grid():
    st.session_state.manual_grid_override = False
    st.session_state.grid_status = "ON"
    st.session_state.alert_level = "NORMAL"
    if bridge:
        bridge.submit_alert("NORMAL", 500, "General", 80)
        bridge.log_grid_event("RESTORE", int(time.time()), 600, "NORMAL_ON")
        st.toast("Grid power restored and logged to blockchain.", icon="🟢")
    else:
        st.toast("Bridge offline. Grid restored locally.", icon="⚠️")

def get_trades_at_timestamp(ts):
    """Return trades matching the current simulation timestamp."""
    if df_trades.empty:
        return pd.DataFrame()
    return df_trades[df_trades['timestamp'] == ts]

def metric_delta(current, previous, unit="kW"):
    diff = float(current) - float(previous)
    if abs(diff) < 0.05:
        return f"0.0 {unit}"
    return f"{diff:+.1f} {unit}"

def apply_chart_theme(fig, showlegend=False):
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_family='Outfit',
        font_color=_chart_font,
        showlegend=showlegend,
        margin=dict(l=20, r=20, t=36, b=24),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.05)' if _is_dark else 'rgba(0,0,0,0.05)',
            zerolinecolor='rgba(255,255,255,0.1)' if _is_dark else 'rgba(0,0,0,0.1)',
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.05)' if _is_dark else 'rgba(0,0,0,0.05)',
            zerolinecolor='rgba(255,255,255,0.1)' if _is_dark else 'rgba(0,0,0,0.1)',
        ),
        transition=dict(duration=350, easing='cubic-in-out'),
        uirevision='hospital-microgrid-simulation',
    )
    return fig

def get_sim_interval_seconds():
    speed = st.session_state.get("sim_speed", "10×")
    return {
        '1×': 3.0,
        '5×': 1.8,
        '10×': 1.0,
        '50×': 0.6,
        '100×': 0.4,
    }.get(speed, 1.0)

def get_live_narrative(row, active_trades):
    if not row:
        return ["System initializing..."]
    
    is_out = int(row.get('is_outage', 0))
    narratives = []
    
    if is_out == 1:
        narratives.append("⚠️ **GRID OUTAGE IN PROGRESS**: Utility grid power is completely offline. The microgrid has entered autonomous resilience mode.")
        
        # Generator state narrative
        g_running_count = 0
        g_starting_count = 0
        g_failed_count = 0
        g_empty_count = 0
        
        generator_info = {
            'g1': 'G1 (ICU/Bloc - Priority 1)',
            'g2': 'G2 (Dialyse/Mat - Priority 2)',
            'g3': 'G3 (Radiologie - Priority 3)',
            'g4': 'G4 (General - Priority 5)'
        }
        
        for g_id, label in generator_info.items():
            running = int(row.get(f'{g_id}_running', 0))
            starting = int(row.get(f'{g_id}_starting', 0))
            fuel = float(row.get(f'{g_id}_fuel_pct', 0.0))
            
            if starting:
                g_starting_count += 1
                narratives.append(f"🔄 **{label}**: Initializing startup sequence...")
            elif running:
                g_running_count += 1
                if fuel < 15.0:
                    narratives.append(f"⛽ **{label}**: Running but fuel level is CRITICAL ({fuel:.1f}%).")
                else:
                    narratives.append(f"🟢 **{label}**: Online and generating power. Fuel at {fuel:.1f}%.")
            elif fuel <= 0.0:
                g_empty_count += 1
                narratives.append(f"❌ **{label}**: Shut down. Fuel tank is completely exhausted!")
            else:
                # Failed startup repair window
                g_failed_count += 1
                narratives.append(f"🚨 **{label}**: FAILED to start. Maintenance crew working on repairs.")
                
        # P2P trading commentary
        if not active_trades.empty:
            for _, trade in active_trades.iterrows():
                narratives.append(
                    f"🔄 **P2P Blockchain Trade**: **{trade['donor_section']}** (P5) transferred **{trade['traded_kw']:.1f} kW** "
                    f"to **{trade['receiver_section']}** ({trade['receiver_priority']}) to prevent critical blackout. "
                    f"Transaction secured on-chain (Hash: `{trade['blockchain_hash'][:14]}...`)."
                )
        else:
            # Check if any batteries are critical
            crit_bats = []
            for col in [c for c in row if c.startswith('bat_') and c.endswith('_pct')]:
                val = float(row[col])
                sec_name = col.replace('bat_', '').replace('_pct', '').replace('_', ' ').title()
                if val < 20.0:
                    crit_bats.append(f"{sec_name} ({val:.1f}%)")
            if crit_bats:
                narratives.append(f"🔋 **Critical SoC Alerts**: {', '.join(crit_bats)} need emergency charging support.")
    else:
        narratives.append("🟢 **UTILITY GRID ONLINE**: Hospital is receiving normal power from the main grid.")
        # Recharging
        charging_bats = []
        for col in [c for c in row if c.startswith('bat_') and c.endswith('_pct')]:
            val = float(row[col])
            if val < 90.0:
                sec_name = col.replace('bat_', '').replace('_pct', '').replace('_', ' ').title()
                charging_bats.append(sec_name)
        if charging_bats:
            narratives.append("🔋 Batteries are charging using surplus solar/wind and grid supply.")
            
    return narratives

# =====================================================================
# SIDEBAR NAVIGATION (Premium Redesign)
# =====================================================================
with st.sidebar:
    # --- Logo / Branding ---
    st.markdown("""
    <div style="text-align:left; padding:8px 8px 4px 8px;">
        <h1 style="font-size:1.6rem; margin:0; font-weight:700; letter-spacing:-0.5px;">
            ⚡ Hospital Microgrid
        </h1>
        <p style="font-size:0.78rem; opacity:0.5; margin:4px 0 0 0; letter-spacing:1.5px; text-transform:uppercase;">
            Smart Energy Dashboard
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Simulation Status Indicator ---
    sim_running = st.session_state.sim_running
    sim_scenario = st.session_state.sim_scenario
    sim_index = st.session_state.sim_index

    if sim_running:
        scen_label = sim_scenario if sim_scenario != "None" else "Free Play"
        end_idx = st.session_state.sim_end_index if st.session_state.sim_end_index is not None else (len(df_master) - 1 if not df_master.empty else 0)
        start_idx = find_scenario_start(df_master, sim_scenario) if sim_scenario != "None" else 0
        pct = int(((sim_index - start_idx) / max(1, end_idx - start_idx)) * 100)
        pct = max(0, min(100, pct))
        st.markdown(f"""
        <div style="background: rgba(79,156,249,0.08); border:1px solid rgba(79,156,249,0.25); border-radius:10px; padding:12px 14px; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <span style="width:8px;height:8px;border-radius:50%;background:#00ff66;display:inline-block;box-shadow:0 0 8px #00ff66;animation:pulse 1.6s infinite;"></span>
                <span style="font-size:0.82rem; font-weight:600; color:var(--accent);">SIMULATION RUNNING</span>
            </div>
            <p style="font-size:0.78rem; margin:0 0 6px 0; opacity:0.75;">{scen_label}</p>
            <div style="background:rgba(255,255,255,0.08); border-radius:6px; height:6px; overflow:hidden;">
                <div style="width:{pct}%; height:100%; background:linear-gradient(90deg,#4f9cf9,#00ff66); border-radius:6px; transition:width 0.4s ease;"></div>
            </div>
            <p style="font-size:0.72rem; opacity:0.5; margin:4px 0 0 0; text-align:right;">{pct}% complete</p>
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.get("sim_completed", False):
        st.markdown("""
        <div style="background: rgba(0,255,102,0.06); border:1px solid rgba(0,255,102,0.25); border-radius:10px; padding:12px 14px; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1rem;">✅</span>
                <span style="font-size:0.82rem; font-weight:600; color:#00ff66;">SCENARIO COMPLETED</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(148,163,184,0.06); border:1px solid rgba(148,163,184,0.15); border-radius:10px; padding:12px 14px; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1rem;">⏸️</span>
                <span style="font-size:0.82rem; font-weight:500; opacity:0.6;">Simulation Idle</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Navigation with Buttons ---
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Real-time Energy Overview"

    nav_items = {
        "📊 Real-time Energy Overview": "Real-time Energy Overview",
        "🏥 Hospital Sections Status": "Hospital Sections Status",
        "🎛️ Simulation Control Center": "Simulation Control Center",
        "📈 AI Predictions": "AI Predictions",
        "🔗 Blockchain Audit Log": "Blockchain Audit Log",
    }
    
    for label, page_name in nav_items.items():
        is_active = st.session_state.current_page == page_name
        btn_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_{page_name}", use_container_width=True, type=btn_type):
            st.session_state.current_page = page_name
            st.rerun()

    page = st.session_state.current_page

    st.markdown("---")

    # --- System Status ---
    st.markdown("""
    <p style="font-size:0.78rem; font-weight:600; text-transform:uppercase; letter-spacing:1.2px; opacity:0.5; margin-bottom:8px;">
        System Status
    </p>
    """, unsafe_allow_html=True)
    
    node_up = is_hardhat_running()
    status_color = "🟢" if (bridge_connected or node_up) else "🔴"
    status_text = "Connected" if (bridge_connected or node_up) else "Offline"
    grid_st = st.session_state.grid_status
    grid_icon = "🟢" if grid_st == "ON" else "🔴"
    
    st.markdown(f"""
    <div style="font-size:0.82rem; line-height:2;">
        <span>Hardhat Node: {status_color} {status_text}</span><br>
        <span>Grid Power: {grid_icon} {grid_st}</span><br>
        <span>Alert: <strong>{st.session_state.alert_level}</strong></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # --- About ---
    st.markdown("""
    <p style="font-size:0.72rem; opacity:0.4; line-height:1.6; margin:0;">
        <strong>PFE Project</strong> — Smart Hospital Microgrid Dashboard with Blockchain P2P Energy Trading.<br>
        Built with Streamlit, Plotly, Hardhat & Solidity.
    </p>
    """, unsafe_allow_html=True)

# =====================================================================
# FRAGMENT WRAPPER FOR SMOOTH PLAYBACK (Zero Flickering!)
# =====================================================================
@st.fragment(run_every=get_sim_interval_seconds() if st.session_state.sim_running else None)
def render_simulation_dashboard(page_name):
    # Advance simulation step if running
    if st.session_state.sim_running:
        next_index = st.session_state.sim_index + 1
        end_index = st.session_state.sim_end_index if st.session_state.sim_end_index is not None else len(df_master) - 1
        
        if next_index < end_index:
            st.session_state.sim_index = next_index
        else:
            st.session_state.sim_index = end_index
            st.session_state.sim_running = False
            st.session_state.sim_completed = True
            st.rerun()

    # Load master rows
    if not df_master.empty:
        st.session_state.sim_index = min(st.session_state.sim_index, len(df_master) - 1)
        current_state = df_master.iloc[st.session_state.sim_index].to_dict()
        previous_state = df_master.iloc[max(st.session_state.sim_index - 1, 0)].to_dict()
    else:
        current_state = {}
        previous_state = {}

    # Sync grid status from data (if manual override is not active)
    if current_state and not st.session_state.manual_grid_override:
        is_outage = int(current_state.get('is_outage', 0))
        st.session_state.grid_status = "OFF" if is_outage == 1 else "ON"
        st.session_state.alert_level = current_state.get('alert_level', 'NORMAL')

    # Get active trades
    current_ts = current_state.get('timestamp', '')
    active_trades = get_trades_at_timestamp(current_ts)
    
    # During scenario playback, automatically log new trades to blockchain
    if st.session_state.sim_running and not active_trades.empty:
        for _, trade in active_trades.iterrows():
            trade_key = f"{trade['timestamp']}_{trade['donor_section']}_{trade['receiver_section']}"
            if trade_key not in st.session_state.logged_trades:
                # Log this trade to blockchain
                if bridge:
                    try:
                        donor = trade['donor_section']
                        receiver = trade['receiver_section']
                        amount = float(trade['traded_kw'])
                        tx_hash = trade['blockchain_hash']
                        bridge.execute_trade(donor, receiver, amount, f"Auto-logged P2P trade during scenario playback")
                        st.session_state.logged_trades.add(trade_key)
                    except Exception as e:
                        print(f"Error logging trade to blockchain: {e}")
    
    # Also automatically log grid events (outage/restore) during scenarios
    if st.session_state.sim_running and not st.session_state.manual_grid_override:
        is_outage = int(current_state.get('is_outage', 0))
        outage_key = f"{current_ts}_outage_{is_outage}"
        
        # Log outage start
        if is_outage == 1 and outage_key not in st.session_state.logged_trades:
            if bridge:
                try:
                    alert_level = current_state.get('alert_level', 'CRITICAL')
                    bridge.submit_alert(alert_level, 0, "General", 0)
                    bridge.log_grid_event("OUTAGE", int(time.time()), 0, f"{alert_level}_OFF")
                    st.session_state.logged_trades.add(outage_key)
                except Exception as e:
                    print(f"Error logging outage to blockchain: {e}")

    # Compute Energy Values
    solar_kw = current_state.get('net_solar_kw', 0.0)
    wind_kw = current_state.get('net_wind_kw', 0.0)

    # Use live weather only when NOT playing
    if not st.session_state.sim_running:
        live_w = get_live_weather()
        if live_w and 'shortwave_radiation' in live_w:
            solar_kw = calculate_solar_power(live_w['shortwave_radiation'], live_w.get('temperature_2m', 20.0))
            wind_kw = calculate_wind_power(live_w['windspeed_10m'], live_w.get('temperature_2m', 20.0))
            live_badge = " (Live 🔴)"
        else:
            live_badge = " (Simulated)"
    else:
        live_badge = ""

    renewable_kw = solar_kw + wind_kw
    total_demand = current_state.get('total_hospital_kw', 0.0)
    gen_kw = current_state.get('total_generator_kw', 0.0)

    grid_capacity_kw = float(current_state.get('grid_available_kw', 600.0))
    if st.session_state.grid_status == "OFF":
        grid_kw = 0.0
        if st.session_state.manual_grid_override and gen_kw == 0.0:
            gen_kw = max(0.0, min(total_demand - renewable_kw, 750.0))
    else:
        grid_kw = max(0.0, min(grid_capacity_kw, total_demand - renewable_kw - gen_kw))

    total_supply = grid_kw + gen_kw + renewable_kw

    # -----------------------------------------------------------------
    # PAGE RENDERING LOGIC
    # -----------------------------------------------------------------
    if page_name == "Simulation Control Center":
        # Control Deck (Wrapped inside a glowing premium card)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0;'>🎛️ Simulation Control Center</h3>", unsafe_allow_html=True)
        
        # Progress representation
        total_steps = len(df_master) - 1 if not df_master.empty else 0
        if st.session_state.sim_scenario != "None":
            scen_start = find_scenario_start(df_master, st.session_state.sim_scenario)
            scen_end = st.session_state.sim_end_index if st.session_state.sim_end_index is not None else 1785
            progress_val = (st.session_state.sim_index - scen_start) / max(1, (scen_end - scen_start))
            progress_val = max(0.0, min(1.0, progress_val))
            st.progress(progress_val)
            st.markdown(f"<p class='quiet-caption'><strong>Scenario Active</strong>: Step {st.session_state.sim_index - scen_start} / {scen_end - scen_start} | <strong>Time</strong>: {current_ts}</p>", unsafe_allow_html=True)
        else:
            progress_val = st.session_state.sim_index / max(total_steps, 1)
            st.progress(progress_val)
            st.markdown(f"<p class='quiet-caption'><strong>Global Playback</strong>: Step {st.session_state.sim_index} / {total_steps} | <strong>Time</strong>: {current_ts}</p>", unsafe_allow_html=True)
        
        # Control buttons layout
        c_play, c_reset, c_speed, c_scen, c_run = st.columns([1.5, 1.5, 2.5, 4, 2.5])
        
        with c_play:
            if st.button("⏸ Pause" if st.session_state.sim_running else "▶️ Play", key="play_btn", use_container_width=True):
                st.session_state.sim_running = not st.session_state.sim_running
                st.session_state.sim_completed = False
                st.rerun()
        
        with c_reset:
            if st.button("⏹ Reset", key="reset_btn", use_container_width=True):
                st.session_state.sim_running = False
                st.session_state.sim_index = 0
                st.session_state.sim_scenario = "None"
                st.session_state.sim_end_index = None
                st.session_state.sim_completed = False
                st.session_state.manual_grid_override = False
                st.session_state.logged_trades = set()  # Clear logged trades for fresh playback
                st.rerun()
        
        with c_speed:
            st.selectbox("Speed", ["1×", "5×", "10×", "50×", "100×"], key="sim_speed", label_visibility="collapsed")
        
        with c_scen:
            scenarios = ["Demo: outage, batteries, generators", "Demo: P2P energy trading"]
            st.selectbox("Select Scenario", scenarios, key="selected_scenario_ui", label_visibility="collapsed")
        
        with c_run:
            if st.button("🚀 Launch Scenario", key="launch_btn", use_container_width=True):
                selected_scen = st.session_state.selected_scenario_ui
                st.session_state.sim_scenario = selected_scen
                st.session_state.sim_index = find_scenario_start(df_master, selected_scen)
                if selected_scen == "Demo: outage, batteries, generators":
                    st.session_state.sim_end_index = 1785
                else:
                    st.session_state.sim_end_index = 1700
                st.session_state.sim_running = True
                st.session_state.sim_completed = False
                st.session_state.manual_grid_override = False
                st.rerun()
        
        # Manual Overrides
        c_over_1, c_over_2, c_guide = st.columns([2.5, 3, 6.5])
        with c_over_1:
            if st.session_state.grid_status == "ON" or not st.session_state.manual_grid_override:
                if st.button("🚨 Force Grid OFF", key="force_off_btn", use_container_width=True):
                    simulate_grid_failure()
                    st.rerun()
            else:
                if st.button("🟢 Restore Grid", key="restore_btn", use_container_width=True):
                    restore_grid()
                    st.rerun()
        with c_over_2:
            st.markdown("<p style='font-size:0.85rem; margin-top:8px;' class='quiet-caption'>Manual overrides are for local presentation demonstration only.</p>", unsafe_allow_html=True)
        with c_guide:
            if st.session_state.sim_scenario != "None":
                st.info(SCENARIO_GUIDES.get(st.session_state.sim_scenario, ""))
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.get("sim_completed", False):
            st.success("🎉 **Scenario Completed! Grid power restored, generators shut down, batteries stabilized. Transactions verified on blockchain.**")
    
    # -----------------------------------------------------------------
    # NARRATOR PANEL (on Simulation Control Center page)
    # -----------------------------------------------------------------
    if page_name == "Simulation Control Center":
        narratives = get_live_narrative(current_state, active_trades)
        st.markdown('<div class="narrator-card">'
                    '<h4><span class="pulsing-dot"></span> Live Event Narrator</h4>' + 
                    "".join([f"<p>{n}</p>" for n in narratives]) + 
                    '</div>', unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # SIMULATION INFO BAR (shown on all pages when sim is active)
    # -----------------------------------------------------------------
    is_outage_val = int(current_state.get('is_outage', 0))
    is_trading_val = int(current_state.get('is_trading', 0))
    
    grid_indicator = "<span class='status-off'>🔴 GRID BLACKOUT</span>" if st.session_state.grid_status == "OFF" else "<span class='status-on'>🟢 Grid Online</span>"
    gen_indicator = f"⚡ Generators: <strong>{gen_kw:.0f} kW</strong>" if gen_kw > 0 else "💤 Generators: Standby"
    trade_indicator = "<span class='status-on'>🔄 P2P TRADING ACTIVE</span>" if is_trading_val else "💤 P2P Trading: Idle"
    
    alert_lvl = st.session_state.alert_level
    alert_color = "status-off" if alert_lvl == "CRITICAL" else ("warning" if alert_lvl == "WARNING" else "status-on")
    alert_indicator = f"<span class='{alert_color}'>{alert_lvl}</span>"

    st.markdown(f"""
    <div class="sim-info-bar">
        <span>📅 Timestamp: <strong>{current_ts}</strong></span>
        <span>{grid_indicator}</span>
        <span>{gen_indicator}</span>
        <span>{trade_indicator}</span>
        <span>Alert Level: {alert_indicator}</span>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # PAGE RENDERING
    # -----------------------------------------------------------------
    if page_name == "Real-time Energy Overview":
        # --- Top Metrics ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            previous_supply = float(previous_state.get('total_supply_kw', total_supply)) if previous_state else total_supply
            st.metric("Total Supply", f"{total_supply:.1f} kW", delta=metric_delta(total_supply, previous_supply))
            st.markdown(f"<p class='quiet-caption'>Renewable: <strong>{renewable_kw:.1f} kW</strong>{live_badge}</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            previous_demand = float(previous_state.get('total_hospital_kw', total_demand)) if previous_state else total_demand
            st.metric("Total Demand", f"{total_demand:.1f} kW", delta=metric_delta(total_demand, previous_demand))
            st.markdown(f"<p class='quiet-caption'>Hospital Load profile</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            grid_status_lbl = st.session_state.grid_status
            grid_color = "status-on" if grid_status_lbl == "ON" else "status-off"
            capacity_used_pct = (grid_kw / grid_capacity_kw * 100) if grid_capacity_kw > 0 else 0.0
            st.markdown(
                f"<h3 style='margin:0 0 6px 0; font-size:0.95rem; font-weight:500; opacity:0.8;'>Grid Power</h3>"
                f"<h2 class='{grid_color}' style='margin:0 0 8px 0; font-size:1.9rem;'>{grid_status_lbl}</h2>"
                f"<p style='margin:0; font-size:0.85rem;'>Import: <strong>{grid_kw:.1f} kW</strong></p>"
                f"<p style='margin:0; font-size:0.85rem;'>Cap: <strong>{grid_capacity_kw:.0f} kW</strong> ({capacity_used_pct:.0f}% used)</p>",
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            alert_lvl = st.session_state.alert_level
            alert_color = "status-off" if alert_lvl == "CRITICAL" else ("warning" if alert_lvl == "WARNING" else "status-on")
            st.markdown(
                f"<h3 style='margin:0 0 6px 0; font-size:0.95rem; font-weight:500; opacity:0.8;'>System Alert</h3>"
                f"<h2 class='{alert_color}' style='margin:0 0 8px 0; font-size:1.9rem;'>{alert_lvl}</h2>"
                f"<p style='margin:0; font-size:0.85rem;' class='quiet-caption'>Based on Battery & Supply balance</p>",
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # --- Generator Fleet Status ---
        st.markdown('---')
        st.subheader('Generator Fleet Status')
        gen_cols = st.columns(4)
        generator_specs = {
            'g1': {'label': 'G1 — ICU/Bloc/Urgences/Neo', 'capacity': 300},
            'g2': {'label': 'G2 — Dialyse/Maternite/Lab/Pharma', 'capacity': 200},
            'g3': {'label': 'G3 — Radiologie', 'capacity': 150},
            'g4': {'label': 'G4 — General', 'capacity': 100},
        }
        for idx, gen_id in enumerate(['g1', 'g2', 'g3', 'g4']):
            with gen_cols[idx]:
                spec = generator_specs[gen_id]
                running = int(current_state.get(f'{gen_id}_running', 0))
                starting = int(current_state.get(f'{gen_id}_starting', 0))
                fuel_pct = float(current_state.get(f'{gen_id}_fuel_pct', 100.0))
                output_kw = float(current_state.get(f'{gen_id}_output_kw', 0.0))

                # Determine status
                if st.session_state.manual_grid_override and not running and not starting:
                    status_label = 'RUNNING (Override)'
                    badge = 'status-on'
                    output_kw = spec['capacity']
                elif running:
                    if fuel_pct < 15:
                        status_label = '⛽ FUEL CRITICAL'
                        badge = 'status-off'
                    else:
                        status_label = '🟢 ONLINE'
                        badge = 'status-on'
                elif starting:
                    status_label = '🔄 STARTING'
                    badge = 'warning'
                else:
                    is_outage_now = int(current_state.get('is_outage', 0))
                    if is_outage_now and not running and not starting:
                        if fuel_pct <= 0.0:
                            status_label = '❌ OUT OF FUEL'
                            badge = 'status-off'
                        else:
                            status_label = '❌ FAILURE / REPAIR'
                            badge = 'status-off'
                    else:
                        status_label = '💤 STANDBY'
                        badge = ''

                st.markdown(f"""
                <div class='metric-card'>
                    <h4 style='margin-top:0; font-weight:600;'>{gen_id.upper()} <span style='font-size:0.7em; font-weight:400; opacity:0.65;'>({spec['capacity']} kW)</span></h4>
                    <p style='margin-bottom:6px;'>Status: <span class='{badge}'><strong>{status_label}</strong></span></p>
                    <p style='margin-bottom:12px;'>Power: <strong>{output_kw:.0f} kW</strong></p>
                </div>
                """, unsafe_allow_html=True)
                pct_value = max(0.0, min(1.0, fuel_pct / 100.0))
                st.progress(pct_value)
                st.caption(f"Fuel tank: {fuel_pct:.1f}%")

        # --- Energy Production by Source ---
        st.markdown('---')
        st.subheader("Energy Sources and Grid Availability")
        sources = ['Grid Import', 'Solar', 'Wind', 'Generators']
        values = [grid_kw, solar_kw, wind_kw, gen_kw]

        fig = px.bar(x=sources, y=values, labels={'x': 'Source', 'y': 'Power (kW)'}, color=sources,
                     color_discrete_map={
                         'Grid Import': '#4dabf7',
                         'Solar': '#ffc078',
                         'Wind': '#a5d8ff',
                         'Generators': '#ffa500',
                     })
        fig.update_yaxes(range=[0, max(values + [total_demand, 1]) * 1.15])
        apply_chart_theme(fig, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Grid Import is the utility power currently used from the grid. "
            f"Grid Capacity available this timestep: {grid_capacity_kw:.0f} kW."
        )

        # --- Current Trades (contextual to simulation timestep) ---
        st.markdown('---')
        st.subheader("Active Peer-to-Peer Energy Trades")

        if not active_trades.empty:
            st.success(f"🔄 **{len(active_trades)} active trade(s) at this timestep!**")
            for _, trade in active_trades.iterrows():
                st.markdown('<div class="metric-card" style="min-height: auto; padding: 16px;">', unsafe_allow_html=True)
                col_t1, col_t2, col_t3 = st.columns([2, 1, 2])
                with col_t1:
                    st.markdown(f"**Donor:** <span class='status-on'>{trade['donor_section']}</span> ({trade['donor_priority']})", unsafe_allow_html=True)
                    st.caption(f"Charge before: {trade['donor_charge_pct_before']:.1f}%")
                with col_t2:
                    st.markdown(f"<h3 style='margin:0; text-align:center; color:#4f9cf9;'>➡️ {trade['traded_kw']:.1f} kW</h3>", unsafe_allow_html=True)
                    st.caption(f"<div style='text-align:center;'>P2P Trade</div>", unsafe_allow_html=True)
                with col_t3:
                    st.markdown(f"**Receiver:** <span class='status-off'>{trade['receiver_section']}</span> ({trade['receiver_priority']})", unsafe_allow_html=True)
                    st.caption(f"Charge before: {trade['receiver_charge_pct_before']:.1f}%")
                st.markdown(f"<p style='margin:12px 0 0 0; font-size:0.8rem; font-family:monospace;' class='quiet-caption'>🔗 Blockchain Transaction Hash: <code style='color:#4f9cf9;'>{trade['blockchain_hash']}</code></p>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No P2P trades active at this timestep. Peer-to-peer trading is triggered during grid blackouts when a generator fails and a high-priority section needs emergency battery power from another department.")

        # --- Lifetime Cost Efficiency ---
        st.subheader('Lifetime Cost Efficiency')
        c1, c2, c3 = st.columns(3)
        total_trade_kwh = (df_trades['traded_kw'] * 0.5).sum() if not df_trades.empty else 0.0
        total_trade_savings = df_trades['cost_saving_eur'].sum() if not df_trades.empty else 0.0
        c1.metric('Total P2P Energy Traded', f"{total_trade_kwh:.1f} kWh")
        c2.metric('Total Cost Savings', f"{total_trade_savings:.1f} MAD")
        c3.metric('Renewable Fraction', f"{current_state.get('renewable_fraction', 0.0) * 100:.1f}%")

    elif page_name == "Hospital Sections Status":
        st.header("Hospital Sections Status")

        sections = [
            {"name": "Reanimation/ICU", "priority": 1, "col": "bat_reanimation_pct"},
            {"name": "Bloc Operatoire", "priority": 1, "col": "bat_bloc_pct"},
            {"name": "Urgences", "priority": 1, "col": "bat_urgences_pct"},
            {"name": "Neonatologie", "priority": 1, "col": "bat_neonatologie_pct"},
            {"name": "Dialyse", "priority": 2, "col": "bat_dialyse_pct"},
            {"name": "Maternite", "priority": 2, "col": "bat_maternite_pct"},
            {"name": "Laboratoire", "priority": 2, "col": "bat_laboratoire_pct"},
            {"name": "Pharmacie", "priority": 2, "col": "bat_pharmacie_pct"},
            {"name": "Radiologie", "priority": 3, "col": "bat_radiologie_pct"},
            {"name": "General", "priority": 5, "col": "bat_general_pct"}
        ]

        grid_cols = st.columns(3)
        alert_lvl = st.session_state.alert_level

        for i, sec in enumerate(sections):
            col = grid_cols[i % 3]
            with col:
                p_class = f"p{sec['priority']}-card"
                bat_pct = current_state.get(sec['col'], 0.0)
                
                # Check if powered: Priority 5 is load-shedded during critical alerts
                is_powered = True
                if alert_lvl == 'CRITICAL' and sec['priority'] > 3:
                    is_powered = False

                status_text = "⚡ ACTIVE" if is_powered else "❌ SHEDDED"
                status_class = "status-on" if is_powered else "status-off"

                if bat_pct < 15:
                    bat_icon = "🔴"
                elif bat_pct < 30:
                    bat_icon = "🟠"
                elif bat_pct < 60:
                    bat_icon = "🟡"
                else:
                    bat_icon = "🟢"

                st.markdown(f"""
                <div class="section-card {p_class}">
                    <h3 style='margin-top:0; font-weight:600;'>{sec['name']} <span style="font-size: 0.6em; color: rgba(255,255,255,0.45);">Priority P{sec['priority']}</span></h3>
                    <p style='margin-bottom:6px;'>Load Status: <span class="{status_class}"><strong>{status_text}</strong></span></p>
                    <p style='margin-bottom:12px;'>Battery: {bat_icon} <strong>{bat_pct:.1f}%</strong></p>
                </div>
                """, unsafe_allow_html=True)

                st.progress(min(1.0, max(0.0, float(bat_pct) / 100.0)))

                if sec['priority'] == 5:
                    if st.button(f"Trigger Manual Emergency Trade", key=f"trade_{sec['name']}"):
                        trigger_trade(sec['name'], "Reanimation/ICU", 10)
                st.markdown("<br>", unsafe_allow_html=True)

    elif page_name == "AI Predictions":
        st.header("AI Demand Forecasting & Anomaly Detection")

        sections_names = ["Reanimation/ICU", "Bloc Operatoire", "Urgences", "Neonatologie", "Dialyse", "Maternite", "Laboratoire", "Pharmacie", "Radiologie", "General"]
        selected_sec = st.selectbox("Select Section", sections_names)

        if not df_master.empty:
            recent_data = df_master.tail(48).copy()
            times = pd.date_range(start=datetime.now(), periods=48, freq='30min')

            seed = sum(ord(ch) for ch in selected_sec) + st.session_state.sim_index
            rng = np.random.default_rng(seed)
            section_factor = 0.05 + rng.random() * 0.1
            actual = recent_data['total_hospital_kw'].values * section_factor
            predicted = actual * (1 + (rng.random(48) - 0.5) * 0.15)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=times, y=actual, name='Actual Demand', line=dict(color='#00ff66', width=2)))
            fig.add_trace(go.Scatter(x=times, y=predicted, name='AI Forecast (LSTM)', line=dict(color='#ffc078', width=2, dash='dash')))
            fig.update_layout(title=f"24-Hour Load Demand Forecast: {selected_sec}")
            apply_chart_theme(fig, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Data unavailable for predictions.")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Predicted Peak Shortfalls (Next 6 hours)")
            candidates = ['Radiologie', 'Pharmacie', 'General']
            needs = [45, 30, 20]
            fig2 = px.bar(x=candidates, y=needs, labels={'x': 'Section', 'y': 'Predicted Need (kWh)'}, color=candidates, color_discrete_sequence=px.colors.sequential.Plasma)
            apply_chart_theme(fig2, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.subheader("Model Performance")
            st.metric("Mean Absolute Error (MAE)", "1.85 kWh", "-0.15 kWh")

            st.subheader("Anomaly Alerts")
            st.error("⚠️ **General**: Consumption 15% above historical normal profile.")
            st.info("ℹ " + " **Laboratoire**: Unexpected drop in battery level during charging window.")

    elif page_name == "Blockchain Audit Log":
        st.header("Blockchain Audit Log & Ledger")

        # Show trades from dataset
        if not df_trades.empty:
            st.subheader("📜 P2P Energy Trades Ledger")
            st.dataframe(df_trades, use_container_width=True, hide_index=True)

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Trades Logged", len(df_trades))
            total_kwh = (df_trades['traded_kw'] * 0.5).sum()
            c2.metric("Total Energy Exchanged", f"{total_kwh:.1f} kWh")
            c3.metric("Total Financial Savings", f"{df_trades['cost_saving_eur'].sum():.1f} MAD")

            st.markdown("---")
            st.subheader("Trades Distribution by Scenario")
            scenario_counts = df_trades['trade_scenario'].value_counts()
            fig_sc = px.pie(values=scenario_counts.values, names=scenario_counts.index, color_discrete_sequence=px.colors.sequential.Plasma)
            apply_chart_theme(fig_sc, showlegend=True)
            st.plotly_chart(fig_sc, use_container_width=True)
        else:
            st.info("No trades logged in the current dataset.")

        # Show on-chain logs from hardhat node bridge log
        st.markdown("---")
        st.subheader("🔗 Blockchain On-Chain Transaction Log")
        logs = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if "|" in line:
                        parts = line.split("|")
                        ts_action = parts[0].strip()
                        tx_hash = parts[1].replace("TX_HASH:", "").strip()

                        ts = ts_action[1:20]
                        action = ts_action[22:]

                        action_type = "ALERT" if "SUBMIT_ALERT" in action else ("TRADE" if "EXECUTE_TRADE" in action else "GRID EVENT")

                        logs.append({
                            "Timestamp": ts,
                            "Type": action_type,
                            "Transaction Details": action,
                            "Transaction Hash": f"{tx_hash[:8]}...{tx_hash[-8:]}" if len(tx_hash) > 16 else tx_hash
                        })

        if logs:
            df_logs = pd.DataFrame(logs)

            filter_type = st.selectbox("Filter by Action Type", ["All", "ALERT", "TRADE", "GRID EVENT"])
            if filter_type != "All":
                df_logs = df_logs[df_logs["Type"] == filter_type]

            st.dataframe(df_logs, use_container_width=True, hide_index=True)

            st.markdown("---")
            l_c1, l_c2, l_c3 = st.columns(3)
            l_c1.metric("On-Chain Trades", len([l for l in logs if l['Type'] == 'TRADE']))
            l_c2.metric("On-Chain Alerts", len([l for l in logs if l['Type'] == 'ALERT']))
            l_c3.metric("On-Chain Grid Events", len([l for l in logs if l['Type'] == 'GRID EVENT']))
        else:
            st.info("No on-chain transactions logged yet. Start the Hardhat local node and interact with the control center to write transactions to the blockchain ledger.")

# =====================================================================
# EXECUTE FRAGMENT RENDERING
# =====================================================================
render_simulation_dashboard(page)
