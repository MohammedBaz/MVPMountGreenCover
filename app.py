# app.py
import streamlit as st
from streamlit_folium import st_folium
import folium
import ee
import json
import pandas as pd
import altair as alt
import base64
from datetime import datetime

st.set_page_config(page_title="Saudi MGCI 2025 (MVP)", layout="wide")

st.title("🌿 Saudi Arabia — Mountain Green Cover Index (MGCI) MVP")
st.markdown("**Live map • SDG 15.4.2 • Google Earth Engine + Dynamic World**")

# --------- AUTHENTICATE Earth Engine ----------
try:
    credentials = ee.ServiceAccountCredentials(
        st.secrets["gcp_service_account"]["client_email"],
        key_data=st.secrets["gcp_service_account"]["private_key"]
    )
    ee.Initialize(credentials)
    st.success("✅ Earth Engine initialized")
except Exception as e:
    st.error(f"EE init failed: {e}")
    st.stop()

# --------- Sidebar controls ----------
st.sidebar.header("Settings")
start_date = st.sidebar.date_input("Start date", value=pd.to_datetime("2025-01-01"))
end_date = st.sidebar.date_input("End date", value=pd.to_datetime("2025-11-20"))
opacity = st.sidebar.slider("Green layer opacity", 0.0, 1.0, 0.8)
compute_button = st.sidebar.button("Compute MGCI")

# Optional: timeseries range selector
with st.sidebar.expander("Timeseries (optional)"):
    ts_start = st.date_input("TS start", value=pd.to_datetime("2016-01-01"))
    ts_end = st.date_input("TS end", value=pd.to_datetime("2025-12-31"))
    ts_interval = st.selectbox("TS interval", ["year", "month"], index=0)

# --------- Define geometry & datasets ----------
saudi = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(
    ee.Filter.eq('ADM0_NAME', 'Saudi Arabia')
)

elevation = ee.Image("USGS/SRTMGL1_003")
slope = ee.Terrain.slope(elevation)

# mountain mask (same logic as earlier, using Or/And)
mountain_cond = (
    elevation.gte(4500)
    .Or(elevation.gte(3500).And(elevation.lt(4500)))
    .Or(elevation.gte(2500).And(elevation.lt(3500)))
    .Or(elevation.gte(1500).And(elevation.lt(2500)).And(slope.gte(2)))
    .Or(elevation.gte(1000).And(elevation.lt(1500)).And(slope.gte(2)))
    .Or(elevation.gte(300).And(elevation.lt(1000)).And(slope.gte(5)))
)
mountains_mask = mountain_cond.selfMask().clip(saudi)

# helper: build Dynamic World green mask for a date range
def dynamicworld_green_mask(start, end, region):
    coll = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
        .filterDate(start, end) \
        .filterBounds(region) \
        .select("label")
    # remap label -> green(1) / non-green(0)
    # DynamicWorld label codes: 0:water,1:trees,2:grass,3:cloud,4:shrub,5:bare,6:snow,7:cultivation,8:built
    # We'll treat trees, grass, shrub, cultivation as green (1)
    def to_green(img):
        return img.remap([0,1,2,4,7],[0,1,1,1,1],0)
    green_mode = coll.map(lambda i: to_green(i)).mode()
    # threshold to get persistent green (>=0.5)
    green_bin = green_mode.gte(0.5).selfMask().clip(region)
    return green_bin

# precompute static map tiles for the chosen start/end
green_img = dynamicworld_green_mask(start_date.isoformat(), end_date.isoformat(), saudi) \
    .updateMask(mountains_mask)  # only mountains

vis_params = {'min': 0, 'max': 1, 'palette': ['#f4f4f4', '#006400']}

mapid = green_img.getMapId(vis_params)

# --------- Folium map and st_folium ----------
m = folium.Map(location=[23.5, 45], zoom_start=6, tiles="CartoDB positron")

folium.TileLayer(
    tiles=mapid['tile_fetcher'].url_format,
    attr='Google Earth Engine',
    name='2025 Green Cover',
    overlay=True,
    control=True,
    opacity=opacity
).add_to(m)

# add boundary (convert to GeoJSON client-side)
try:
    saudi_geojson = saudi.getInfo()
    folium.GeoJson(
        saudi_geojson,
        name="Saudi boundary",
        style_function=lambda feat: {"color": "red", "weight": 2, "fillOpacity": 0}
    ).add_to(m)
except Exception as e:
    st.warning(f"Could not retrieve GeoJSON for boundary (getInfo failed): {e}")

folium.LayerControl().add_to(m)

st.markdown("### 🔍 Interactive Map")
# render with st_folium (recommended)
st_folium(m, width=1200, height=650)

