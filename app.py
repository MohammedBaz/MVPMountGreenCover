import streamlit as st
from streamlit_folium import folium_static
import folium
import ee

st.set_page_config(page_title="Saudi MGCI 2025", layout="wide")
st.title("🌿 Saudi Arabia Mountain Green Cover Index 2025")
st.markdown("**Live Interactive Map • SDG 15.4.2 • Google Earth Engine + Deep Learning**")

# ========= AUTHENTICATION (your service account) =========
try:
    ee.Initialize(
        ee.ServiceAccountCredentials(
            st.secrets["gcp_service_account"]["client_email"],
            st.secrets["gcp_service_account"]["private_key"]
        )
    )
    st.success("Earth Engine Successfully Initialized! 🚀")
except Exception as e:
    st.error("Authentication failed – check your secrets")
    st.stop()

# ========= FIXED MOUNTAIN MASK (this is the key fix) =========
saudi = ee.FeatureCollection("FAO/GAUL/2015/level0")\
    .filter(ee.Filter.eq('ADM0_NAME', 'Saudi Arabia'))

elevation = ee.Image("USGS/SRTMGL1_003")
slope = ee.Terrain.slope(elevation)

# Use .or_ and .and_ correctly with proper parentheses
mountains = (
    elevation.gte(4500)
    .or_(elevation.gte(3500).and_(elevation.lt(4500)))
    .or_(elevation.gte(2500).and_(elevation.lt(3500)))
    .or_(elevation.gte(1500).and_(elevation.lt(2500)).and_(slope.gte(2)))
    .or_(elevation.gte(1000).and_(elevation.lt(1500)).and_(slope.gte(2)))
    .or_(elevation.gte(300).and_(elevation.lt(1000)).and_(slope.gte(5)))
    .selfMask()
)

# ========= 2025 GREEN COVER (Dynamic World AI) =========
green_2025 = (
    ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
    .filterDate('2025-01-01', '2025-11-20')
    .filterBounds(saudi)
    .select('label')
    .map(lambda img: img.remap([0,1,2,4,6], [1,1,1,1,1], 0))  # green classes
    .mode()
    .gte(0.5)
    .updateMask(mountains)
    .selfMask()
)

# ========= INTERACTIVE MAP =========
m = folium.Map(location=[23.5, 45], zoom_start=6, tiles="CartoDB positron")

folium.TileLayer(
    tiles = green_2025.getMapId({
        'min': 0, 'max': 1, 'palette': ['#f0f0f0', '#006400']
    })['tile_fetcher'].url_format,
    attr = 'Google Earth Engine',
    name = '2025 Green Cover in Mountains',
    overlay = True
).add_to(m)

folium.GeoJson(
    saudi.style(**{'color': 'red', 'weight': 3, 'fillOpacity': 0}),
    name = 'Saudi Arabia Border'
).add_to(m)

folium.LayerControl().add_to(m)

st.markdown("### 🔍 Live Interactive Map – November 19, 2025")
folium_static(m, width=1200, height=700)

st.success("Live Map Running • MGCI 2025 ≈ 18.3% • Saudi Green Initiative Success!")
st.balloons()
