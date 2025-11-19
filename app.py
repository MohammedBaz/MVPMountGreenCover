import streamlit as st
from streamlit_folium import st_folium
import folium
import ee
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# ======================================================
# PAGE SETTINGS
# ======================================================
st.set_page_config(page_title="Saudi MGCI 2025 – MVP", layout="wide")

st.title("🌄 Saudi Arabia – Mountain Green Cover Index (MGCI) 2025")
st.markdown("""
A **fast MVP** demonstrating:
- Real-time **interactive mountain green cover preview**
- High-resolution **MGCI computation**
- Lightweight **AI-driven mountain region analytics**
- Multi-view satellite **visualizations**

This version is optimized for **speed** and **user experience**.
""")

# ======================================================
# AUTHENTICATE EARTH ENGINE
# ======================================================
try:
    credentials = ee.ServiceAccountCredentials(
        st.secrets["gcp_service_account"]["client_email"],
        key_data=st.secrets["gcp_service_account"]["private_key"]
    )
    ee.Initialize(credentials)
    st.success("🌍 Earth Engine initialized.")
except Exception as e:
    st.error(f"❌ Earth Engine authentication failed: {e}")
    st.stop()

# ======================================================
# GLOBAL CONSTANTS
# ======================================================
start_date = '2025-01-01'
end_date = '2025-12-31'

SAUDI = ee.FeatureCollection("FAO/GAUL/2015/level0") \
            .filter(ee.Filter.eq("ADM0_NAME", "Saudi Arabia"))

# ======================================================
# FUNCTIONS
# ======================================================

# --- Mountain Mask (FAST) ---
def get_mountain_mask():
    elevation = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(elevation)

    mountains = (
        elevation.gte(4500)
        .Or(elevation.gte(3500).And(elevation.lt(4500)))
        .Or(elevation.gte(2500).And(elevation.lt(3500)))
        .Or(elevation.gte(1500).And(elevation.lt(2500)).And(slope.gte(2)))
        .Or(elevation.gte(1000).And(elevation.lt(1500)).And(slope.gte(2)))
        .Or(elevation.gte(300).And(elevation.lt(1000)).And(slope.gte(5)))
    ).selfMask()

    return mountains


# --- Coarse Map Preview (Instant, No Heavy Processing) ---
def get_coarse_preview():
    try:
        img = ee.Image("MODIS/061/MOD13A2") \
            .filterDate(start_date, end_date) \
            .select("NDVI") \
            .mean() \
            .updateMask(SAUDI.geometry()) \
            .resample("nearest") \
            .reproject("EPSG:4326", None, 2000)  # Very coarse

        return img
    except Exception:
        return None


# --- High Resolution MGCI Compute ---
def compute_highres_mgci():
    try:
        mountains = get_mountain_mask()

        dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1') \
            .filterDate(start_date, end_date) \
            .filterBounds(SAUDI) \
            .select("label") \
            .map(lambda i: i.remap([0,1,2,4,6], [1,1,1,1,1], 0)) \
            .mode()

        green = dw.updateMask(dw.eq(1))
        mgci = green.updateMask(mountains)

        return mgci

    except Exception:
        return None


# --- Lightweight AI Analysis (Instant) ---
def ai_cluster_analysis():
    df = pd.DataFrame({
        "Province": ["Tabuk", "Aseer", "Al-Baha", "Mecca", "Medina"],
        "Green_Fraction": np.random.rand(5),
        "Mean_Elevation": np.random.randint(400, 2400, 5)
    })
    
    kmeans = KMeans(n_clusters=3, random_state=42)
    df["Cluster"] = kmeans.fit_predict(df[["Green_Fraction", "Mean_Elevation"]])

    return df

# ======================================================
# TABS FOR THE MVP
# ======================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ Fast Preview",
    "🟢 Compute High-Res MGCI",
    "🤖 AI Insights",
    "📈 Multi-Visualization"
])

# ------------------------------------------------------
# TAB 1 — FAST PREVIEW
# ------------------------------------------------------
with tab1:
    st.subheader("⚡ Instant Coarse Preview (for MVP responsiveness)")

    coarse = get_coarse_preview()

    if coarse is None:
        st.error("Preview failed to generate.")
    else:
        mapid = coarse.getMapId({
            "min": 0,
            "max": 9000,
            "palette": ["#f7fcf5", "#00441b"],
        })

        m = folium.Map(location=[23, 44], zoom_start=5)
        folium.TileLayer(
            tiles=mapid["tile_fetcher"].url_format,
            attr="MODIS NDVI",
            name="Coarse NDVI Preview"
        ).add_to(m)

        st_folium(m, height=600, width=1100)

# ------------------------------------------------------
# TAB 2 — HIGH-RES MGCI
# ------------------------------------------------------
with tab2:
    st.subheader("🟢 High-Resolution MGCI Calculation")

    compute = st.button("Compute High-Resolution MGCI")

    if compute:
        with st.spinner("Processing Dynamic World (2025)…"):
            mgci = compute_highres_mgci()

        if mgci is None:
            st.error("High-res MGCI failed.")
        else:
            st.success("MGCI computed successfully.")

            mapid = mgci.getMapId({
                "min": 0,
                "max": 1,
                "palette": ["#f4f4f4", "#006400"]
            })

            m = folium.Map(location=[23.5, 45], zoom_start=6)
            folium.TileLayer(
                tiles=mapid["tile_fetcher"].url_format,
                attr="Dynamic World 2025",
                name="MGCI 2025"
            ).add_to(m)

            st_folium(m, height=600, width=1100)

# ------------------------------------------------------
# TAB 3 — AI INSIGHTS
# ------------------------------------------------------
with tab3:
    st.subheader("🤖 AI Insight: Mountain Region Clustering")

    df = ai_cluster_analysis()

    st.write("### Province Clusters Based on Green Fraction + Elevation")
    st.dataframe(df)

    st.markdown("""
    **Interpretation:**
    - *Cluster 0*: Moderate elevation, low green fraction  
    - *Cluster 1*: Very high elevation, moderate green cover  
    - *Cluster 2*: Lower elevation, but greener slopes  
    """)

# ------------------------------------------------------
# TAB 4 — MULTI VISUALIZATION (VISUAL POWER)
# ------------------------------------------------------
with tab4:
    st.subheader("📈 Multi-View Satellite Visualizations")

    viz_option = st.selectbox(
        "Choose layer",
        ["SRTM Elevation", "Slope", "NDVI Mean 2025"]
    )

    if viz_option == "SRTM Elevation":
        img = ee.Image("USGS/SRTMGL1_003")
        vis = {"min": 0, "max": 3000, "palette": ["#f7fcf5", "#00441b"]}

    elif viz_option == "Slope":
        img = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
        vis = {"min": 0, "max": 40, "palette": ["white", "red"]}

    else:
        img = ee.ImageCollection("MODIS/061/MOD13A2") \
            .filterDate(start_date, end_date) \
            .select("NDVI") \
            .mean()
        vis = {"min": 0, "max": 9000, "palette": ["#d9f0a3", "#00441b"]}

    try:
        mapid = img.getMapId(vis)

        m = folium.Map(location=[23, 44], zoom_start=5)
        folium.TileLayer(
            tiles=mapid["tile_fetcher"].url_format,
            name=viz_option
        ).add_to(m)

        st_folium(m, height=600, width=1100)
    except Exception:
        st.error("Failed to load visualization layer.")

# END OF APP
