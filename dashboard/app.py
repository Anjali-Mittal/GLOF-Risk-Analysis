"""GLOF-RAS Intelligence Platform
Glacial Lake Outburst Flood Risk Assessment & Breach Hydrograph Analysis
Central & Eastern Himalayas (Koshi, Gandaki, Karnali, Tista)
"""

import os
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="GLOF-RAS Intelligence | Glacial Lake Risk Platform",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling
st.markdown("""
<style>
    /* Global & Typography */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Top Header */
    .brand-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0 1.25rem;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1.5rem;
    }
    .brand-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
    }
    .page-title {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.025em;
        margin-bottom: 0.2rem;
    }
    .page-subtitle {
        font-size: 0.94rem;
        color: #475569;
        margin-bottom: 1.75rem;
    }

    /* KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.25rem;
        margin-bottom: 1.75rem;
    }
    .kpi-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem 1.4rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .kpi-tag {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94A3B8;
    }
    .kpi-val {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.03em;
        margin: 6px 0 2px;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #64748B;
    }
    
    /* Badges */
    .badge-high { background-color: #FFF1F2; color: #E11D48; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
    .badge-med { background-color: #FFFBEB; color: #D97706; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
    .badge-safe { background-color: #ECFDF5; color: #059669; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load and merge live GLOF-RAS pipeline outputs."""
    vol_path = "outputs/tables/stage3_volume.csv"
    discharge_path = "outputs/tables/stage4_discharge.csv"
    labels_path = "data/labels/dangerous_lake_labels.csv"
    coef_path = "outputs/tables/stage2_coefficients.csv"
    features_terrain_path = "outputs/tables/stage2_features_terrain_rain.csv"
    features_growth_path = "outputs/tables/stage2_features_growth.csv"

    vol_df = pd.read_csv(vol_path) if os.path.exists(vol_path) else pd.DataFrame()
    dis_df = pd.read_csv(discharge_path) if os.path.exists(discharge_path) else pd.DataFrame()
    labels_df = pd.read_csv(labels_path) if os.path.exists(labels_path) else pd.DataFrame()
    coef_df = pd.read_csv(coef_path) if os.path.exists(coef_path) else pd.DataFrame()
    terrain_df = pd.read_csv(features_terrain_path) if os.path.exists(features_terrain_path) else pd.DataFrame()
    growth_df = pd.read_csv(features_growth_path) if os.path.exists(features_growth_path) else pd.DataFrame()

    # Merge Stage 3 and Stage 4
    if not vol_df.empty and not dis_df.empty:
        dis_cols = [c for c in dis_df.columns if c not in vol_df.columns or c == "lake_id"]
        master = vol_df.merge(dis_df[dis_cols], on="lake_id", how="left")
    else:
        master = vol_df

    # Merge Terrain & Rain features
    if not terrain_df.empty:
        t_cols = [c for c in ["slope_ring_mean_deg", "steep_frac", "rain_max5d_mm", "rain_p95_wetday_mm"] if c in terrain_df.columns]
        master = master.merge(terrain_df[["lake_id"] + t_cols], on="lake_id", how="left")

    # Merge Growth features
    if not growth_df.empty:
        g_cols = [c for c in ["growth_rate", "acceleration"] if c in growth_df.columns]
        master = master.merge(growth_df[["lake_id"] + g_cols], on="lake_id", how="left")

    # Merge Labels & Names
    if not labels_df.empty:
        merge_cols = [c for c in ["lat", "lon", "hazard_rank", "notes", "on_official_list"] if c in labels_df.columns and c not in master.columns]
        master = master.merge(labels_df[["lake_id"] + merge_cols], on="lake_id", how="left")

    master["display_name"] = master["name"].fillna(master["lake_id"])
    master["severity"] = np.where(master["risk_prob"] >= 0.70, "High Risk",
                         np.where(master["risk_prob"] >= 0.35, "Moderate", "Stable"))
    
    return master, coef_df


master_df, coef_df = load_data()

# Top Header Bar
col_brand, col_sel = st.columns([3, 1])
with col_brand:
    st.markdown('<div class="brand-title">GLOF-RAS Intelligence | Glacial Lake Risk Assessment</div>', unsafe_allow_html=True)
with col_sel:
    basins = ["All Basins"] + sorted(master_df["basin"].dropna().unique().tolist())
    selected_basin = st.selectbox("Basin Filter", basins, label_visibility="collapsed")

# Filter by basin if selected
view_df = master_df.copy()
if selected_basin != "All Basins":
    view_df = view_df[view_df["basin"] == selected_basin]

# Primary 3 Clean Views
tab1, tab2, tab3 = st.tabs(["Overview", "Lake Inventory & Discharge", "Case Benchmarks & Audit"])


# ==============================================================================
# TAB 1: OVERVIEW
# ==============================================================================
with tab1:
    st.markdown('<div class="page-title">Regional Glacial Lake Threat & Breach Overview</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Unified Stage 1–4 physical-statistical pipeline across 190 monitored lakes ({selected_basin}).</div>', unsafe_allow_html=True)

    # 4 KPI Cards Row
    total_lakes = len(view_df)
    flagged_count = int((view_df["risk_prob"] >= 0.50).sum())
    high_count = int((view_df["risk_prob"] >= 0.70).sum())
    mod_count = int(((view_df["risk_prob"] >= 0.35) & (view_df["risk_prob"] < 0.70)).sum())
    stable_count = int((view_df["risk_prob"] < 0.35).sum())
    
    tot_vol = view_df["vol_median"].sum() if "vol_median" in view_df.columns else 0
    vol_min_sum = view_df["vol_min"].sum() if "vol_min" in view_df.columns else 0
    vol_max_sum = view_df["vol_max"].sum() if "vol_max" in view_df.columns else 0
    
    max_qp = view_df["qp_primary_median"].max() if "qp_primary_median" in view_df.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-tag">LAKES MONITORED</div>
            <div class="kpi-val">{total_lakes}</div>
            <div class="kpi-sub"><strong>{flagged_count} flagged</strong> for bathymetry (P ≥ 0.50)</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-tag">TOTAL STORED WATER</div>
            <div class="kpi-val">{tot_vol:,.1f} <span style="font-size:0.9rem; color:#94A3B8;">MCM</span></div>
            <div class="kpi-sub">Envelope: {vol_min_sum:,.1f} – {vol_max_sum:,.1f} MCM</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-tag">HIGH RISK TIER (P ≥ 0.70)</div>
            <div class="kpi-val" style="color: #E11D48;">{high_count}</div>
            <div class="kpi-sub">{mod_count} Moderate · {stable_count} Stable</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-tag">MAX PEAK DISCHARGE (Qp)</div>
            <div class="kpi-val">{max_qp:,.0f} <span style="font-size:0.9rem; color:#94A3B8;">m³/s</span></div>
            <div class="kpi-sub">South Lhonak: 25,291 m³/s primary median</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Scientific Area vs Volume & Discharge Chart
    st.markdown("### Area vs Stored Volume & Peak Discharge Scaling")
    fig_scatter = px.scatter(
        view_df,
        x="area_s2_km2",
        y="vol_median",
        color="severity",
        color_discrete_map={"High Risk": "#E11D48", "Moderate": "#D97706", "Stable": "#059669"},
        size=view_df["qp_primary_median"].fillna(100).clip(lower=100, upper=35000),
        hover_name="display_name",
        hover_data={
            "basin": True,
            "risk_prob": ":.3f",
            "vol_median": ":.1f",
            "qp_primary_median": ":,.0f",
            "area_s2_km2": ":.3f"
        },
        labels={
            "area_s2_km2": "Sentinel-2 Surface Area (km²)",
            "vol_median": "Stored Volume (MCM)",
            "severity": "Hazard Tier"
        },
        log_x=True,
        log_y=True,
        height=400
    )
    fig_scatter.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#F1F5F9"),
        yaxis=dict(gridcolor="#F1F5F9")
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Basin & Physical Drivers Summary
    col_basin, col_coef = st.columns([1, 1])
    with col_basin:
        st.markdown("### Regional Basin Distribution")
        basin_summary = master_df.groupby("basin").agg(
            total_lakes=("lake_id", "count"),
            flagged_lakes=("risk_prob", lambda p: (p >= 0.50).sum()),
            stored_water_mcm=("vol_median", "sum")
        ).reset_index()
        basin_summary["stored_water_mcm"] = basin_summary["stored_water_mcm"].round(1)
        st.dataframe(basin_summary, hide_index=True, use_container_width=True)

    with col_coef:
        st.markdown("### Stage 2 Machine Learning Feature Weights")
        if not coef_df.empty:
            fig_coef = px.bar(
                coef_df.sort_values(by="coef_std", ascending=True),
                x="coef_std",
                y="feature",
                orientation="h",
                color="coef_std",
                color_continuous_scale="Reds",
                labels={"coef_std": "Standardized Weight (β)", "feature": "Feature"}
            )
            fig_coef.update_layout(
                height=240,
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                xaxis=dict(gridcolor="#F1F5F9")
            )
            st.plotly_chart(fig_coef, use_container_width=True)


# ==============================================================================
# TAB 2: LAKE INVENTORY & DISCHARGE
# ==============================================================================
with tab2:
    st.markdown('<div class="page-title">Lake Inventory, Volume & Breach Discharge</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Inspect Stage 3 empirical stored water volumes and Stage 4 peak breach discharge hydrographs.</div>', unsafe_allow_html=True)

    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])
    with col_filter1:
        search_query = st.text_input("Search Lakes", placeholder="Search by name, ID, or coordinates...", label_visibility="collapsed")
    with col_filter2:
        tier_filter = st.selectbox("Hazard Tier", ["All Tiers", "High Risk (P ≥ 0.70)", "Moderate (0.35–0.70)", "Stable (< 0.35)", "Flagged (P ≥ 0.50)"], label_visibility="collapsed")
    with col_filter3:
        sort_choice = st.selectbox("Sort By", ["Risk Probability (High to Low)", "Peak Discharge Qp (High to Low)", "Median Volume (Large to Small)", "Sentinel-2 Area (Large to Small)"], label_visibility="collapsed")

    filtered = view_df.copy()
    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered["display_name"].astype(str).str.lower().str.contains(q) |
            filtered["lake_id"].astype(str).str.lower().str.contains(q) |
            filtered["basin"].astype(str).str.lower().str.contains(q)
        ]

    if tier_filter == "High Risk (P ≥ 0.70)":
        filtered = filtered[filtered["risk_prob"] >= 0.70]
    elif tier_filter == "Moderate (0.35–0.70)":
        filtered = filtered[(filtered["risk_prob"] >= 0.35) & (filtered["risk_prob"] < 0.70)]
    elif tier_filter == "Stable (< 0.35)":
        filtered = filtered[filtered["risk_prob"] < 0.35]
    elif tier_filter == "Flagged (P ≥ 0.50)":
        filtered = filtered[filtered["risk_prob"] >= 0.50]

    if sort_choice == "Risk Probability (High to Low)":
        filtered = filtered.sort_values(by="risk_prob", ascending=False)
    elif sort_choice == "Peak Discharge Qp (High to Low)":
        filtered = filtered.sort_values(by="qp_primary_median", ascending=False)
    elif sort_choice == "Median Volume (Large to Small)":
        filtered = filtered.sort_values(by="vol_median", ascending=False)
    elif sort_choice == "Sentinel-2 Area (Large to Small)":
        filtered = filtered.sort_values(by="area_s2_km2", ascending=False)

    display_table = filtered[[
        "display_name", "lake_id", "basin", "area_s2_km2", "risk_prob",
        "vol_median", "vol_min", "vol_max",
        "qp_primary_median", "qp_evans", "qp_costa_vol", "qp_popov", "qp_froehlich"
    ]].rename(columns={
        "display_name": "Lake Name",
        "lake_id": "Lake ID",
        "basin": "Basin",
        "area_s2_km2": "Area (km²)",
        "risk_prob": "Risk Prob",
        "vol_median": "Vol Median (MCM)",
        "vol_min": "Vol Min (MCM)",
        "vol_max": "Vol Max (MCM)",
        "qp_primary_median": "Qp Median (m³/s)",
        "qp_evans": "Qp Evans",
        "qp_costa_vol": "Qp Costa",
        "qp_popov": "Qp Popov",
        "qp_froehlich": "Qp Froehlich"
    })

    st.dataframe(
        display_table.style.format({
            "Area (km²)": "{:.3f}",
            "Risk Prob": "{:.3f}",
            "Vol Median (MCM)": "{:.1f}",
            "Vol Min (MCM)": "{:.1f}",
            "Vol Max (MCM)": "{:.1f}",
            "Qp Median (m³/s)": "{:,.0f}",
            "Qp Evans": "{:,.0f}",
            "Qp Costa": "{:,.0f}",
            "Qp Popov": "{:,.0f}",
            "Qp Froehlich": "{:,.0f}"
        }),
        use_container_width=True,
        height=500
    )


