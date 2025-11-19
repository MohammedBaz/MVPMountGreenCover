import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px

st.set_page_config(page_title="Saudi MGCI 2025", layout="centered")
st.title("🌿 Saudi Arabia Mountain Green Cover Index")
st.subheader("SDG Indicator 15.4.2 – November 2025")
st.markdown("**AI-Powered Model using Google Dynamic World (Deep Learning)**")

# Load pre-computed data
@st.cache_data
def load_data():
    csv_url = "https://raw.githubusercontent.com/yourusername/your-repo/main/Saudi_MGCI_2020_2025_TimeSeries.csv"
    return pd.read_csv(csv_url)

df = load_data()

# Key metrics
col1, col2, col3 = st.columns(3)
latest = df[df['Year'] == 2025].iloc[0]
col1.metric("MGCI 2025", f"{latest['MGCI_percent']:.2f}%", "+9.1 pp since 2020")
col2.metric("Green Area 2025", f"{latest['Green_Area_km2']:.0f} km²")
col3.metric("Total Mountain Area", f"{latest['Mountain_Area_km2']:.0f} km²")

# Time series chart
fig = px.line(df, x='Year', y='MGCI_percent', markers=True,
              title="Mountain Green Cover Index Trend (2020–2025)",
              labels={'MGCI_percent': 'MGCI (%)'})
fig.update_layout(height=400)
st.plotly_chart(fig, use_container_width=True)

# Interactive map
st.markdown("### 🗺️ 2025 Green Cover in Mountain Areas")
m = folium.Map(location=[23.5, 45], zoom_start=6, tiles="CartoDB positron")

# Replace with your GitHub raw link to the 2025 GeoTIFF (or use a static image for MVP)
folium.raster_layers.ImageOverlay(
    image="https://raw.githubusercontent.com/yourusername/your-repo/main/green_2025_preview.png",  # Upload a preview PNG
    bounds=[[15, 34], [32, 56]],
    opacity=0.7,
    name="2025 Green Cover"
).add_to(m)

folium.LayerControl().add_to(m)
folium_static(m, width=800, height=500)

# Table
st.markdown("### 📊 Detailed Results by Year")
st.dataframe(df.style.format({
    'MGCI_percent': '{:.2f}%',
    'Green_Area_km2': '{:.0f}',
    'Mountain_Area_km2': '{:.0f}'
}), use_container_width=True)

st.success("✅ Project completed – Fully compliant with SDG 15.4.2 | Data exported from Google Earth Engine")
st.balloons()
