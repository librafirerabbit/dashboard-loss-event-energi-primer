from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Dashboard Loss Event Energi Primer",
    page_icon="⚡",
    layout="wide",
)

SHEET_ID = "1XgArP1hSelfwEE5slWuRapmwuIr5T1QT757zgy6l-_w"
DATA_GID = "1521184887"
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
            df[column] = pd.to_numeric(df[column], errors="coerce")

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

tab_overview, tab_quality, tab_detail, tab_method = st.tabs(
    ["Ringkasan", "Kualitas Data", "Detail Event", "Metodologi"]
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

with tab_quality:
    q1, q2, q3 = st.columns(3)
    detailed = int((filtered.get("Kelengkapan_Waktu", "") == "TANGGAL LENGKAP").sum())
    monthly_only = int((filtered.get("Kelengkapan_Waktu", "") == "HANYA BULAN").sum())
    review = int((filtered.get("Event_Layak_Model", "") != "LAYAK").sum())
    q1.metric("Tanggal Lengkap", f"{detailed:,}")
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

        **Batas interpretasi**

        Dashboard ini merupakan analisis historis dampak loss event. Record tanpa
        tanggal harian tidak dipaksakan menjadi event harian. Risk map penuh dan
        simulasi probabilistik akan ditambahkan setelah definisi frekuensi kejadian
        dan periode observasi disepakati.
        """
    )

