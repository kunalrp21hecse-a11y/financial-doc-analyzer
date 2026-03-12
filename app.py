# ================================================================
# 📊 FINANCIAL DOCUMENT ANALYZER
# ================================================================
# Upload ANY financial document (PDF or TXT) and get an instant
# interactive dashboard with extracted metrics, charts & insights.
#
# Supports:
#   - Annual Reports
#   - Quarterly Results (Q1/Q2/Q3/Q4)
#   - Credit Rating Reports (CRISIL, ICRA, CARE)
#   - Conference Call Transcripts
#   - Investor Presentations
#
# TO DEPLOY FREE:
#   1. Upload app.py + requirements.txt to GitHub
#   2. Go to share.streamlit.io → connect GitHub → Deploy
#   3. Get free live link to share on LinkedIn!
# ================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import io

# PDF support
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ── PAGE SETUP ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Doc Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── DARK STYLING ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stApp {
    background-color: #07080f !important;
    color: #d8dce8 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Hero ── */
.hero-wrap {
    padding: 10px 0 30px;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3.6rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -2.5px;
    line-height: 1.05;
}
.hero-grad {
    background: linear-gradient(90deg, #fbbf24, #f97316);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    color: #3d4860;
    font-size: 1.05rem;
    margin-top: 10px;
}

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    background: #0c0f1a !important;
    border: 2px dashed #1c2438 !important;
    border-radius: 18px !important;
    padding: 10px 20px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #fbbf24 !important;
}
[data-testid="stFileUploader"] label {
    display: none !important;
}

/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background: #0c0f1a !important;
    border: 1px solid #181f30 !important;
    border-radius: 14px !important;
    padding: 18px !important;
}
div[data-testid="metric-container"] label {
    color: #3d4860 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    font-family: 'DM Sans', sans-serif !important;
}
div[data-testid="metric-container"] div[data-testid="metric-value"] {
    color: #fbbf24 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1.65rem !important;
    font-weight: 700 !important;
}

/* ── Section labels ── */
.sec-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    color: #fbbf24;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    border-left: 3px solid #fbbf24;
    padding-left: 10px;
    margin: 28px 0 16px;
}

/* ── Insight cards ── */
.icard {
    background: #0c0f1a;
    border: 1px solid #181f30;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    font-size: 0.92rem;
    line-height: 1.65;
    color: #b0b8cc;
}

/* ── Tag pills ── */
.tag {
    display: inline-block;
    background: #0c0f1a;
    border: 1px solid #181f30;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.8rem;
    color: #5a6880;
    margin: 3px 3px 3px 0;
}