# ==============================================================================
# TAB 3: CASE BENCHMARKS & AUDIT
# ==============================================================================
with tab3:
    st.markdown('<div class="page-title">Case Benchmarks & Ground Truth Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Rigorous verification of the GLOF-RAS pipeline against historical outburst events.</div>', unsafe_allow_html=True)

    col_case1, col_case2 = st.columns(2)

    with col_case1:
        st.markdown("""
        <div style="background:white; border:1px solid #E2E8F0; border-radius:12px; padding:1.5rem;">
            <span class="badge-safe">VERIFIED POSITIVE DETECTION</span>
            <h3 style="margin-top:8px;">South Lhonak Lake (Tista Basin, Sikkim)</h3>
            <p style="color:#64748B; font-size:0.85rem;">Catastrophic outburst on 4 October 2023. Real satellite drainage confirmed.</p>
            <div style="background:#ECFDF5; border-left:4px solid #059669; padding:10px 14px; border-radius:6px; color:#065F46; font-size:0.85rem; margin:10px 0;">
                <strong>Actual Drainage:</strong> Lake area dropped from <strong>1.130 km²</strong> (2022) to <strong>0.975 km²</strong> (2023 Sentinel-2), confirming massive drainage after an ice/rock avalanche trigger (Mohanty et al., 2026).
            </div>
            <ul style="font-size:0.85rem; line-height:1.7;">
                <li><strong>Pipeline Risk Prob:</strong> <span style="color:#E11D48; font-weight:700;">0.997</span> (Rank #2 Regional Threat)</li>
                <li><strong>Stored Volume:</strong> 40.9 – 44.6 MCM (Cook-Quincey: 44.6, Evans: 42.0, Huggel: 40.9)</li>
                <li><strong>Peak Discharge (Qp):</strong> 8,000 – 33,404 m³/s (Primary Median: 25,291 m³/s; Froehlich: 9,322 m³/s)</li>
                <li><strong>Ring Slope:</strong> 17.5° · <strong>5-Day Monsoon:</strong> 135.6 mm</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # South Lhonak Timeseries Chart
        ts_lhonak_path = "data/processed/lake_area_timeseries/SPECIAL_SOUTH_LHONAK.csv"
        if os.path.exists(ts_lhonak_path):
            l_df = pd.read_csv(ts_lhonak_path)
            l_df = l_df[l_df["source"] == "S2"].dropna(subset=["area_km2"])
            l_df["year"] = pd.to_datetime(l_df["date"]).dt.year
            fig_l = px.line(l_df, x="year", y="area_km2", markers=True, title="South Lhonak Post-Outburst Area Drop (Sentinel-2)")
            fig_l.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
            st.plotly_chart(fig_l, use_container_width=True)

    with col_case2:
        st.markdown("""
        <div style="background:white; border:1px solid #E2E8F0; border-radius:12px; padding:1.5rem;">
            <span class="badge-med">KNOWN ISSUE: POLYGON MISMATCH</span>
            <h3 style="margin-top:8px;">Thame Glacial Lake (Koshi Basin, Nepal)</h3>
            <p style="color:#64748B; font-size:0.85rem;">Outburst event on 16 August 2024. Audit of inventory polygon vs real burst source.</p>
            <div style="background:#FFFBEB; border-left:4px solid #D97706; padding:10px 14px; border-radius:6px; color:#92400E; font-size:0.85rem; margin:10px 0;">
                <strong>Polygon Mismatch Audit:</strong> The actual burst lake in August 2024 was a small supraglacial pond (~0.05 km²) releasing ~0.3–0.38 MCM. Monitored polygon <code>SPECIAL_THAME</code> tracks an adjacent 0.55 km² proglacial body (~15 MCM) which did not drain (0.54 km² in 2024 vs 0.55 km² in 2022).
            </div>
            <ul style="font-size:0.85rem; line-height:1.7;">
                <li><strong>Pipeline Risk Prob:</strong> <span style="color:#D97706; font-weight:700;">0.675</span> (Classified as Moderate Risk)</li>
                <li><strong>Tracked Volume:</strong> 15.1 MCM (~40× larger than actual ~0.35 MCM breach)</li>
                <li><strong>Peak Discharge (Qp):</strong> 4,600 – 13,889 m³/s (Reflects adjacent large lake)</li>
                <li><strong>Audit Conclusion:</strong> "2/2 detection" claim is invalid for Thame. Standard 30m inventory polygons fail to resolve micro-supraglacial ponds.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Thame Timeseries Chart
        ts_thame_path = "data/processed/lake_area_timeseries/SPECIAL_THAME.csv"
        if os.path.exists(ts_thame_path):
            t_df = pd.read_csv(ts_thame_path)
            t_df = t_df[t_df["source"] == "S2"].dropna(subset=["area_km2"])
            t_df["year"] = pd.to_datetime(t_df["date"]).dt.year
            fig_t = px.line(t_df, x="year", y="area_km2", markers=True, title="Tracked Polygon Shows No 2024 Breach Drop (Adjacent Lake)")
            fig_t.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF")
            st.plotly_chart(fig_t, use_container_width=True)
