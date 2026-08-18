# Abu Dhabi Real Estate Market Intelligence Dashboard

A production-grade, enterprise-level Streamlit dashboard for analysing the Abu Dhabi residential real estate market.

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the dashboard

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

---

## 📁 Project Structure

```
abu dhabi dashboard/
├── app.py                    ← Main Streamlit application
├── requirements.txt          ← Python dependencies
├── README.md                 ← This file
│
├── config/
│   ├── __init__.py
│   └── settings.py           ← App config, column names, colour palette
│
├── utils/
│   ├── __init__.py
│   └── data_loader.py        ← Data loading, cleaning, filtering utilities
│
├── styles/
│   ├── __init__.py
│   └── theme.py              ← CSS styles + Plotly layout helpers
│
├── components/
│   ├── __init__.py
│   └── ui_components.py      ← Reusable UI: KPI cards, section headers, etc.
│
├── charts/
│   ├── __init__.py
│   └── plotly_charts.py      ← All chart factory functions (Plotly)
│
├── .streamlit/
│   └── config.toml           ← Dark theme & server configuration
│
└── Abu_Dhabi_Sales_Cleaned (1).csv   ← Source data
```

---

## 🎛️ Dashboard Sections

| Tab | Description |
|-----|-------------|
| 📋 Business Insights | Auto-generated natural language insights |
| 📈 Sales Trends | Monthly/yearly/quarterly transaction trends |
| 🏘️ Geographic | Treemap, sunburst, bubble chart by district |
| 🏠 Property | Type, layout, sale category breakdowns |
| 💵 Price | Price trends, distribution, scatter plots |
| 📊 Distribution | Violin plots, density charts |
| 🕐 Time Series | Seasonality & YoY growth analysis |
| 🔗 Correlations | Interactive correlation heatmap |
| ⚠️ Outliers | Outlier detection and business explanation |
| 🔍 Data Quality | Missing values, column quality report |
| ⬇️ Download | CSV, Excel exports of filtered data |
| ℹ️ About | Column definitions, methodology, limitations |

---

## 🎨 Design Features

- **Glassmorphism** dark UI
- **Gradient KPI cards** with hover animations
- **Fully interactive Plotly charts** (hover, zoom, pan, download)
- **Real-time sidebar filters** — all charts update instantly
- **Corporate colour palette** (violet, teal, gold, coral)
- **Inter font** for premium typography
- **Responsive layout** across screen sizes

---

## 📊 Data Source

- **Dataset:** Abu Dhabi Sales Cleaned
- **Rows:** ~109,097 transactions
- **Period:** 2019 – 2026
- **Source:** Abu Dhabi Department of Municipalities and Transport (DMT)

---

## 🔧 Requirements

- Python 3.9+
- streamlit >= 1.35
- pandas >= 2.0
- plotly >= 5.18
- numpy >= 1.24
- openpyxl (for Excel export)