/* ── Doc banner ── */
.doc-banner {
    background: linear-gradient(135deg, #0c0f1a, #111627);
    border: 1px solid #1c2438;
    border-left: 4px solid #fbbf24;
    border-radius: 14px;
    padding: 20px 26px;
    margin: 20px 0 28px;
}

/* ── Misc ── */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
.stDataFrame { border-radius: 12px !important; border: 1px solid #181f30 !important; }
.stExpander { border: 1px solid #181f30 !important; border-radius: 12px !important; background: #0c0f1a !important; }
</style>
""", unsafe_allow_html=True)


# ================================================================
# ── TEXT EXTRACTION ──────────────────────────────────────────────
# ================================================================

def read_pdf(file) -> str:
    """Extract all text from a PDF using pdfplumber."""
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        st.warning(f"PDF read issue: {e}")
    return text


def read_txt(file) -> str:
    """Read a plain-text file."""
    try:
        return file.read().decode("utf-8", errors="ignore")
    except:
        return ""


# ================================================================
# ── EXTRACTION ENGINE ────────────────────────────────────────────
# ================================================================

def detect_doc_info(text: str, filename: str) -> dict:
    """Detect document type, company name, year, and sector."""
    info = {"filename": filename}
    tl = text.lower()

    # Company name — first non-empty line
    lines = [l.strip() for l in text[:600].split("\n") if l.strip() and len(l.strip()) > 4]
    info["company"] = lines[0][:55] if lines else filename.replace(".pdf", "").replace(".txt", "")

    # Document type
    types = {
        "Annual Report":              ["annual report", "directors' report", "annual accounts"],
        "Quarterly Results":          ["quarterly results", "q1 fy", "q2 fy", "q3 fy", "q4 fy", "quarter ended"],
        "Credit Rating Report":       ["credit rating", "crisil", "icra", "care ratings", "fitch", "brickwork"],
        "Conference Call Transcript": ["conference call", "earnings call", "analyst call", "q&a session"],
        "Investor Presentation":      ["investor presentation", "investor day", "capital markets day"],
        "Balance Sheet / P&L":        ["balance sheet", "profit and loss", "income statement"],
    }
    info["doc_type"] = "Financial Document"
    for dtype, kws in types.items():
        if any(k in tl for k in kws):
            info["doc_type"] = dtype
            break

    # Year
    years = re.findall(r"\b(20\d{2})\b", text[:1200])
    info["year"] = max(years) if years else ""

    # Sector
    sectors = {
        "Banking & Finance":  ["bank", "nbfc", "lending", "deposits", "npa", "net interest income"],
        "Technology / IT":    ["software", "it services", "digital", "saas", "cloud"],
        "Pharmaceuticals":    ["pharma", "drug", "api", "formulation", "clinical"],
        "Manufacturing":      ["manufacturing", "plant", "capacity utilisation", "production"],
        "Real Estate":        ["real estate", "realty", "housing", "residential", "commercial project"],
        "FMCG / Consumer":    ["fmcg", "consumer goods", "brand", "distribution network"],
        "Energy / Power":     ["energy", "power", "renewable", "solar", "wind", "generation"],
        "Infrastructure":     ["infrastructure", "roads", "highways", "epc", "construction"],
        "Automobile":         ["automobile", "vehicle", "two-wheeler", "passenger vehicle", "ev"],
        "Telecom":            ["telecom", "subscriber", "arpu", "spectrum", "tower"],
    }
    info["sector"] = ""
    for sec, kws in sectors.items():
        if any(k in tl for k in kws):
            info["sector"] = sec
            break

    return info


def extract_metrics(text: str) -> dict:
    """
    Scan the document for ~20 financial metrics.
    For each metric we search for keyword patterns,
    then grab the number that immediately follows.
    Returns dict: { 'Metric Label': {'value': float, 'unit': str, 'snippet': str} }
    """
    tl = text.lower()
    results = {}

    # Each entry: display_label → list of search phrases
    targets = {
        # Income Statement
        "Total Revenue":         ["total revenue", "net revenue", "total income from operations",
                                  "net sales", "total turnover", "revenue from operations"],
        "Net Profit / PAT":      ["profit after tax", "net profit", "pat", "net income"],
        "EBITDA":                ["ebitda", "earnings before interest tax depreciation"],
        "Operating Profit":      ["operating profit", "ebit ", "pbit"],
        "Gross Profit":          ["gross profit"],
        "Total Expenses":        ["total expenses", "total expenditure"],
        "Finance Costs":         ["finance costs", "interest expense", "interest cost"],
        "Depreciation":          ["depreciation and amortisation", "depreciation & amortisation",
                                  "depreciation"],

        # Balance Sheet
        "Total Assets":          ["total assets"],
        "Total Debt":            ["total debt", "total borrowings", "gross debt"],
        "Net Debt":              ["net debt"],
        "Cash & Equivalents":    ["cash and cash equivalents", "cash & cash equivalents",
                                  "cash and bank balances"],
        "Shareholders Equity":   ["shareholders' equity", "shareholders equity",
                                  "total equity", "net worth"],
        "Capital Employed":      ["capital employed"],

        # Per Share / Ratios
        "EPS (₹)":               ["earnings per share", "basic eps", "diluted eps", "eps "],
        "Book Value per Share":  ["book value per share", "bvps"],
        "Debt to Equity":        ["debt to equity", "d/e ratio", "debt-equity ratio"],
        "Interest Coverage":     ["interest coverage ratio", "icr "],
        "Return on Equity %":    ["return on equity", "roe "],
        "Return on Assets %":    ["return on assets", "roa "],
        "Net Profit Margin %":   ["net profit margin", "pat margin", "net margin"],
        "EBITDA Margin %":       ["ebitda margin"],
        "Revenue Growth %":      ["revenue growth", "growth in revenue", "sales growth"],
    }

    num_pattern = re.compile(
        r'(?:₹|rs\.?|inr|\$)?\s*'   # optional currency symbol
        r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'  # the number itself
        r'\s*(?:(crore|cr|lakh|lacs|million|mn|billion|bn|%))?',
        re.IGNORECASE
    )

    for label, phrases in targets.items():
        for phrase in phrases:
            idx = tl.find(phrase)
            if idx == -1:
                continue
            # Look at text in a window after the phrase
            window = text[idx: idx + 250]
            m = num_pattern.search(window[len(phrase):])
            if m:
                try:
                    val = float(m.group(1).replace(",", ""))
                    unit = (m.group(2) or "").lower()
                    results[label] = {
                        "value": val,
                        "unit": unit,
                        "snippet": window[:120].replace("\n", " ").strip()
                    }
                    break  # found for this label, move on
                except:
                    pass

    return results


def extract_sentences(text: str) -> dict:
    """
    Pull meaningful sentences about performance, risks,
    outlook, and management commentary.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    out = {"highlights": [], "risks": [], "outlook": [], "management": []}

    hi_kw   = ["record", "highest", "strong", "robust", "growth", "increased", "improved", "surpassed"]
    ri_kw   = ["risk", "challenge", "concern", "volatile", "decline", "pressure", "adverse", "headwind"]
    ou_kw   = ["guidance", "outlook", "expect", "target", "plan", "focus", "strategy", "next year"]
    mg_kw   = ["ceo", "md ", "chairman", "management", "said", "stated", "commented", "according to"]

    for s in sentences:
        s = s.strip()
        if len(s) < 35 or len(s) > 320:
            continue
        sl = s.lower()
        if any(w in sl for w in hi_kw) and len(out["highlights"]) < 4:
            out["highlights"].append(s)
        if any(w in sl for w in ri_kw) and len(out["risks"]) < 4:
            out["risks"].append(s)
        if any(w in sl for w in ou_kw) and len(out["outlook"]) < 4:
            out["outlook"].append(s)
        if any(w in sl for w in mg_kw) and len(out["management"]) < 3:
            out["management"].append(s)

    return out


def term_frequency(text: str) -> pd.DataFrame:
    """Count how many times key financial terms appear."""
    terms = [
        "revenue", "profit", "growth", "debt", "equity", "margin",
        "ebitda", "cash", "sales", "income", "risk", "rating",
        "outlook", "strong", "increase", "decrease", "guidance",
        "target", "strategy", "dividend", "acquisition", "expansion",
        "working capital", "market share", "cost", "efficiency"
    ]
    tl = text.lower()
    data = [(t.title(), tl.count(t)) for t in terms if tl.count(t) > 0]
    df = pd.DataFrame(data, columns=["Term", "Mentions"])
    return df.sort_values("Mentions", ascending=False).head(18)


# ================================================================
# ── FORMATTING ───────────────────────────────────────────────────
# ================================================================

def fmt(value: float, unit: str) -> str:
    unit = (unit or "").lower()
    if unit in ("cr", "crore"):
        return f"₹{value/100:,.1f}K Cr" if value >= 1000 else f"₹{value:,.1f} Cr"
    if unit in ("lakh", "lacs"):
        return f"₹{value:,.1f} L"
    if unit in ("mn", "million"):
        return f"${value:,.1f} M"
    if unit in ("bn", "billion"):
        return f"${value:,.2f} B"
    if unit == "%":
        return f"{value:.2f}%"
    if value >= 10_000_000:
        return f"₹{value/10_000_000:,.2f} Cr"
    if value >= 100_000:
        return f"₹{value/100_000:,.2f} L"
    return f"{value:,.2f}"


# ================================================================
# ── CHART BUILDERS ───────────────────────────────────────────────
# ================================================================

DARK = dict(paper_bgcolor="#07080f", plot_bgcolor="#0c0f1a",
            font=dict(family="DM Sans, sans-serif", color="#d8dce8"))
AMBER = ["#fbbf24", "#f97316", "#ef4444", "#22c55e",
         "#60a5fa", "#a78bfa", "#f472b6", "#34d399", "#38bdf8"]


def bar_chart_metrics(metrics: dict):
    rows = []
    for lbl, d in metrics.items():
        if d["unit"] not in ("%", "") and d["value"] > 0:
            rows.append({"Metric": lbl, "Value": d["value"]})
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("Value")
    fig = px.bar(df, x="Value", y="Metric", orientation="h",
                 color="Value", color_continuous_scale=["#111827", "#fbbf24"],
                 text=df["Value"].apply(lambda x: f"{x:,.1f}"))
    fig.update_layout(**DARK, coloraxis_showscale=False,
                      xaxis=dict(gridcolor="#181f30", title=""),
                      yaxis=dict(gridcolor="#181f30", title=""),
                      margin=dict(t=10, b=10, l=10, r=10),
                      height=max(280, len(rows) * 42))
    fig.update_traces(textposition="outside", textfont_color="#d8dce8",
                      marker_line_width=0)
    return fig


def donut_chart(metrics: dict):
    """Donut chart comparing major P&L figures."""
    labels = ["Revenue", "Gross Profit", "EBITDA", "Operating Profit", "Net Profit"]
    key_map = {"Revenue": "Total Revenue", "Gross Profit": "Gross Profit",
               "EBITDA": "EBITDA", "Operating Profit": "Operating Profit",
               "Net Profit": "Net Profit / PAT"}
    vals = [metrics[key_map[l]]["value"] for l in labels if key_map[l] in metrics]
    lbls = [l for l in labels if key_map[l] in metrics]
    if len(vals) < 2:
        return None
    fig = go.Figure(go.Pie(labels=lbls, values=vals, hole=0.52,
                           marker_colors=AMBER,
                           textfont_size=12))
    fig.update_layout(**DARK, margin=dict(t=10, b=10, l=10, r=10),
                      showlegend=True,
                      legend=dict(font=dict(color="#6b7280"),
                                  bgcolor="rgba(0,0,0,0)"))
    fig.update_traces(marker=dict(line=dict(color="#07080f", width=2)))
    return fig


def term_bar(df: pd.DataFrame):
    fig = px.bar(df, x="Mentions", y="Term", orientation="h",
                 color="Mentions",
                 color_continuous_scale=["#111827", "#f97316"])
    fig.update_layout(**DARK, coloraxis_showscale=False,
                      xaxis=dict(gridcolor="#181f30", title="Times mentioned"),
                      yaxis=dict(gridcolor="#181f30", title=""),
                      margin=dict(t=10, b=10, l=10, r=10), height=420)
    fig.update_traces(marker_line_width=0)
    return fig


def gauge(value: float, title: str, max_val: float = 100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": "#d8dce8", "size": 13,
                                       "family": "DM Sans"}},
        number={"font": {"color": "#fbbf24", "size": 26,
                         "family": "Syne"}, "suffix": "%"},
        gauge={
            "axis": {"range": [0, max_val], "tickcolor": "#3d4860"},
            "bar": {"color": "#fbbf24"},
            "bgcolor": "#0c0f1a",
            "bordercolor": "#181f30",
            "steps": [
                {"range": [0, max_val * 0.35], "color": "#120a0a"},
                {"range": [max_val * 0.35, max_val * 0.65], "color": "#12100a"},
                {"range": [max_val * 0.65, max_val], "color": "#0a120a"},
            ],
        }
    ))
    fig.update_layout(**DARK, height=210,
                      margin=dict(t=30, b=0, l=20, r=20))
    return fig


