import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="SolarAI - Güneş Üretim Tahmini",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ SolarAI: Güneş Enerjisi Üretim Tahmin Paneli")
st.markdown("Hava durumu ve ışınım API'si kullanılarak önümüzdeki 7 günün saatlik üretim tahmini.")

st.sidebar.header("Tesis ve Konum Parametreleri")

sehir = st.sidebar.selectbox("Konum Seçin", ["Kayseri", "Ankara", "İzmir", "Antalya", "İstanbul"])
kurulu_guc_kw = st.sidebar.number_input("Kurulu Güç (kWp)", min_value=1.0, max_value=5000.0, value=100.0, step=10.0)
panel_verimi = st.sidebar.slider("Panel / Sistem Verimi (%)", min_value=10, max_value=25, value=18) / 100.0
kayip_orani = st.sidebar.slider("Sistem Kayıpları (Kablo, Inverter, Toz) (%)", min_value=5, max_value=25, value=14) / 100.0

koordinatlar = {
    "Kayseri": {"lat": 38.7205, "lon": 35.4826},
    "Ankara": {"lat": 39.9334, "lon": 32.8597},
    "İzmir": {"lat": 38.4192, "lon": 27.1287},
    "Antalya": {"lat": 36.8969, "lon": 30.7133},
    "İstanbul": {"lat": 41.0082, "lon": 28.9784}
}

secilen_konum = koordinatlar[sehir]

@st.cache_data(ttl=3600)
def veri_cek(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=direct_normal_irradiance,diffuse_radiation,temperature_2m&forecast_days=7&timezone=auto"
    res = requests.get(url).json()
    
    saatlik = res["hourly"]
    df = pd.DataFrame({
        "Zaman": pd.to_datetime(saatlik["time"]),
        "Direkt_Isinim": saatlik["direct_normal_irradiance"],
        "Yayili_Isinim": saatlik["diffuse_radiation"],
        "Sicaklik": saatlik["temperature_2m"]
    })
    df["Toplam_Isinim"] = df["Direkt_Isinim"] + df["Yayili_Isinim"]
    return df

with st.spinner("Meteoroloji verileri alınıyor..."):
    df = veri_cek(secilen_konum["lat"], secilen_konum["lon"])

# Saatlik üretim tahmini (kWh)
df["Uretim_kWh"] = (df["Toplam_Isinim"] / 1000.0) * kurulu_guc_kw * (1.0 - kayip_orani)

st.markdown("---")
col1, col2, col3 = st.columns(3)

toplam_uretim = df["Uretim_kWh"].sum()
gunluk_ort = toplam_uretim / 7.0
pik_guc = df["Uretim_kWh"].max()

col1.metric("7 Günlük Toplam Üretim", f"{toplam_uretim:,.1f} kWh")
col2.metric("Günlük Ortalama Üretim", f"{gunluk_ort:,.1f} kWh")
col3.metric("Tahmini Pik Güç", f"{pik_guc:,.1f} kW")

st.markdown("---")

st.subheader("📊 7 Günlük Saatlik Güneş Üretim Profili")
fig = px.line(
    df, 
    x="Zaman", 
    y="Uretim_kWh", 
    labels={"Uretim_kWh": "Tahmini Üretim (kWh)", "Zaman": "Tarih ve Saat"},
    title=f"{sehir} İçin {kurulu_guc_kw} kWp Tesis Üretim Eğrisi",
    color_discrete_sequence=["#FFA500"]
)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

with st.expander("Detaylı Veri Tablosunu İncele ve İndir"):
    st.dataframe(df[["Zaman", "Toplam_Isinim", "Sicaklik", "Uretim_kWh"]].head(24))
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Tüm Verileri İndir (.CSV)", data=csv, file_name=f"{sehir}_solar_tahmin.csv", mime="text/csv")
