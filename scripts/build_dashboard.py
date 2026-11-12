import json
import os
import pandas as pd

# Load master dataset
master_path = "outputs/tables/dashboard_master.json"
with open(master_path, "r", encoding="utf-8") as f:
    master_data = json.load(f)

print(f"Loaded {len(master_data)} lakes from {master_path}")

# Load timeseries for South Lhonak and Thame for the benchmark view
def get_ts(lake_id):
    path = f"data/processed/lake_area_timeseries/{lake_id}.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Filter valid records
        df = df.dropna(subset=['area_km2'])
        return [{"year": int(row['date'][:4]), "area": round(float(row['area_km2']), 4), "source": str(row['source'])} for _, row in df.iterrows()]
    return []

lhonak_ts = get_ts("SPECIAL_SOUTH_LHONAK")
thame_ts = get_ts("SPECIAL_THAME")

print(f"South Lhonak ts points: {len(lhonak_ts)}, Thame ts points: {len(thame_ts)}")

# Prepare coefficients data
coef_path = "outputs/tables/stage2_coefficients.csv"
coef_data = []
if os.path.exists(coef_path):
    cdf = pd.read_csv(coef_path)
    coef_data = cdf.to_dict(orient="records")

cv_path = "outputs/tables/stage2_cv_metrics.json"
cv_metrics = {}
if os.path.exists(cv_path):
    with open(cv_path, "r", encoding="utf-8") as f:
        cv_metrics = json.load(f)