# --------- Compute MGCI when requested ----------
def compute_area_stats(green_img, mountains_mask, region):
    # pixel area (m^2) image
    pixel_area = ee.Image.pixelArea()

    # green area within region
    green_area_img = pixel_area.updateMask(green_img)
    green_area = green_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region.geometry(),
        scale=30,
        maxPixels=1e13
    ).get('area')

    # mountain total area (masked mountain pixels)
    mountain_area_img = pixel_area.updateMask(mountains_mask)
    mountain_area = mountain_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region.geometry(),
        scale=30,
        maxPixels=1e13
    ).get('area')

    # return numbers (will be ee Objects)
    return ee.Number(green_area), ee.Number(mountain_area)

if compute_button:
    with st.spinner("Computing MGCI... this may take 15–60s depending on region..."):
        try:
            green_area_ee, mountain_area_ee = compute_area_stats(green_img, mountains_mask, saudi)
            green_area = green_area_ee.getInfo() or 0.0
            mountain_area = mountain_area_ee.getInfo() or 0.0

            mgci_pct = (green_area / mountain_area * 100) if mountain_area > 0 else None

            # friendly formatting
            st.metric("Mountain area (km²)", f"{mountain_area/1e6:,.2f}")
            st.metric("Green area in mountains (km²)", f"{green_area/1e6:,.2f}")
            if mgci_pct is not None:
                st.success(f"MGCI: {mgci_pct:.2f}%")
            else:
                st.error("Could not compute MGCI (mountain_area==0)")

            # small report + download GeoJSON of green mask (vectorized)
            # vectorize green cells to polygons (optional & may be heavy)
            export_fc = green_img.reduceToVectors(
                geometry=saudi.geometry(),
                scale=30,
                geometryType='polygon',
                eightConnected=False,
                labelProperty='green',
                maxPixels=1e13
            )
            # get a small preview (first features) as GeoJSON
            try:
                export_geojson = export_fc.getInfo()
                geojson_str = json.dumps(export_geojson)
                b64 = base64.b64encode(geojson_str.encode()).decode()
                href = f'<a href="data:application/json;base64,{b64}" download="green_mask.geojson">⬇️ Download green_mask.geojson (preview)</a>'
                st.markdown(href, unsafe_allow_html=True)
            except Exception as e:
                st.info("Vectorization preview failed (server-side). You can export full raster/asset via Earth Engine Tasks.")
        except Exception as e:
            st.error(f"MGCI computation failed: {e}")

# --------- Timeseries (annual) - lightweight client-side chart using EE reductions ----------
def ts_mgci_by_year(start, end, region, mountains_mask):
    years = list(range(start.year, end.year + 1))
    rows = []
    for y in years:
        s = datetime(y, 1, 1).isoformat()
        e = datetime(y, 12, 31).isoformat()
        img = dynamicworld_green_mask(s, e, region).updateMask(mountains_mask)
        pixel_area = ee.Image.pixelArea()
        green_area = ee.Number(pixel_area.updateMask(img).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region.geometry(),
            scale=30,
            maxPixels=1e13
        ).get('area'))
        mountain_area = ee.Number(pixel_area.updateMask(mountains_mask).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region.geometry(),
            scale=30,
            maxPixels=1e13
        ).get('area'))
        # compute percent as ee.Number (but we'll getInfo below)
        percent = ee.Algorithms.If(mountain_area.gt(0), green_area.divide(mountain_area).multiply(100), None)
        try:
            ga = green_area.getInfo() or 0.0
            ma = mountain_area.getInfo() or 0.0
            pct = percent.getInfo() if (ma and ma > 0) else None
            rows.append({'year': y, 'green_km2': ga/1e6, 'mountain_km2': ma/1e6, 'pct': pct})
        except Exception:
            # if any getInfo fails, append None
            rows.append({'year': y, 'green_km2': None, 'mountain_km2': None, 'pct': None})
    return pd.DataFrame(rows)

with st.expander("Show Annual MGCI timeseries (2016–2025)"):
    if st.button("Compute timeseries"):
        with st.spinner("Computing timeseries (this may take some minutes)..."):
            df_ts = ts_mgci_by_year(ts_start, ts_end, saudi, mountains_mask)
            st.dataframe(df_ts)
            chart = alt.Chart(df_ts).mark_line(point=True).encode(
                x='year:O',
                y='pct:Q',
                tooltip=['year','green_km2','mountain_km2','pct']
            ).properties(width=800, height=300, title="Annual MGCI (%)")
            st.altair_chart(chart)

st.markdown("---")
st.caption("Notes: green mask uses Dynamic World labels remapped to 'green' (trees, grass, shrub, cultivation). "
           "MGCI = green area within mountain mask / mountain area. Results depend on date range and thresholds.")
