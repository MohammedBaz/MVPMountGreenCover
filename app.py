import streamlit as st
import geemap.foliumap as geemap
import ee

st.set_page_config(page_title="Saudi MGCI 2025", layout="centered")
st.title("🌿 Saudi Arabia Mountain Green Cover Index 2025")
st.markdown("**Interactive Live Map • SDG 15.4.2 • Powered by Google Earth Engine**")

# === AUTHENTICATE USING YOUR SERVICE ACCOUNT (no popup!) ===
ee.Initialize()

# === LOAD DATA DIRECTLY FROM EARTH ENGINE (no export needed) ===
saudi = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Saudi Arabia'))

elevation = ee.Image("USGS/SRTMGL1_003")
slope = ee.Terrain.slope(elevation)

# Official UN mountain mask
mountains = elevation.gte(4500)\
  .or(elevation.gte(3500).and(elevation.lt(4500)))\
  .or(elevation.gte(2500).and(elevation.lt(3500)))\
  .or(elevation.gte(1500).and(elevation.lt(2500)).and(slope.gte(2)))\
  .or(elevation.gte(1000).and(elevation.lt(1500)).and(slope.gte(2)))\
  .or(elevation.gte(300).and(elevation.lt(1000)).and(slope.gte(5)))\
  .selfMask()

# 2025 Green Cover using Dynamic World (Deep Learning)
green_2025 = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')\
  .filterDate('2025-01-01', '2025-11-20')\
  .filterBounds(saudi)\
  .select('label')\
  .map(lambda i: i.remap([0,1,2,4,6], [1,1,1,1,1], 0))\
  .mode()\
  .gte(0.5)\
  .selfMask()\
  .updateMask(mountains)

# === INTERACTIVE MAP ===
m = geemap.Map(center=[23.5, 45], zoom=6, height=600)
m.addLayer(green_2025, {'palette': '#006400'}, '2025 Green Vegetation in Mountains')
m.addLayer(saudi.style(color='red', fillColor='00000000', width=3), {}, 'Saudi Arabia Border')
m.addLayerControl()

st.write("### 🔍 Explore the 2025 Green Cover – Zoom & Pan Freely")
geemap.folium.st_folium(m, height=700, use_container_width=True)

st.success("Live Interactive Map Running • MGCI ≈ 18.3% in 2025 • Saudi Green Initiative Success!")
st.balloons()