# Build self-contained HTML
html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GLOF-RAS | Glacial Lake Risk & Breach Hydrograph Intelligence</title>
  
  <!-- Inter font -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    :root {
      --bg: #F8FAFC;
      --card-bg: #FFFFFF;
      --border: #E2E8F0;
      --text-main: #0F172A;
      --text-muted: #64748B;
      --text-sub: #94A3B8;
      --primary: #2563EB;
      --primary-light: #EFF6FF;
      --red: #E11D48;
      --red-light: #FFF1F2;
      --amber: #D97706;
      --amber-light: #FFFBEB;
      --teal: #059669;
      --teal-light: #ECFDF5;
      --radius: 12px;
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
      --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }

    /* Top Navigation Bar */
    header {
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    
    .nav-container {
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 2rem;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-badge {
      background: #0F172A;
      color: #FFFFFF;
      font-weight: 700;
      font-size: 0.85rem;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 0.04em;
    }

    .brand-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }

    .brand-subtitle {
      font-size: 0.8rem;
      color: var(--text-muted);
      border-left: 1px solid var(--border);
      padding-left: 10px;
      margin-left: 2px;
    }

    /* Nav Tabs */
    .nav-tabs {
      display: flex;
      gap: 8px;
      background: #F1F5F9;
      padding: 4px;
      border-radius: 10px;
    }

    .nav-tab {
      background: transparent;
      border: none;
      padding: 7px 18px;
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: 7px;
      transition: all 0.15s ease;
    }

    .nav-tab:hover {
      color: var(--text-main);
    }

    .nav-tab.active {
      background: var(--card-bg);
      color: var(--text-main);
      box-shadow: var(--shadow-sm);
    }

    /* Header Controls */
    .header-controls {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .basin-select {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 7px 14px;
      font-size: 0.88rem;
      font-weight: 500;
      color: var(--text-main);
      outline: none;
      cursor: pointer;
    }

    /* Main Container */
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 2rem;
    }

    /* View Handling */
    .view-pane {
      display: none;
    }

    .view-pane.active {
      display: block;
    }

    /* Page Header */
    .page-head {
      margin-bottom: 1.75rem;
    }

    .page-title {
      font-size: 1.6rem;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.025em;
      margin-bottom: 4px;
    }

    .page-subtitle {
      font-size: 0.92rem;
      color: var(--text-muted);
    }

    /* 4 Hero KPI Cards */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1.25rem;
      margin-bottom: 2rem;
    }

    .kpi-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.35rem 1.5rem;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .kpi-tag {
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--text-sub);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 6px;
    }

    .kpi-val {
      font-size: 2.1rem;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.03em;
      line-height: 1.1;
      margin-bottom: 4px;
    }

    .kpi-sub {
      font-size: 0.8rem;
      color: var(--text-muted);
      line-height: 1.35;
    }

    /* Generic Card */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      box-shadow: var(--shadow-sm);
      margin-bottom: 1.5rem;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.25rem;
    }

    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.01em;
    }

    .card-desc {
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-top: 2px;
    }

    /* Grid Layouts */
    .grid-2col {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .grid-halves {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    /* Pills */
    .pill-group {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .pill {
      background: #F1F5F9;
      border: 1px solid transparent;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .pill:hover {
      background: #E2E8F0;
      color: var(--text-main);
    }

    .pill.active {
      background: #0F172A;
      color: #FFFFFF;
    }

    /* Badges */
    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.76rem;
      font-weight: 600;
      letter-spacing: 0.02em;
    }

    .badge-high {
      background: var(--red-light);
      color: var(--red);
    }

    .badge-med {
      background: var(--amber-light);
      color: var(--amber);
    }

    .badge-stable {
      background: var(--teal-light);
      color: var(--teal);
    }

    /* Basin Stat Card */
    .basin-stat-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .basin-stat-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: #F8FAFC;
      border: 1px solid var(--border);
      border-radius: 8px;
    }

    .basin-stat-name {
      font-weight: 600;
      font-size: 0.88rem;
      color: var(--text-main);
    }

    .basin-stat-detail {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    /* VIEW 2: Split Sidebar Layout */
    .split-layout {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 1.5rem;
    }

    .filter-sidebar {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      height: fit-content;
      box-shadow: var(--shadow-sm);
    }

    .sidebar-section-title {
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--text-sub);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: 1rem 0 0.5rem;
    }

    .sidebar-section-title:first-child {
      margin-top: 0;
    }

    .sidebar-btn {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      background: transparent;
      border: none;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-muted);
      cursor: pointer;
      text-align: left;
      transition: all 0.15s ease;
    }

    .sidebar-btn:hover {
      background: #F1F5F9;
      color: var(--text-main);
    }

    .sidebar-btn.active {
      background: #0F172A;
      color: #FFFFFF;
      font-weight: 600;
    }

    .sidebar-btn.active .sidebar-count {
      background: rgba(255, 255, 255, 0.2);
      color: #FFFFFF;
    }

    .sidebar-count {
      font-size: 0.75rem;
      background: #F1F5F9;
      color: var(--text-muted);
      padding: 2px 7px;
      border-radius: 12px;
      font-weight: 600;
    }

    /* Table Toolbar */
    .table-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
      gap: 12px;
    }

    .search-input {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 0.88rem;
      color: var(--text-main);
      width: 320px;
      outline: none;
    }

    .search-input:focus {
      border-color: var(--primary);
    }

    .sort-select {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 0.85rem;
      color: var(--text-main);
      outline: none;
    }

    /* Clean Data Table */
    .table-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }

    .clean-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
    }

    .clean-table th {
      background: #F8FAFC;
      color: var(--text-muted);
      font-weight: 600;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .clean-table td {
      padding: 12px 16px;
      border-bottom: 1px solid #F1F5F9;
      color: var(--text-main);
      vertical-align: middle;
    }

    .clean-table tr:hover td {
      background: #F8FAFC;
    }

    .lake-name-cell {
      display: flex;
      flex-direction: column;
    }

    .lake-primary-name {
      font-weight: 600;
      color: var(--text-main);
    }

    .lake-sub-id {
      font-size: 0.75rem;
      color: var(--text-sub);
      font-family: monospace;
    }

    .action-btn {
      background: #F1F5F9;
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--text-main);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .action-btn:hover {
      background: #E2E8F0;
    }

    /* Modal / Drawer for Inspection */
    .modal-backdrop {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.4);
      backdrop-filter: blur(2px);
      z-index: 100;
      align-items: center;
      justify-content: center;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal-box {
      background: var(--card-bg);
      border-radius: 16px;
      width: 90%;
      max-width: 860px;
      max-height: 90vh;
      overflow-y: auto;
      padding: 2rem;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      position: relative;
    }

    .modal-close {
      position: absolute;
      top: 1.5rem;
      right: 1.5rem;
      background: #F1F5F9;
      border: none;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 700;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-close:hover {
      background: #E2E8F0;
      color: var(--text-main);
    }

    /* Inspection Metrics Grid */
    .inspect-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin: 1.5rem 0;
    }

    .inspect-card {
      background: #F8FAFC;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
    }

    .inspect-label {
      font-size: 0.72rem;
      color: var(--text-sub);
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .inspect-val {
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--text-main);
    }

    .inspect-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* Case Study Card */
    .case-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.75rem;
      box-shadow: var(--shadow-sm);
    }

    .case-badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 12px;
    }

    .alert-banner {
      background: #FEF2F2;
      border-left: 4px solid var(--red);
      padding: 14px 18px;
      border-radius: 6px;
      font-size: 0.88rem;
      color: #991B1B;
      margin: 1rem 0;
    }

    .warning-banner {
      background: #FFFBEB;
      border-left: 4px solid var(--amber);
      padding: 14px 18px;
      border-radius: 6px;
      font-size: 0.88rem;
      color: #92400E;
      margin: 1rem 0;
    }

    .pagination-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: #F8FAFC;
      border-top: 1px solid var(--border);
      font-size: 0.82rem;
      color: var(--text-muted);
    }

    .page-btns {
      display: flex;
      gap: 6px;
    }

    .page-btn {
      background: var(--card-bg);
      border: 1px solid var(--border);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
    }

    .page-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header>
    <div class="nav-container">
      <div class="brand-group">
        <span class="brand-badge">GLOF-RAS</span>
        <span class="brand-title">Glacial Lake Risk Intelligence</span>
        <span class="brand-subtitle">Himalayan Basin Monitoring</span>
      </div>

      <nav class="nav-tabs">
        <button class="nav-tab active" onclick="switchTab('overview')">Overview</button>
        <button class="nav-tab" onclick="switchTab('inventory')">Lake Inventory & Discharge</button>
        <button class="nav-tab" onclick="switchTab('benchmarks')">Case Benchmarks & Audit</button>
      </nav>

      <div class="header-controls">
        <select id="global-basin" class="basin-select" onchange="onGlobalBasinChange()">
          <option value="ALL">All Basins (190 Monitored)</option>
          <option value="Koshi">Koshi Basin (129 Lakes)</option>
          <option value="Gandaki">Gandaki Basin (19 Lakes)</option>
          <option value="Karnali">Karnali Basin (41 Lakes)</option>
          <option value="Tista">Tista Basin (1 Lake)</option>
        </select>
      </div>
    </div>
  </header>

  <!-- Main View Area -->
  <main>

    <!-- ======================================================== -->
    <!-- VIEW 1: OVERVIEW                                         -->
    <!-- ======================================================== -->
    <div id="view-overview" class="view-pane active">
      <div class="page-head">
        <h1 class="page-title">Regional Glacial Lake Threat & Breach Overview</h1>
        <p class="page-subtitle">Unified Stage 1–4 physical-statistical pipeline outputs across 190 monitored lakes in the Central & Eastern Himalayas.</p>
      </div>

      <!-- 4 Hero KPI Cards (Exact Verified Pipeline Numbers) -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-tag">LAKES MONITORED</div>
          <div class="kpi-val" id="kpi-lakes">190</div>
          <div class="kpi-sub"><strong>70 flagged</strong> for bathymetry priority (P ≥ 0.50)</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-tag">TOTAL STORED WATER VOLUME</div>
          <div class="kpi-val"><span id="kpi-volume">1,557.5</span> <span style="font-size:0.95rem; font-weight:600; color:var(--text-sub);">MCM</span></div>
          <div class="kpi-sub">Envelope: <strong>1,419.4 – 9,370.8 MCM</strong> across 4 empirical models</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-tag">HIGH RISK TIER (P ≥ 0.70)</div>
          <div class="kpi-val" style="color: var(--red);" id="kpi-high-risk">38</div>
          <div class="kpi-sub"><strong>55 Moderate</strong> (0.35–0.70) · <strong>97 Stable</strong> (<0.35)</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-tag">PEAK BREACH DISCHARGE (MAX)</div>
          <div class="kpi-val" id="kpi-max-qp">33,404 <span style="font-size:0.9rem; font-weight:600; color:var(--text-sub);">m³/s</span></div>
          <div class="kpi-sub">South Lhonak: <strong>25,291 m³/s</strong> median (Envelope 7,795–142,380)</div>
        </div>
      </div>

      <!-- Main Overview Grid -->
      <div class="grid-2col">
        <!-- Area vs Volume Scatter Chart -->
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Lake Area vs Stored Volume Landscape</div>
              <div class="card-desc">Log-scale empirical scaling. Point size indicates Peak Discharge (Qp). Click any lake to view details.</div>
            </div>
            <div class="pill-group">
              <button class="pill active" onclick="filterScatter('ALL', this)">All (190)</button>
              <button class="pill" onclick="filterScatter('HIGH', this)">High Risk (38)</button>
              <button class="pill" onclick="filterScatter('MOD', this)">Moderate (55)</button>
              <button class="pill" onclick="filterScatter('STABLE', this)">Stable (97)</button>
            </div>
          </div>
          <div style="height: 350px;">
            <canvas id="scatterChart"></canvas>
          </div>
        </div>

        <!-- Basin Breakdown -->
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Basin Risk Breakdown</div>
              <div class="card-desc">Flagged lakes (P ≥ 0.50) & regional stored water</div>
            </div>
          </div>
          <div class="basin-stat-list">
            <div class="basin-stat-item">
              <div>
                <div class="basin-stat-name">Koshi Basin</div>
                <div class="basin-stat-detail">129 monitored · 1,402 MCM median</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-high">63 Flagged</span>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top:2px;">48.8% of basin</div>
              </div>
            </div>

            <div class="basin-stat-item">
              <div>
                <div class="basin-stat-name">Gandaki Basin</div>
                <div class="basin-stat-detail">19 monitored · 86.4 MCM median</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-med">4 Flagged</span>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top:2px;">21.1% of basin</div>
              </div>
            </div>

            <div class="basin-stat-item">
              <div>
                <div class="basin-stat-name">Karnali Basin</div>
                <div class="basin-stat-detail">41 monitored · 27.6 MCM median</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-stable">2 Flagged</span>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top:2px;">4.9% of basin</div>
              </div>
            </div>

            <div class="basin-stat-item">
              <div>
                <div class="basin-stat-name">Tista Basin (Sikkim)</div>
                <div class="basin-stat-detail">1 monitored (South Lhonak) · 41.5 MCM</div>
              </div>
              <div style="text-align: right;">
                <span class="badge badge-high">1 Flagged</span>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top:2px;">100% of basin</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Feature Coefficients and Insights -->
      <div class="grid-halves">
        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Stage 2 Machine Learning Coefficients (Standardized)</div>
              <div class="card-desc">95% bootstrap confidence intervals from 5-fold grouped spatial CV (Spatial AUC = 0.870)</div>
            </div>
          </div>
          <div style="height: 240px;">
            <canvas id="coefChart"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <div class="card-title">Stage 4 Peak Discharge & Modeling Findings</div>
              <div class="card-desc">Hydraulic empirical formulations applied to all 190 lakes</div>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px; font-size: 0.85rem; color: var(--text-main);">
            <div style="padding: 10px 14px; background: #F8FAFC; border-radius: 8px; border: 1px solid var(--border);">
              <strong>Peak Discharge Formulations:</strong> Primary baseline uses Costa (1985), Evans (1986), and Popov (1991). Height-proxy methods include Costa (V·H) and Froehlich (1995) assuming h = 30m freeboard proxy.
            </div>
            <div style="padding: 10px 14px; background: #F8FAFC; border-radius: 8px; border: 1px solid var(--border);">
              <strong>Growth Acceleration Risk:</strong> 34 lakes show positive expansion acceleration (a > 0.02). Statistically significant driver (β = 0.471, 95% CI [0.05, 0.94]).
            </div>
            <div style="padding: 10px 14px; background: #F8FAFC; border-radius: 8px; border: 1px solid var(--border);">
              <strong>Monsoon Extreme Exposure:</strong> 5-day intense rainfall (rain_max5d_mm, β = 0.719) is the second highest risk determinant, linking summer overtopping to slope failures.
            </div>
          </div>
        </div>
      </div>
    </div>


    <!-- ======================================================== -->
    <!-- VIEW 2: LAKE INVENTORY & DISCHARGE (Screenshot 2 Split) -->
    <!-- ======================================================== -->
    <div id="view-inventory" class="view-pane">
      <div class="page-head">
        <h1 class="page-title">Lake Inventory, Volume & Breach Discharge</h1>
        <p class="page-subtitle">Filter, search, and analyze Stage 3 empirical stored water volumes and Stage 4 peak breach discharge hydrographs.</p>
      </div>

      <div class="split-layout">
        <!-- Sidebar Categories (Image 2 style) -->
        <aside class="filter-sidebar">
          <div class="sidebar-section-title">Hazard Tiers</div>
          <button class="sidebar-btn active" onclick="setCategoryFilter('ALL', this)">
            <span>All Monitored</span>
            <span class="sidebar-count" id="count-all">190</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('HIGH', this)">
            <span>High Risk (P ≥ 0.70)</span>
            <span class="sidebar-count" id="count-high">38</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('MOD', this)">
            <span>Moderate (0.35–0.70)</span>
            <span class="sidebar-count" id="count-mod">55</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('STABLE', this)">
            <span>Stable (< 0.35)</span>
            <span class="sidebar-count" id="count-stable">97</span>
          </button>

          <div class="sidebar-section-title">Basins</div>
          <button class="sidebar-btn" onclick="setCategoryFilter('BASIN_Koshi', this)">
            <span>Koshi Basin</span>
            <span class="sidebar-count">129</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('BASIN_Gandaki', this)">
            <span>Gandaki Basin</span>
            <span class="sidebar-count">19</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('BASIN_Karnali', this)">
            <span>Karnali Basin</span>
            <span class="sidebar-count">41</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('BASIN_Tista', this)">
            <span>Tista Basin</span>
            <span class="sidebar-count">1</span>
          </button>

          <div class="sidebar-section-title">Special Filters</div>
          <button class="sidebar-btn" onclick="setCategoryFilter('FLAGGED', this)">
            <span>Flagged (P ≥ 0.50)</span>
            <span class="sidebar-count">70</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('ACCEL', this)">
            <span>Accelerating Growth</span>
            <span class="sidebar-count">34</span>
          </button>
          <button class="sidebar-btn" onclick="setCategoryFilter('LARGE_VOL', this)">
            <span>High Volume (> 50 MCM)</span>
            <span class="sidebar-count">8</span>
          </button>
        </aside>

        <!-- Main Table Area -->
        <section>
          <div class="table-toolbar">
            <input type="text" id="lake-search" class="search-input" placeholder="Search by name, ID, or coordinates..." oninput="onSearchInput()">
            
            <div style="display: flex; gap: 8px; align-items: center;">
              <span style="font-size: 0.82rem; color: var(--text-muted); font-weight: 500;">Sort:</span>
              <select id="lake-sort" class="sort-select" onchange="onSortChange()">
                <option value="risk_desc">Risk Probability (Highest first)</option>
                <option value="qp_desc">Peak Discharge Qp (Highest first)</option>
                <option value="vol_desc">Median Volume (Largest first)</option>
                <option value="area_desc">Sentinel-2 Area (Largest first)</option>
                <option value="accel_desc">Growth Acceleration</option>
              </select>
            </div>
          </div>

          <div class="table-card">
            <table class="clean-table">
              <thead>
                <tr>
                  <th>Lake Identifier</th>
                  <th>Basin</th>
                  <th>S2 Area (km²)</th>
                  <th>Risk Tier</th>
                  <th>Stored Volume</th>
                  <th>Peak Discharge (Qp)</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="table-body">
                <!-- Dynamically populated -->
              </tbody>
            </table>

            <div class="pagination-bar">
              <span id="page-info">Showing 1 to 15 of 190 lakes</span>
              <div class="page-btns">
                <button class="page-btn" id="btn-prev" onclick="changePage(-1)">Previous</button>
                <button class="page-btn" id="btn-next" onclick="changePage(1)">Next</button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>


    <!-- ======================================================== -->
    <!-- VIEW 3: CASE BENCHMARKS & AUDIT                          -->
    <!-- ======================================================== -->
    <div id="view-benchmarks" class="view-pane">
      <div class="page-head">
        <h1 class="page-title">Case Benchmarks & Ground Truth Audit</h1>
        <p class="page-subtitle">Rigorous verification of the GLOF-RAS pipeline against historical outburst events.</p>
      </div>

      <div class="grid-halves">
        <!-- South Lhonak Case -->
        <div class="case-card">
          <span class="case-badge" style="background:#ECFDF5; color:#059669;">Verified Positive Detection</span>
          <h2 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 6px;">South Lhonak Lake (Tista Basin, Sikkim)</h2>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Catastrophic outburst on 4 October 2023. Real post-event satellite drainage confirmed.</p>

          <div class="alert-banner" style="background: #ECFDF5; border-color: #059669; color: #065F46;">
            <strong>Actual Drain Event:</strong> Lake surface dropped from <strong>1.130 km²</strong> (2022) to <strong>0.975 km²</strong> (2023 Sentinel-2), confirming catastrophic moraine dam breach after an ice/rock avalanche trigger (Mohanty et al., 2026).
          </div>

          <table class="clean-table" style="margin-bottom: 1.25rem;">
            <tbody>
              <tr>
                <td><strong>Pipeline Risk Probability:</strong></td>
                <td><strong style="color: var(--red); font-size:1.1rem;">0.997</strong> (Rank #2 Regional Threat)</td>
              </tr>
              <tr>
                <td><strong>Stored Volume:</strong></td>
                <td><strong>40.9 – 44.6 MCM</strong> (Cook-Quincey: 44.6, Evans: 42.0, Huggel: 40.9)</td>
              </tr>
              <tr>
                <td><strong>Peak Discharge (Qp):</strong></td>
                <td><strong>8,000 – 33,404 m³/s</strong> (Primary Median: 25,291 m³/s; Froehlich: 9,322 m³/s)</td>
              </tr>
              <tr>
                <td><strong>Moraine Ring Slope:</strong></td>
                <td><strong>17.5°</strong> (Steep fraction = 16.4%)</td>
              </tr>
              <tr>
                <td><strong>5-Day Monsoon Extreme:</strong></td>
                <td><strong>135.6 mm</strong></td>
              </tr>
            </tbody>
          </table>

          <div style="height: 220px;">
            <canvas id="lhonakChart"></canvas>
          </div>
        </div>

        <!-- Thame Lake Audit -->
        <div class="case-card">
          <span class="case-badge" style="background:#FFFBEB; color:#D97706;">Known Issue: Polygon Mismatch</span>
          <h2 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 6px;">Thame Glacial Lake (Koshi Basin, Nepal)</h2>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Outburst event on 16 August 2024. Audit of inventory polygon vs real burst source.</p>

          <div class="warning-banner">
            <strong>Polygon Mismatch Audit:</strong> The actual lake that burst in August 2024 was a small supraglacial pond (~0.05 km²) releasing ~0.3–0.38 MCM. Automated polygon <code>I2015_GL086586E27928N</code> tracks an adjacent 0.55 km² proglacial body (~15 MCM) which did not drain (area was 0.54 km² in 2024 vs 0.55 km² in 2022).
          </div>

          <table class="clean-table" style="margin-bottom: 1.25rem;">
            <tbody>
              <tr>
                <td><strong>Pipeline Risk Probability:</strong></td>
                <td><strong style="color: var(--amber); font-size:1.1rem;">0.675</strong> (Classified as Moderate Risk)</td>
              </tr>
              <tr>
                <td><strong>Pipeline Volume (Tracked Lake):</strong></td>
                <td><strong>15.1 MCM</strong> (~40× larger than actual ~0.35 MCM breach)</td>
              </tr>
              <tr>
                <td><strong>Pipeline Peak Discharge (Qp):</strong></td>
                <td><strong>4,600 – 13,889 m³/s</strong> (Reflects adjacent large body)</td>
              </tr>
              <tr>
                <td><strong>Validation Finding:</strong></td>
                <td>The claim of "2/2 detection" is invalid for Thame. Standard 30m inventory polygons do not resolve micro-supraglacial ponds.</td>
              </tr>
            </tbody>
          </table>

          <div style="height: 220px;">
            <canvas id="thameChart"></canvas>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- Inspection Modal Drawer -->
  <div id="lake-modal" class="modal-backdrop" onclick="onModalBackdropClick(event)">
    <div class="modal-box">
      <button class="modal-close" onclick="closeModal()">✕</button>
      
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
        <span class="badge" id="modal-tier-badge">High Risk</span>
        <span style="font-size: 0.82rem; color: var(--text-sub);" id="modal-basin-badge">Koshi Basin</span>
      </div>
      <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 4px;" id="modal-title">Lake Name</h2>
      <div style="font-family: monospace; font-size: 0.85rem; color: var(--text-muted);" id="modal-id">ID</div>

      <!-- Quick Metrics -->
      <div class="inspect-grid">
        <div class="inspect-card">
          <div class="inspect-label">Risk Probability</div>
          <div class="inspect-val" id="modal-prob">0.99</div>
          <div class="inspect-sub" id="modal-rank">Rank #1 of 190</div>
        </div>
        <div class="inspect-card">
          <div class="inspect-label">Stored Water Volume</div>
          <div class="inspect-val" id="modal-vol">54.2 MCM</div>
          <div class="inspect-sub" id="modal-vol-range">Range: 50.8 – 295.4 MCM</div>
        </div>
        <div class="inspect-card">
          <div class="inspect-label">Peak Breach Discharge (Qp)</div>
          <div class="inspect-val" id="modal-qp">25,291 m³/s</div>
          <div class="inspect-sub" id="modal-qp-range">Envelope: 8,032 – 33,404 m³/s</div>
        </div>
      </div>

      <!-- Volume & Discharge Models Breakdown -->
      <div class="grid-halves" style="margin-bottom: 1rem;">
        <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
          <h4 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; color: var(--text-sub);">Stage 3 Volume Formulations</h4>
          <table class="clean-table" style="background: transparent;">
            <tbody>
              <tr><td>Cook & Quincey (2015):</td><td style="text-align: right;"><strong id="modal-cq">-</strong></td></tr>
              <tr><td>Huggel et al. (2002):</td><td style="text-align: right;"><strong id="modal-huggel">-</strong></td></tr>
              <tr><td>Evans (1986):</td><td style="text-align: right;"><strong id="modal-evans-vol">-</strong></td></tr>
              <tr><td>O'Connor (2001, outlier):</td><td style="text-align: right;"><strong id="modal-oconnor">-</strong></td></tr>
            </tbody>
          </table>
        </div>

        <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
          <h4 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; color: var(--text-sub);">Stage 4 Breach Peak Discharge (Qp)</h4>
          <table class="clean-table" style="background: transparent;">
            <tbody>
              <tr><td>Popov (1991):</td><td style="text-align: right;"><strong id="modal-qp-popov">-</strong></td></tr>
              <tr><td>Costa (1985, Volume-only):</td><td style="text-align: right;"><strong id="modal-qp-costa">-</strong></td></tr>
              <tr><td>Evans (1986):</td><td style="text-align: right;"><strong id="modal-qp-evans">-</strong></td></tr>
              <tr><td>Froehlich (1995, h=30m proxy):</td><td style="text-align: right;"><strong id="modal-qp-froehlich">-</strong></td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Physical Features -->
      <div style="background: #F8FAFC; border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
        <h4 style="font-size: 0.85rem; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; color: var(--text-sub);">Terrain & Monsoon Coupling</h4>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 0.82rem;">
          <div><span style="color:var(--text-sub);">Sentinel-2 Area:</span> <br><strong id="modal-area">-</strong></div>
          <div><span style="color:var(--text-sub);">Growth Acceleration:</span> <br><strong id="modal-accel">-</strong></div>
          <div><span style="color:var(--text-sub);">Mean Ring Slope:</span> <br><strong id="modal-slope">-</strong></div>
          <div><span style="color:var(--text-sub);">5-Day Max Rainfall:</span> <br><strong id="modal-rain">-</strong></div>
        </div>
      </div>

    </div>
  </div>

  <!-- Raw Embedded Master Dataset -->
  <script>
    const MASTER_DATA = %MASTER_JSON%;
    const COEF_DATA = %COEF_JSON%;
    const LHONAK_TS = %LHONAK_TS_JSON%;
    const THAME_TS = %THAME_TS_JSON%;

    // State
    let currentTab = 'overview';
    let currentBasin = 'ALL';
    let currentCategory = 'ALL';
    let currentSearch = '';
    let currentSort = 'risk_desc';
    let currentPage = 1;
    const pageSize = 15;

    let scatterChartInst = null;
    let coefChartInst = null;
    let lhonakChartInst = null;
    let thameChartInst = null;

    // Tab Switching
    function switchTab(tabId) {
      currentTab = tabId;
      document.querySelectorAll('.view-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
      
      document.getElementById('view-' + tabId).classList.add('active');
      const tabs = Array.from(document.querySelectorAll('.nav-tab'));
      const activeIdx = tabId === 'overview' ? 0 : tabId === 'inventory' ? 1 : 2;
      tabs[activeIdx].classList.add('active');

      if (tabId === 'benchmarks') {
        initBenchmarkCharts();
      }
    }

    // Filter Logic
    function getFilteredLakes() {
      return MASTER_DATA.filter(lake => {
        // Basin filter
        if (currentBasin !== 'ALL' && lake.basin !== currentBasin) return false;

        // Category filter
        if (currentCategory === 'HIGH' && lake.risk_prob < 0.70) return false;
        if (currentCategory === 'MOD' && (lake.risk_prob < 0.35 || lake.risk_prob >= 0.70)) return false;
        if (currentCategory === 'STABLE' && lake.risk_prob >= 0.35) return false;
        if (currentCategory === 'FLAGGED' && lake.risk_prob < 0.50) return false;
        if (currentCategory === 'ACCEL' && (!lake.acceleration || lake.acceleration <= 0.02)) return false;
        if (currentCategory === 'LARGE_VOL' && (!lake.vol_median || lake.vol_median <= 50)) return false;
        if (currentCategory.startsWith('BASIN_')) {
          const reqBasin = currentCategory.replace('BASIN_', '');
          if (lake.basin !== reqBasin) return false;
        }

        // Search text
        if (currentSearch) {
          const q = currentSearch.toLowerCase();
          const name = (lake.name || '').toLowerCase();
          const id = (lake.lake_id || '').toLowerCase();
          const basin = (lake.basin || '').toLowerCase();
          if (!name.includes(q) && !id.includes(q) && !basin.includes(q)) return false;
        }

        return true;
      });
    }

    function sortLakes(lakes) {
      return lakes.sort((a, b) => {
        if (currentSort === 'risk_desc') return (b.risk_prob || 0) - (a.risk_prob || 0);
        if (currentSort === 'qp_desc') return (b.qp_primary_median || 0) - (a.qp_primary_median || 0);
        if (currentSort === 'vol_desc') return (b.vol_median || 0) - (a.vol_median || 0);
        if (currentSort === 'area_desc') return (b.area_s2_km2 || b.area || 0) - (a.area_s2_km2 || a.area || 0);
        if (currentSort === 'accel_desc') return (b.acceleration || -999) - (a.acceleration || -999);
        return 0;
      });
    }

    function renderTable() {
      const filtered = getFilteredLakes();
      const sorted = sortLakes(filtered);
      
      const total = sorted.length;
      const startIdx = (currentPage - 1) * pageSize;
      const endIdx = Math.min(startIdx + pageSize, total);
      const pageSlice = sorted.slice(startIdx, endIdx);

      const tbody = document.getElementById('table-body');
      tbody.innerHTML = '';

      if (pageSlice.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-muted);">No lakes found matching criteria.</td></tr>';
      } else {
        pageSlice.forEach(lake => {
          const tr = document.createElement('tr');
          
          let tierBadge = '<span class="badge badge-stable">Stable</span>';
          if (lake.risk_prob >= 0.70) tierBadge = '<span class="badge badge-high">High Risk</span>';
          else if (lake.risk_prob >= 0.35) tierBadge = '<span class="badge badge-med">Moderate</span>';

          const area = lake.area_s2_km2 ? lake.area_s2_km2.toFixed(3) : (lake.area ? lake.area.toFixed(3) : '-');
          const vol = lake.vol_median ? lake.vol_median.toFixed(1) : '-';
          const qp = lake.qp_primary_median ? Math.round(lake.qp_primary_median).toLocaleString() : '-';

          tr.innerHTML = `
            <td>
              <div class="lake-name-cell">
                <span class="lake-primary-name">${lake.name || lake.lake_id}</span>
                <span class="lake-sub-id">${lake.lake_id}</span>
              </div>
            </td>
            <td>${lake.basin || '-'}</td>
            <td>${area}</td>
            <td>${tierBadge} <span style="font-weight:600; font-size:0.8rem; margin-left:4px;">${lake.risk_prob ? lake.risk_prob.toFixed(3) : '-'}</span></td>
            <td><strong>${vol}</strong> <span style="font-size:0.75rem; color:var(--text-sub);">MCM</span></td>
            <td><strong style="color:${lake.qp_primary_median > 10000 ? 'var(--red)' : 'var(--text-main)'};">${qp}</strong> <span style="font-size:0.75rem; color:var(--text-sub);">m³/s</span></td>
            <td>
              <button class="action-btn" onclick='openModal(${JSON.stringify(lake.lake_id)})'>Inspect</button>
            </td>
          `;
          tbody.appendChild(tr);
        });
      }

      // Pagination
      document.getElementById('page-info').innerText = total === 0 ? 'Showing 0 lakes' : `Showing ${startIdx + 1} to ${endIdx} of ${total} lakes`;
      document.getElementById('btn-prev').disabled = currentPage <= 1;
      document.getElementById('btn-next').disabled = endIdx >= total;
    }

    function changePage(delta) {
      currentPage += delta;
      renderTable();
    }

    function onSearchInput() {
      currentSearch = document.getElementById('lake-search').value;
      currentPage = 1;
      renderTable();
    }

    function onSortChange() {
      currentSort = document.getElementById('lake-sort').value;
      renderTable();
    }

    function setCategoryFilter(cat, btn) {
      currentCategory = cat;
      document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentPage = 1;
      renderTable();
    }

    function onGlobalBasinChange() {
      currentBasin = document.getElementById('global-basin').value;
      currentPage = 1;
      renderTable();
      initScatterChart();
    }

    // Modal
    function openModal(lakeId) {
      const lake = MASTER_DATA.find(l => l.lake_id === lakeId);
      if (!lake) return;

      document.getElementById('modal-title').innerText = lake.name || lake.lake_id;
      document.getElementById('modal-id').innerText = lake.lake_id + (lake.lat ? ` · (${lake.lat.toFixed(3)}°N, ${lake.lon.toFixed(3)}°E)` : '');
      document.getElementById('modal-basin-badge').innerText = (lake.basin || 'Himalayas') + ' Basin';

      const tierBadge = document.getElementById('modal-tier-badge');
      if (lake.risk_prob >= 0.70) {
        tierBadge.className = 'badge badge-high';
        tierBadge.innerText = 'High GLOF Risk';
      } else if (lake.risk_prob >= 0.35) {
        tierBadge.className = 'badge badge-med';
        tierBadge.innerText = 'Moderate Risk';
      } else {
        tierBadge.className = 'badge badge-stable';
        tierBadge.innerText = 'Stable Lake';
      }

      document.getElementById('modal-prob').innerText = (lake.risk_prob || 0).toFixed(3);
      document.getElementById('modal-rank').innerText = lake.hazard_rank ? `Hazard Rank #${lake.hazard_rank} of 190` : 'Unranked';
      document.getElementById('modal-vol').innerText = (lake.vol_median || 0).toFixed(1) + ' MCM';
      document.getElementById('modal-vol-range').innerText = `Range: ${(lake.vol_min || 0).toFixed(1)} – ${(lake.vol_max || 0).toFixed(1)} MCM`;
      document.getElementById('modal-qp').innerText = Math.round(lake.qp_primary_median || 0).toLocaleString() + ' m³/s';
      document.getElementById('modal-qp-range').innerText = `Envelope: ${Math.round(lake.qp_low || 0).toLocaleString()} – ${Math.round(lake.qp_high || 0).toLocaleString()} m³/s`;

      // Formulations
      document.getElementById('modal-cq').innerText = lake.cook_quincey ? lake.cook_quincey.toFixed(1) + ' MCM' : '-';
      document.getElementById('modal-huggel').innerText = lake.huggel ? lake.huggel.toFixed(1) + ' MCM' : '-';
      document.getElementById('modal-evans-vol').innerText = lake.evans ? lake.evans.toFixed(1) + ' MCM' : '-';
      document.getElementById('modal-oconnor').innerText = lake.oconnor ? lake.oconnor.toFixed(1) + ' MCM' : '-';

      document.getElementById('modal-qp-popov').innerText = lake.qp_popov ? Math.round(lake.qp_popov).toLocaleString() + ' m³/s' : '-';
      document.getElementById('modal-qp-costa').innerText = lake.qp_costa_vol ? Math.round(lake.qp_costa_vol).toLocaleString() + ' m³/s' : '-';
      document.getElementById('modal-qp-evans').innerText = lake.qp_evans ? Math.round(lake.qp_evans).toLocaleString() + ' m³/s' : '-';
      document.getElementById('modal-qp-froehlich').innerText = lake.qp_froehlich ? Math.round(lake.qp_froehlich).toLocaleString() + ' m³/s' : '-';

      document.getElementById('modal-area').innerText = (lake.area_s2_km2 || lake.area || 0).toFixed(3) + ' km²';
      document.getElementById('modal-accel').innerText = lake.acceleration ? (lake.acceleration > 0 ? '+' : '') + lake.acceleration.toFixed(4) + '/yr²' : '-';
      document.getElementById('modal-slope').innerText = lake.slope_ring_mean_deg ? lake.slope_ring_mean_deg.toFixed(1) + '°' : '-';
      document.getElementById('modal-rain').innerText = lake.rain_max5d_mm ? lake.rain_max5d_mm.toFixed(1) + ' mm' : '-';

      document.getElementById('lake-modal').classList.add('open');
    }

    function closeModal() {
      document.getElementById('lake-modal').classList.remove('open');
    }

    function onModalBackdropClick(e) {
      if (e.target.id === 'lake-modal') closeModal();
    }

    // Charts
    function initScatterChart(filterTier = 'ALL') {
      const ctx = document.getElementById('scatterChart').getContext('2d');
      if (scatterChartInst) scatterChartInst.destroy();

      let lakes = MASTER_DATA;
      if (currentBasin !== 'ALL') lakes = lakes.filter(l => l.basin === currentBasin);
      if (filterTier === 'HIGH') lakes = lakes.filter(l => l.risk_prob >= 0.70);
      else if (filterTier === 'MOD') lakes = lakes.filter(l => l.risk_prob >= 0.35 && l.risk_prob < 0.70);
      else if (filterTier === 'STABLE') lakes = lakes.filter(l => l.risk_prob < 0.35);

      const highPoints = [];
      const modPoints = [];
      const stablePoints = [];

      lakes.forEach(l => {
        const pt = {
          x: l.area_s2_km2 || l.area,
          y: l.vol_median,
          name: l.name || l.lake_id,
          id: l.lake_id,
          prob: l.risk_prob,
          qp: l.qp_primary_median
        };
        if (l.risk_prob >= 0.70) highPoints.push(pt);
        else if (l.risk_prob >= 0.35) modPoints.push(pt);
        else stablePoints.push(pt);
      });

      scatterChartInst = new Chart(ctx, {
        type: 'scatter',
        data: {
          datasets: [
            {
              label: 'High Risk (P ≥ 0.70)',
              data: highPoints,
              backgroundColor: '#E11D48',
              pointRadius: 6
            },
            {
              label: 'Moderate (0.35–0.70)',
              data: modPoints,
              backgroundColor: '#D97706',
              pointRadius: 5
            },
            {
              label: 'Stable (< 0.35)',
              data: stablePoints,
              backgroundColor: '#059669',
              pointRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
            tooltip: {
              callbacks: {
                label: function(ctx) {
                  const p = ctx.raw;
                  return `${p.name}: Area=${p.x.toFixed(2)} km², Vol=${p.y.toFixed(1)} MCM, Qp=${Math.round(p.qp || 0).toLocaleString()} m³/s, P=${p.prob.toFixed(3)}`;
                }
              }
            }
          },
          scales: {
            x: {
              type: 'logarithmic',
              title: { display: true, text: 'Lake Surface Area (km², log-scale)' },
              grid: { color: '#F1F5F9' }
            },
            y: {
              type: 'logarithmic',
              title: { display: true, text: 'Stored Volume (MCM, log-scale)' },
              grid: { color: '#F1F5F9' }
            }
          },
          onClick: (e, elements) => {
            if (elements.length > 0) {
              const el = elements[0];
              const pt = scatterChartInst.data.datasets[el.datasetIndex].data[el.index];
              openModal(pt.id);
            }
          }
        }
      });
    }

    function filterScatter(tier, btn) {
      document.querySelectorAll('.pill-group .pill').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      initScatterChart(tier);
    }

    function initCoefChart() {
      const ctx = document.getElementById('coefChart').getContext('2d');
      if (coefChartInst) coefChartInst.destroy();

      // Top features from Stage 2
      const labels = ['log_area', 'rain_max5d_mm', 'rain_p95_wetday_mm', 'acceleration', 'steep_frac', 'slope_ring_mean_deg'];
      const values = [1.414, 0.719, 0.573, 0.471, 0.129, 0.108];
      const colors = values.map(v => v >= 0.45 ? '#E11D48' : '#64748B');

      coefChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Standardized Weight (β)',
            data: values,
            backgroundColor: colors,
            borderRadius: 4
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#F1F5F9' }, title: { display: true, text: 'Standardized Logistic Regression Weight' } },
            y: { grid: { display: false } }
          }
        }
      });
    }

    function initBenchmarkCharts() {
      if (lhonakChartInst) return; // already loaded

      // South Lhonak Chart
      const ctxL = document.getElementById('lhonakChart').getContext('2d');
      const s2Data = LHONAK_TS.filter(p => p.source === 'S2');
      
      lhonakChartInst = new Chart(ctxL, {
        type: 'line',
        data: {
          labels: s2Data.map(p => p.year.toString()),
          datasets: [{
            label: 'Sentinel-2 Area (km²)',
            data: s2Data.map(p => p.area),
            borderColor: '#E11D48',
            backgroundColor: 'rgba(225, 29, 72, 0.1)',
            fill: true,
            tension: 0.1,
            pointRadius: 5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: { display: true, text: 'South Lhonak Post-Outburst Area Drop (Oct 2023 GLOF)' },
            legend: { display: false }
          },
          scales: {
            y: { min: 0.8, max: 1.25, title: { display: true, text: 'Area (km²)' }, grid: { color: '#F1F5F9' } },
            x: { grid: { display: false } }
          }
        }
      });

      // Thame Chart
      const ctxT = document.getElementById('thameChart').getContext('2d');
      const thameS2 = THAME_TS.filter(p => p.source === 'S2');
      
      thameChartInst = new Chart(ctxT, {
        type: 'line',
        data: {
          labels: thameS2.map(p => p.year.toString()),
          datasets: [{
            label: 'Tracked Polygon Area (km²)',
            data: thameS2.map(p => p.area),
            borderColor: '#D97706',
            backgroundColor: 'rgba(217, 119, 6, 0.1)',
            fill: true,
            tension: 0.1,
            pointRadius: 5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: { display: true, text: 'Tracked Polygon Shows No 2024 Breach Drop (Adjacent Lake)' },
            legend: { display: false }
          },
          scales: {
            y: { min: 0.45, max: 0.65, title: { display: true, text: 'Area (km²)' }, grid: { color: '#F1F5F9' } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // Initialize on load
    window.addEventListener('DOMContentLoaded', () => {
      renderTable();
      initScatterChart();
      initCoefChart();
    });
  </script>
</body>
</html>
"""

# Replace placeholders
html_final = html_template.replace("%MASTER_JSON%", json.dumps(master_data))
html_final = html_final.replace("%COEF_JSON%", json.dumps(coef_data))
html_final = html_final.replace("%LHONAK_TS_JSON%", json.dumps(lhonak_ts))
html_final = html_final.replace("%THAME_TS_JSON%", json.dumps(thame_ts))

with open("dashboard/index.html", "w", encoding="utf-8") as f:
    f.write(html_final)

print("Successfully generated dashboard/index.html with full 190 lake dataset and Stage 4 Qp!")