# ================================================================
# ── UI ───────────────────────────────────────────────────────────
# ================================================================

# Hero
st.markdown("""
<div class="hero-wrap">
  <div class="hero-title">
    Financial Doc<br>
    <span class="hero-grad">Analyzer</span>
  </div>
  <div class="hero-sub">
    Upload any financial document → instant interactive dashboard
  </div>
</div>
""", unsafe_allow_html=True)

# Tag pills showing what's supported
for tag in ["📋 Annual Reports", "📈 Quarterly Results",
            "⭐ Credit Ratings", "🎙️ Conf. Call Transcripts",
            "📊 Investor Presentations"]:
    st.markdown(f'<span class="tag">{tag}</span>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# File uploader
uploaded = st.file_uploader(
    "upload",
    type=["pdf", "txt"],
    label_visibility="collapsed",
    help="PDF or TXT · Annual reports, earnings, credit ratings, transcripts…"
)
st.markdown("""
<div style="text-align:center;color:#242a38;font-size:0.83rem;margin-top:-6px;">
  📎 Drag & drop or click · PDF or TXT · Any financial document
</div>
""", unsafe_allow_html=True)

# ── PROCESS ───────────────────────────────────────────────────────
if uploaded:
    with st.spinner("🔍 Reading document and extracting data…"):
        # 1. Extract text
        text = read_pdf(uploaded) if uploaded.name.endswith(".pdf") else read_txt(uploaded)

        if len(text.strip()) < 80:
            st.error("Document seems empty or couldn't be read. Try saving as .txt and re-uploading.")
            st.stop()

        # 2. Run all analyzers
        info     = detect_doc_info(text, uploaded.name)
        metrics  = extract_metrics(text)
        insights = extract_sentences(text)
        tf_df    = term_frequency(text)

    # ── DOC BANNER ────────────────────────────────────────────
    year_str   = f"&nbsp;&nbsp;·&nbsp;&nbsp;📅 {info['year']}" if info.get("year") else ""
    sector_str = f"&nbsp;&nbsp;·&nbsp;&nbsp;🏭 {info['sector']}" if info.get("sector") else ""
    st.markdown(f"""
    <div class="doc-banner">
      <div style="font-family:'Syne',sans-serif;font-size:1.55rem;
                  font-weight:800;color:#fff;letter-spacing:-0.5px;">
        {info['company']}
      </div>
      <div style="color:#3d4860;margin-top:6px;font-size:0.88rem;">
        📄 {info['doc_type']}{year_str}{sector_str}
        &nbsp;&nbsp;·&nbsp;&nbsp;
        <span style="color:#fbbf24">{len(metrics)} metrics extracted</span>
        &nbsp; from {len(text):,} characters
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI CARDS ─────────────────────────────────────────────
    priority = [
        "Total Revenue", "Net Profit / PAT", "EBITDA",
        "Total Assets", "Total Debt", "Shareholders Equity",
        "EPS (₹)", "EBITDA Margin %"
    ]
    show = [(k, metrics[k]) for k in priority if k in metrics]
    show += [(k, v) for k, v in metrics.items() if k not in priority]
    show = show[:8]

    if show:
        st.markdown('<div class="sec-label">Key Financial Metrics</div>',
                    unsafe_allow_html=True)
        for i in range(0, len(show), 4):
            cols = st.columns(min(4, len(show) - i))
            for col, (lbl, d) in zip(cols, show[i:i+4]):
                col.metric(lbl, fmt(d["value"], d.get("unit", "")))

    # ── CHARTS ROW 1 ──────────────────────────────────────────
    st.markdown('<div class="sec-label">Visual Analysis</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**📊 Metrics Comparison**")
        fig = bar_chart_metrics(metrics)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough numeric data for this chart.")

    with c2:
        st.markdown("**🥧 P&L Breakdown**")
        fig2 = donut_chart(metrics)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.markdown("**🔤 Most Discussed Topics**")
            if not tf_df.empty:
                st.plotly_chart(term_bar(tf_df), use_container_width=True)

    # Term frequency chart (if donut was shown above)
    if donut_chart(metrics) and not tf_df.empty:
        st.markdown("**🔤 Most Discussed Financial Topics**")
        st.plotly_chart(term_bar(tf_df), use_container_width=True)

    # ── GAUGE CHARTS for % metrics ────────────────────────────
    pct = {k: v for k, v in metrics.items()
           if v.get("unit") == "%" and 0 < v["value"] <= 100}
    if pct:
        st.markdown('<div class="sec-label">Ratio Gauges</div>',
                    unsafe_allow_html=True)
        gcols = st.columns(min(4, len(pct)))
        for col, (lbl, d) in zip(gcols, list(pct.items())[:4]):
            col.plotly_chart(gauge(d["value"], lbl), use_container_width=True)

    # ── INSIGHTS ──────────────────────────────────────────────
    st.markdown('<div class="sec-label">Extracted Insights</div>',
                unsafe_allow_html=True)
    left, right = st.columns(2)

    with left:
        if insights["highlights"]:
            st.markdown("**✅ Performance Highlights**")
            for s in insights["highlights"][:3]:
                st.markdown(f'<div class="icard">"{s}"</div>',
                            unsafe_allow_html=True)
        if insights["outlook"]:
            st.markdown("**🎯 Outlook & Strategy**")
            for s in insights["outlook"][:2]:
                st.markdown(f'<div class="icard">"{s}"</div>',
                            unsafe_allow_html=True)

    with right:
        if insights["risks"]:
            st.markdown("**⚠️ Risk Factors**")
            for s in insights["risks"][:3]:
                st.markdown(f'<div class="icard">"{s}"</div>',
                            unsafe_allow_html=True)
        if insights["management"]:
            st.markdown("**👔 Management Commentary**")
            for s in insights["management"][:2]:
                st.markdown(f'<div class="icard">"{s}"</div>',
                            unsafe_allow_html=True)

    # ── FULL DATA TABLE ───────────────────────────────────────
    if metrics:
        st.markdown('<div class="sec-label">All Extracted Data</div>',
                    unsafe_allow_html=True)
        table_rows = [
            {
                "Metric": k,
                "Formatted Value": fmt(v["value"], v.get("unit", "")),
                "Raw Number": v["value"],
                "Unit": v.get("unit", "—"),
                "Source snippet": v.get("snippet", "")[:90] + "…"
            }
            for k, v in metrics.items()
        ]
        st.dataframe(pd.DataFrame(table_rows),
                     use_container_width=True, height=380)

    # ── RAW TEXT PREVIEW ──────────────────────────────────────
    with st.expander("📄 View raw document text"):
        preview = text[:6000] + ("\n\n[… truncated to 6000 chars]" if len(text) > 6000 else "")
        st.text_area("", preview, height=300, disabled=True,
                     label_visibility="collapsed")

    # ── DOWNLOAD ──────────────────────────────────────────────
    if metrics:
        csv = pd.DataFrame([
            {"Metric": k, "Value": v["value"], "Unit": v.get("unit", ""),
             "Context": v.get("snippet", "")[:100]}
            for k, v in metrics.items()
        ]).to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download Extracted Data as CSV",
            data=csv,
            file_name=f"{info['company'][:25].replace(' ','_')}_analysis.csv",
            mime="text/csv"
        )

# ── EMPTY STATE ───────────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center;padding:70px 20px 40px;color:#1e2535;">
      <div style="font-size:5.5rem;margin-bottom:18px;">📄</div>
      <div style="font-family:'Syne',sans-serif;font-size:1.65rem;
                  font-weight:800;color:#2a3348;letter-spacing:-0.5px;">
        Drop any financial document above
      </div>
      <div style="margin-top:12px;color:#1e2535;font-size:0.95rem;
                  max-width:480px;margin-left:auto;margin-right:auto;">
        Annual reports · Quarterly results · Credit rating reports ·
        Conference call transcripts · Investor presentations
      </div>
    </div>
    """, unsafe_allow_html=True)
