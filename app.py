from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Dashboard Loss Event Energi Primer",
    page_icon="⚡",
    layout="wide",
)

COLORS = {
    "bg": "#0B0F17", "panel": "#121826", "panel_2": "#182235",
    "text": "#F7F9FC", "muted": "#AAB4C5", "grid": "#303A4D",
    "blue": "#46B5D1", "cyan": "#55C2C3", "amber": "#FFB547",
    "coral": "#EF6175", "green": "#78C58A", "red": "#FF5252",
}

st.markdown(
    f"""
    <style>
    .stApp {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #101827 0%, #0B111D 100%);
        border-right: 1px solid #253047;
    }}
    [data-testid="stHeader"] {{ background: rgba(11,15,23,.82); }}
    h1, h2, h3, h4, p, label, [data-testid="stCaptionContainer"] {{
        color: {COLORS['text']};
    }}
    [data-testid="stMetric"] {{
        background: linear-gradient(145deg, {COLORS['panel_2']}, {COLORS['panel']});
        border: 1px solid #2A3853;
        border-top: 3px solid {COLORS['cyan']};
        border-radius: 14px;
        padding: 16px 18px;
        min-height: 118px;
        box-shadow: 0 8px 24px rgba(0,0,0,.20);
    }}
    [data-testid="stMetricLabel"] {{ color: {COLORS['muted']}; }}
    [data-testid="stMetricValue"] {{ color: {COLORS['text']}; }}
    [data-baseweb="tab-list"] {{
        gap: 8px; background: {COLORS['panel']}; padding: 7px;
        border-radius: 12px; border: 1px solid #253047;
    }}
    [data-baseweb="tab"] {{ border-radius: 9px; padding: 8px 14px; }}
    [aria-selected="true"][data-baseweb="tab"] {{
        background: #1F8EA8; color: white;
    }}
    [data-testid="stDataFrame"], [data-testid="stAlert"] {{
        border-radius: 12px; overflow: hidden;
    }}
    .block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = [
    COLORS["cyan"], COLORS["amber"], COLORS["coral"],
    COLORS["green"], COLORS["blue"], "#A78BFA",
]


def style_figure(fig, height: int = 430):
    fig.update_layout(
        paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
        font={"color": COLORS["text"], "family": "Arial"},
        title_font={"size": 20}, height=height,
        margin={"l": 35, "r": 25, "t": 70, "b": 40},
        hoverlabel={"bgcolor": COLORS["panel_2"], "font_color": COLORS["text"]},
        legend={"bgcolor": "rgba(0,0,0,0)"},
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])
    return fig

SHEET_ID = "1k1rEDG8UqMG7Oo6bBrbWK3lrdmUPKPFmrlPjCjRfVno"
DATA_GID = "488571671"
DEFAULT_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    f"?format=csv&gid={DATA_GID}"
)

REQUIRED_COLUMNS = {
    "Event_ID",
    "Regional",
    "Tahun",
    "Bulan",
    "Loss_Production_MWh",
    "Loss_Opportunity_Rp",
    "Risk_Limit_Rp",
    "Kategori_Final",
}

MONTH_ORDER = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Mei": 5, "Jun": 6,
    "Jul": 7, "Agu": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Des": 12,
    "May": 5, "Aug": 8, "Oct": 10, "Dec": 12,
}


@st.cache_data(ttl=600, show_spinner=False)
def load_csv(url: str) -> pd.DataFrame:
    return pd.read_csv(url)


@st.cache_data(show_spinner=False)
def load_upload(file_name: str, raw: bytes) -> pd.DataFrame:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(io.BytesIO(raw))
    return pd.read_excel(io.BytesIO(raw), sheet_name="Data_Loss_Event")


def prepare_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError("Kolom wajib belum tersedia: " + ", ".join(missing))

    numeric_columns = [
        "Tahun", "Loss_Production_MWh", "Loss_Opportunity_Rp",
        "Risk_Limit_Rp", "Pct_Risk_Limit",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("Rp", "", regex=False)
                .str.strip(),
                errors="coerce",
            )

    for column in [
        "Regional", "Unit_Standar", "Unit", "Kategori_Final",
        "Kelengkapan_Waktu", "Granularitas_Record", "Event_Layak_Model",
        "Skala_Dampak", "Flag_Outlier", "Flag_Duplikasi",
    ]:
        if column in df.columns:
            df[column] = df[column].fillna("Tidak tersedia").astype(str).str.strip()

    unit_source = "Unit_Standar" if "Unit_Standar" in df.columns else "Unit"
    df["Unit_Dashboard"] = df[unit_source]
    df["Bulan_No"] = df["Bulan"].astype(str).str.strip().map(MONTH_ORDER)
    df["Periode"] = pd.to_datetime(
        dict(year=df["Tahun"], month=df["Bulan_No"], day=1), errors="coerce"
    )
    return df


def rupiah(value: float) -> str:
    if pd.isna(value):
        return "Rp0"
    return f"Rp{value:,.0f}"


def number(value: float, decimals: int = 2) -> str:
    if pd.isna(value):
        return "0"
    return f"{value:,.{decimals}f}"


def impact_scale(pct: float) -> str:
    if pct <= 0:
        return "Tidak Ada Loss"
    if pct <= 0.20:
        return "Sangat Rendah"
    if pct <= 0.40:
        return "Rendah"
    if pct <= 0.60:
        return "Moderat"
    if pct <= 0.80:
        return "Tinggi"
    return "Sangat Tinggi"


def multiselect_filter(label: str, values: pd.Series, key: str) -> list[str]:
    options = sorted(v for v in values.dropna().astype(str).unique() if v)
    return st.sidebar.multiselect(label, options, default=options, key=key)


def beta_pert_parameters(minimum: float, mode: float, maximum: float, shape: float = 4.0):
    span = maximum - minimum
    if span <= 0:
        return 1.0, 1.0
    alpha = 1.0 + shape * (mode - minimum) / span
    beta = 1.0 + shape * (maximum - mode) / span
    return alpha, beta


def beta_pert_sample(rng, minimum, mode, maximum, size, shape=4.0):
    if maximum <= minimum:
        return np.full(size, minimum, dtype=float)
    alpha, beta = beta_pert_parameters(minimum, mode, maximum, shape)
    return minimum + (maximum - minimum) * rng.beta(alpha, beta, size=size)


def impact_score_from_ratio(ratio: float) -> int:
    if ratio <= 0.20:
        return 1
    if ratio <= 0.40:
        return 2
    if ratio <= 0.60:
        return 3
    if ratio <= 0.80:
        return 4
    return 5


def likelihood_score_from_probability(probability: float) -> int:
    if probability <= 0.05:
        return 1
    if probability <= 0.20:
        return 2
    if probability <= 0.50:
        return 3
    if probability <= 0.80:
        return 4
    return 5


def simulate_annual_loss(
    data: pd.DataFrame,
    year: int,
    cutoff_month: int,
    simulations: int,
    seed: int,
    minimum: float | None = None,
    mode: float | None = None,
    maximum: float | None = None,
):
    scoped = data[data["Tahun"] == year].copy()
    actual_ytd = scoped["Loss_Opportunity_Rp"].sum()
    remaining_months = max(12 - cutoff_month, 0)

    monthly = (
        scoped.groupby("Bulan_No")["Loss_Opportunity_Rp"]
        .sum()
        .reindex(range(1, cutoff_month + 1), fill_value=0.0)
        .astype(float)
    )
    positive = monthly[monthly > 0]
    if positive.empty:
        calibrated_min = calibrated_mode = calibrated_max = 0.0
    else:
        calibrated_min = float(positive.min())
        calibrated_mode = float(positive.median())
        calibrated_max = float(positive.max())

    minimum = calibrated_min if minimum is None else float(minimum)
    mode = calibrated_mode if mode is None else float(mode)
    maximum = calibrated_max if maximum is None else float(maximum)
    minimum, mode, maximum = sorted([minimum, mode, maximum])

    active_months = int((monthly > 0).sum())
    occurrence_probability = (active_months + 1) / (cutoff_month + 2)
    rng = np.random.default_rng(seed)
    future_total = np.zeros(simulations, dtype=float)
    for _ in range(remaining_months):
        occurs = rng.random(simulations) < occurrence_probability
        severity = beta_pert_sample(
            rng, minimum, mode, maximum, simulations, shape=4.0
        )
        future_total += occurs * severity

    annual_loss = actual_ytd + future_total
    return {
        "annual_loss": annual_loss,
        "actual_ytd": actual_ytd,
        "remaining_months": remaining_months,
        "occurrence_probability": occurrence_probability,
        "minimum": minimum,
        "mode": mode,
        "maximum": maximum,
    }


st.title("Dashboard Loss Event Energi Primer")
st.caption(
    "Pendekatan langsung berbasis loss production (MWh) dan loss opportunity (Rp)."
)

with st.sidebar:
    st.header("Sumber Data")
    uploaded = st.file_uploader(
        "Opsional: unggah CSV/XLSX",
        type=["csv", "xlsx"],
        help="Dipakai bila Google Sheet belum dapat diakses oleh aplikasi publik.",
    )
    csv_url = st.text_input("Google Sheet CSV URL", value=DEFAULT_CSV_URL)
    st.divider()

try:
    if uploaded is not None:
        raw_df = load_upload(uploaded.name, uploaded.getvalue())
        source_label = f"Unggahan: {uploaded.name}"
    else:
        raw_df = load_csv(csv_url)
        source_label = "Google Sheet"
    df = prepare_data(raw_df)
except Exception as exc:
    st.error("Data belum dapat dibaca oleh dashboard.")
    st.info(
        "Pastikan Google Sheet dapat diakses oleh aplikasi melalui Publish to web, "
        "atau unggah file XLSX/CSV pada panel kiri."
    )
    st.code(str(exc))
    st.stop()

with st.sidebar:
    st.header("Filter")
    years = sorted(df["Tahun"].dropna().astype(int).unique())
    selected_years = st.multiselect("Tahun", years, default=years)
    selected_regions = multiselect_filter("Regional", df["Regional"], "regional")
    selected_units = multiselect_filter("Unit", df["Unit_Dashboard"], "unit")
    selected_categories = multiselect_filter(
        "Kategori final", df["Kategori_Final"], "category"
    )
    if "Kelengkapan_Waktu" in df.columns:
        selected_time_quality = multiselect_filter(
            "Kelengkapan waktu", df["Kelengkapan_Waktu"], "time_quality"
        )
    else:
        selected_time_quality = []
    st.caption(f"Sumber aktif: {source_label}")

mask = (
    df["Tahun"].isin(selected_years)
    & df["Regional"].isin(selected_regions)
    & df["Unit_Dashboard"].isin(selected_units)
    & df["Kategori_Final"].isin(selected_categories)
)
if "Kelengkapan_Waktu" in df.columns:
    mask &= df["Kelengkapan_Waktu"].isin(selected_time_quality)
filtered = df.loc[mask].copy()

total_events = filtered["Event_ID"].nunique()
total_mwh = filtered["Loss_Production_MWh"].sum()
total_rp = filtered["Loss_Opportunity_Rp"].sum()
risk_limit = filtered["Risk_Limit_Rp"].dropna().max()
pct_limit = total_rp / risk_limit if risk_limit and risk_limit > 0 else np.nan

cols = st.columns(5)
cols[0].metric("Jumlah Loss Event", f"{total_events:,}")
cols[1].metric("Loss Production", f"{number(total_mwh, 3)} MWh")
cols[2].metric("Loss Opportunity", rupiah(total_rp))
cols[3].metric("% Risk Limit", "-" if pd.isna(pct_limit) else f"{pct_limit:.2%}")
cols[4].metric("Skala Dampak Agregat", impact_scale(pct_limit) if not pd.isna(pct_limit) else "-")

st.caption(
    "Skala dampak agregat dihitung dari total loss opportunity terfilter dibagi "
    "risk limit korporat. Ini belum merupakan level risiko penuh karena probabilitas "
    "belum dimasukkan."
)

if filtered.empty:
    st.warning("Tidak ada data yang memenuhi kombinasi filter.")
    st.stop()

(
    tab_overview,
    tab_forecast,
    tab_simulation,
    tab_heatmap,
    tab_quality,
    tab_detail,
    tab_method,
) = st.tabs(
    [
        "Ringkasan",
        "Looking Forward",
        "Monte Carlo",
        "Risk Heat Map",
        "Kualitas Data",
        "Detail Event",
        "Metodologi",
    ]
)

with tab_overview:
    left, right = st.columns(2)
    monthly = (
        filtered.dropna(subset=["Periode"])
        .groupby("Periode", as_index=False)
        .agg(
            Loss_MWh=("Loss_Production_MWh", "sum"),
            Loss_Rp=("Loss_Opportunity_Rp", "sum"),
        )
        .sort_values("Periode")
    )
    with left:
        fig = px.line(
            monthly, x="Periode", y="Loss_MWh", markers=True,
            title="Tren Loss Production Bulanan",
            labels={"Periode": "Periode", "Loss_MWh": "Loss MWh"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.line(
            monthly, x="Periode", y="Loss_Rp", markers=True,
            title="Tren Loss Opportunity Bulanan",
            labels={"Periode": "Periode", "Loss_Rp": "Loss Rp"},
        )
        st.plotly_chart(fig, use_container_width=True)

    category = (
        filtered.groupby("Kategori_Final", as_index=False)
        .agg(
            Jumlah_Event=("Event_ID", "nunique"),
            Loss_MWh=("Loss_Production_MWh", "sum"),
            Loss_Rp=("Loss_Opportunity_Rp", "sum"),
        )
        .sort_values("Loss_Rp", ascending=False)
    )
    regional = (
        filtered.groupby("Regional", as_index=False)
        .agg(Loss_Rp=("Loss_Opportunity_Rp", "sum"))
        .sort_values("Loss_Rp", ascending=False)
    )
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            category, x="Loss_Rp", y="Kategori_Final", orientation="h",
            title="Loss Opportunity per Kategori Final",
            labels={"Loss_Rp": "Loss Rp", "Kategori_Final": "Kategori"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(
            regional, x="Regional", y="Loss_Rp",
            title="Loss Opportunity per Regional",
            labels={"Loss_Rp": "Loss Rp"},
        )
        st.plotly_chart(fig, use_container_width=True)

    top_units = (
        filtered.groupby("Unit_Dashboard", as_index=False)
        .agg(Loss_Rp=("Loss_Opportunity_Rp", "sum"))
        .nlargest(10, "Loss_Rp")
        .sort_values("Loss_Rp")
    )
    fig = px.bar(
        top_units, x="Loss_Rp", y="Unit_Dashboard", orientation="h",
        title="Top 10 Unit Berdasarkan Loss Opportunity",
        labels={"Loss_Rp": "Loss Rp", "Unit_Dashboard": "Unit"},
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_forecast:
    st.subheader("Looking Forward – Estimated Annual Loss")
    st.caption(
        "Estimasi tahunan = aktual YTD + estimasi sisa periode. "
        "Baseline menggunakan rata-rata loss bulanan aktual sampai cut-off data."
    )

    if len(selected_years) != 1:
        st.info("Pilih tepat satu tahun pada filter untuk menampilkan proyeksi tahunan.")
    else:
        forecast_year = int(selected_years[0])
        forecast_data = filtered[filtered["Tahun"] == forecast_year].copy()
        cutoff_month = int(
            df.loc[df["Tahun"] == forecast_year, "Bulan_No"].dropna().max()
        )
        remaining_months = max(12 - cutoff_month, 0)

        scenario = st.radio(
            "Skenario sisa tahun",
            ["Optimistis", "Base", "Pesimistis"],
            index=1,
            horizontal=True,
        )
        scenario_factor = {
            "Optimistis": 0.80,
            "Base": 1.00,
            "Pesimistis": 1.20,
        }[scenario]

        actual_mwh = forecast_data["Loss_Production_MWh"].sum()
        actual_rp = forecast_data["Loss_Opportunity_Rp"].sum()
        monthly_mwh = actual_mwh / cutoff_month if cutoff_month else 0
        monthly_rp = actual_rp / cutoff_month if cutoff_month else 0
        remaining_mwh = monthly_mwh * remaining_months * scenario_factor
        remaining_rp = monthly_rp * remaining_months * scenario_factor
        annual_mwh = actual_mwh + remaining_mwh
        annual_rp = actual_rp + remaining_rp
        annual_pct = annual_rp / risk_limit if risk_limit and risk_limit > 0 else np.nan

        f1, f2, f3, f4, f5 = st.columns(5)
        f1.metric("Cut-off Realisasi", f"Bulan ke-{cutoff_month}")
        f2.metric("Aktual YTD", rupiah(actual_rp))
        f3.metric("Estimasi Sisa Tahun", rupiah(remaining_rp))
        f4.metric("Estimasi Tahunan", rupiah(annual_rp))
        f5.metric(
            "Skala Dampak Estimasi",
            impact_scale(annual_pct) if not pd.isna(annual_pct) else "-",
        )

        st.metric(
            "Estimated Annual Loss Production",
            f"{number(annual_mwh, 3)} MWh",
        )
        st.progress(min(float(annual_pct), 1.0) if not pd.isna(annual_pct) else 0.0)
        st.caption(
            "Estimated annual loss opportunity terhadap risk limit: "
            + (f"{annual_pct:.2%}" if not pd.isna(annual_pct) else "-")
        )

        actual_monthly = (
            forecast_data.dropna(subset=["Periode"])
            .groupby("Periode", as_index=False)
            .agg(Loss_Rp=("Loss_Opportunity_Rp", "sum"))
            .sort_values("Periode")
        )
        actual_monthly["Jenis"] = "Aktual"
        if remaining_months:
            future_dates = pd.date_range(
                start=pd.Timestamp(forecast_year, cutoff_month, 1)
                + pd.offsets.MonthBegin(1),
                periods=remaining_months,
                freq="MS",
            )
            projected = pd.DataFrame(
                {
                    "Periode": future_dates,
                    "Loss_Rp": monthly_rp * scenario_factor,
                    "Jenis": "Estimasi",
                }
            )
            outlook = pd.concat([actual_monthly, projected], ignore_index=True)
        else:
            outlook = actual_monthly

        fig = px.bar(
            outlook,
            x="Periode",
            y="Loss_Rp",
            color="Jenis",
            barmode="group",
            title=f"Aktual dan Estimasi Loss Opportunity {forecast_year}",
            labels={"Loss_Rp": "Loss Opportunity Rp", "Periode": "Periode"},
            color_discrete_map={"Aktual": "#0072CE", "Estimasi": "#F4A261"},
        )
        st.plotly_chart(fig, use_container_width=True)

        summary = pd.DataFrame(
            {
                "Komponen": ["Aktual YTD", "Estimasi Sisa Tahun", "Estimasi Tahunan"],
                "Loss Production MWh": [actual_mwh, remaining_mwh, annual_mwh],
                "Loss Opportunity Rp": [actual_rp, remaining_rp, annual_rp],
            }
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.warning(
            "Proyeksi ini adalah annualized run-rate, bukan hasil Monte Carlo. "
            "Perubahan skenario hanya diterapkan pada periode yang belum terealisasi."
        )

with tab_simulation:
    st.subheader("Monte Carlo – Annual Loss Distribution")
    st.caption(
        "Aktual YTD dipertahankan sebagai nilai pasti. Loss bulan tersisa "
        "disimulasikan menggunakan occurrence bulanan dan severity BETA-PERT."
    )

    if len(selected_years) != 1:
        st.info("Pilih tepat satu tahun pada filter untuk menjalankan simulasi.")
    else:
        model_year = int(selected_years[0])
        model_cutoff = int(
            df.loc[df["Tahun"] == model_year, "Bulan_No"].dropna().max()
        )
        scope_options = ["Agregat Terfilter"] + sorted(
            filtered["Kategori_Final"].dropna().unique().tolist()
        )
        model_scope = st.selectbox("Lingkup simulasi", scope_options)
        model_data = (
            filtered
            if model_scope == "Agregat Terfilter"
            else filtered[filtered["Kategori_Final"] == model_scope]
        )

        calibration = simulate_annual_loss(
            model_data, model_year, model_cutoff, simulations=1000, seed=42
        )
        c1, c2, c3 = st.columns(3)
        minimum = c1.number_input(
            "Minimum loss bulanan (Rp)", min_value=0.0,
            value=float(calibration["minimum"]), format="%.0f"
        )
        mode = c2.number_input(
            "Most likely loss bulanan (Rp)", min_value=0.0,
            value=float(calibration["mode"]), format="%.0f"
        )
        maximum = c3.number_input(
            "Maximum loss bulanan (Rp)", min_value=0.0,
            value=float(calibration["maximum"]), format="%.0f"
        )
        if not (minimum <= mode <= maximum):
            st.error("Parameter harus memenuhi Minimum ≤ Most Likely ≤ Maximum.")
            st.stop()

        m1, m2, m3 = st.columns(3)
        simulations = m1.select_slider(
            "Jumlah iterasi", options=[1000, 5000, 10000, 25000, 50000], value=10000
        )
        seed = m2.number_input("Random seed", min_value=1, value=2026, step=1)
        exceedance_percent = m3.slider(
            "Threshold exceedance (% risk limit)", 5, 100, 20, 5,
            format="%d%%"
        )
        exceedance_pct = exceedance_percent / 100.0

        result = simulate_annual_loss(
            model_data,
            model_year,
            model_cutoff,
            simulations=int(simulations),
            seed=int(seed),
            minimum=minimum,
            mode=mode,
            maximum=maximum,
        )
        annual_loss = result["annual_loss"]
        percentiles = np.percentile(annual_loss, [50, 80, 90, 95])
        threshold_rp = risk_limit * exceedance_pct
        exceedance_probability = float(np.mean(annual_loss > threshold_rp))

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Mean", rupiah(float(np.mean(annual_loss))))
        k2.metric("P50", rupiah(percentiles[0]))
        k3.metric("P80", rupiah(percentiles[1]))
        k4.metric("P90", rupiah(percentiles[2]))
        k5.metric("P95", rupiah(percentiles[3]))
        st.metric(
            f"Peluang annual loss > {exceedance_pct:.0%} risk limit",
            f"{exceedance_probability:.2%}",
        )

        hist = pd.DataFrame({"Annual Loss Rp": annual_loss})
        fig = px.histogram(
            hist,
            x="Annual Loss Rp",
            nbins=60,
            histnorm="probability density",
            title="Forecast Chart – Distribusi Annual Loss",
        )
        colors = {"P50": "#2A9D8F", "P90": "#F4A261", "P95": "#E76F51"}
        for label, value in zip(["P50", "P90", "P95"], [percentiles[0], percentiles[2], percentiles[3]]):
            fig.add_vline(
                x=value, line_dash="dash", line_color=colors[label],
                annotation_text=label, annotation_position="top"
            )
        fig.add_vline(
            x=threshold_rp, line_dash="dot", line_color="#C1121F",
            annotation_text="Exceedance threshold", annotation_position="bottom"
        )
        st.plotly_chart(style_figure(fig, 500), use_container_width=True)

        sorted_loss = np.sort(annual_loss)
        exceedance_curve = pd.DataFrame(
            {
                "Annual Loss Rp": sorted_loss,
                "Probability of Exceedance": 1.0 - np.arange(1, len(sorted_loss) + 1) / len(sorted_loss),
            }
        )
        fig = px.line(
            exceedance_curve,
            x="Annual Loss Rp",
            y="Probability of Exceedance",
            title="Probability of Exceedance Curve",
        )
        st.plotly_chart(style_figure(fig), use_container_width=True)

        alpha, beta = beta_pert_parameters(minimum, mode, maximum)
        pert_sample = beta_pert_sample(
            np.random.default_rng(int(seed)), minimum, mode, maximum, 20000
        )
        p20, p50, p90, p95 = np.percentile(pert_sample, [20, 50, 90, 95])
        density, edges = np.histogram(pert_sample, bins=90, density=True)
        centers = (edges[:-1] + edges[1:]) / 2
        widths = np.diff(edges)
        zone_colors = np.where(
            centers <= p20, COLORS["coral"],
            np.where(
                centers <= p50, COLORS["amber"],
                np.where(centers <= p90, COLORS["cyan"], COLORS["green"]),
            ),
        )
        fig = go.Figure(
            go.Bar(
                x=centers, y=density, width=widths,
                marker={"color": zone_colors, "line": {"width": 0}},
                hovertemplate="Loss Rp %{x:,.0f}<br>Kepadatan %{y:.6f}<extra></extra>",
            )
        )
        fig.update_layout(
            title=f"Distribusi BETA-PERT — Loss Opportunity | α={alpha:.2f}, β={beta:.2f}",
            xaxis_title="Loss Opportunity (Rp)", yaxis_title="Kepadatan Probabilitas",
            bargap=0,
        )
        percentile_lines = {
            "P20": (p20, COLORS["coral"]), "P50": (p50, COLORS["amber"]),
            "P90": (p90, COLORS["blue"]), "P95": (p95, COLORS["red"]),
        }
        for label, (value, color) in percentile_lines.items():
            fig.add_vline(
                x=value, line_dash="dash", line_color=color, line_width=2,
                annotation_text=label, annotation_position="top",
                annotation_font_color=color,
            )
        st.plotly_chart(style_figure(fig, 520), use_container_width=True)
        st.caption(
            f"Probabilitas bulan aktif (smoothed): {result['occurrence_probability']:.2%}. "
            "Parameter dapat diubah untuk memasukkan expert judgement."
        )

with tab_heatmap:
    st.subheader("Risk Heat Map – Monte Carlo P90")
    st.caption(
        "Dampak menggunakan P90 annual loss terhadap risk limit. Kemungkinan "
        "menggunakan peluang annual loss melampaui 20% risk limit."
    )

    if len(selected_years) != 1:
        st.info("Pilih tepat satu tahun pada filter untuk membuat heat map.")
    else:
        heat_year = int(selected_years[0])
        heat_cutoff = int(
            df.loc[df["Tahun"] == heat_year, "Bulan_No"].dropna().max()
        )
        heat_rows = []
        for idx, category_name in enumerate(sorted(filtered["Kategori_Final"].unique())):
            category_data = filtered[filtered["Kategori_Final"] == category_name]
            category_result = simulate_annual_loss(
                category_data,
                heat_year,
                heat_cutoff,
                simulations=10000,
                seed=2026 + idx,
            )
            category_loss = category_result["annual_loss"]
            p90_loss = float(np.percentile(category_loss, 90))
            impact_ratio = p90_loss / risk_limit if risk_limit else 0.0
            exceedance_probability = float(np.mean(category_loss > risk_limit * 0.20))
            impact_score = impact_score_from_ratio(impact_ratio)
            likelihood_score = likelihood_score_from_probability(exceedance_probability)
            heat_rows.append(
                {
                    "Kategori": category_name,
                    "P90 Annual Loss Rp": p90_loss,
                    "% Risk Limit": impact_ratio,
                    "Probability of Exceedance": exceedance_probability,
                    "Skala Kemungkinan": likelihood_score,
                    "Skala Dampak": impact_score,
                    "Nilai Risiko": likelihood_score * impact_score,
                }
            )

        heat_df = pd.DataFrame(heat_rows)
        grid = pd.DataFrame(
            [(x, y, x * y) for x in range(1, 6) for y in range(1, 6)],
            columns=["Skala Dampak", "Skala Kemungkinan", "Nilai Risiko"],
        )
        fig = px.scatter(
            grid,
            x="Skala Dampak",
            y="Skala Kemungkinan",
            color="Nilai Risiko",
            size=np.full(len(grid), 45),
            color_continuous_scale=["#2E7D32", "#F9A825", "#EF6C00", "#C62828"],
            range_x=[0.5, 5.5],
            range_y=[0.5, 5.5],
            title="Heat Map Risiko Hambatan Energi Primer",
        )
        fig.add_scatter(
            x=heat_df["Skala Dampak"],
            y=heat_df["Skala Kemungkinan"],
            mode="markers+text",
            text=heat_df["Kategori"],
            textposition="top center",
            marker={"size": 18, "color": "#111827", "symbol": "diamond"},
            name="Kategori Risiko",
        )
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(dtick=1)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            heat_df.style.format(
                {
                    "P90 Annual Loss Rp": "{:,.0f}",
                    "% Risk Limit": "{:.2%}",
                    "Probability of Exceedance": "{:.2%}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.warning(
            "Batas Skala Kemungkinan masih provisional: ≤5%, ≤20%, ≤50%, "
            "≤80%, dan >80%. Ganti dengan threshold resmi ED 0012.E-2024 "
            "setelah tabel kemungkinan tersedia."
        )

with tab_quality:
    q1, q2, q3 = st.columns(3)
    detailed = int(
        filtered["Kelengkapan_Waktu"]
        .isin(["ADA TANGGAL", "TANGGAL LENGKAP"])
        .sum()
    )
    monthly_only = int((filtered.get("Kelengkapan_Waktu", "") == "HANYA BULAN").sum())
    review = int((filtered.get("Event_Layak_Model", "") != "LAYAK").sum())
    q1.metric("Ada Tanggal", f"{detailed:,}")
    q2.metric("Hanya Bulan", f"{monthly_only:,}")
    q3.metric("Perlu Review Model", f"{review:,}")

    quality_col = "Kelengkapan_Waktu" if "Kelengkapan_Waktu" in filtered else None
    if quality_col:
        quality = filtered.groupby(quality_col, as_index=False).size()
        fig = px.pie(
            quality, names=quality_col, values="size", hole=0.45,
            title="Komposisi Kelengkapan Waktu",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.warning(
        "Record berstatus HANYA BULAN ditampilkan sebagai agregasi bulanan. "
        "Dashboard tidak mengasumsikan tanggal kejadian tertentu."
    )

with tab_detail:
    display_columns = [
        "Event_ID", "Tahun", "Bulan", "Tanggal_Mulai", "Regional",
        "Unit_Dashboard", "Kategori_Final", "Subkategori_Event",
        "Loss_Production_MWh", "Loss_Opportunity_Rp", "Pct_Risk_Limit",
        "Skala_Dampak", "Kelengkapan_Waktu", "Granularitas_Record",
        "Rule_ID", "Override_Kategori", "Catatan_Review_AI",
    ]
    display_columns = [c for c in display_columns if c in filtered.columns]
    detail = filtered[display_columns].sort_values(
        "Loss_Opportunity_Rp", ascending=False
    )
    st.dataframe(detail, use_container_width=True, hide_index=True)
    st.download_button(
        "Unduh data terfilter (CSV)",
        data=detail.to_csv(index=False).encode("utf-8-sig"),
        file_name="loss_event_energi_primer_terfilter.csv",
        mime="text/csv",
    )

with tab_method:
    st.markdown(
        """
        **Alur perhitungan**

        1. Dashboard membaca `Data_Loss_Event` dan menggunakan `Kategori_Final`.
        2. `Kategori_Final` mengambil `Override_Kategori` bila diisi; bila kosong,
           menggunakan hasil klasifikasi formula.
        3. Loss production dijumlahkan dalam MWh dan loss opportunity dalam Rp.
        4. Persentase risk limit agregat = total loss opportunity terfilter / risk
           limit korporat.
        5. Batas skala dampak: sampai 20% Sangat Rendah; sampai 40% Rendah;
           sampai 60% Moderat; sampai 80% Tinggi; di atas 80% Sangat Tinggi.

        **Looking Forward**

        Estimasi sisa tahun menggunakan rata-rata bulanan aktual sampai cut-off,
        kemudian dikalikan jumlah bulan tersisa dan faktor skenario: Optimistis
        80%, Base 100%, dan Pesimistis 120%. Estimasi tahunan merupakan aktual
        YTD ditambah estimasi sisa tahun.

        **Batas interpretasi**

        Dashboard ini merupakan analisis historis dampak loss event. Record tanpa
        tanggal harian tidak dipaksakan menjadi event harian. Risk map penuh dan
        simulasi probabilistik akan ditambahkan setelah definisi frekuensi kejadian
        dan periode observasi disepakati.
        """
    )
