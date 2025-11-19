# ---------------- FAST / COARSE PREVIEW + AI ANALYSIS ----------------
import numpy as np
from sklearn.cluster import KMeans
import geopandas as gpd
import json
import time

# Caching wrappers for repeated EE operations
@st.cache_data(show_spinner=False)
def get_coarse_green_fraction_mapid(start_iso, end_iso, region, vis_params, scale=1000):
    """
    Return a MapID for a coarse green fraction map (fast).
    scale (meters) controls the internal reduction resolution; use large (e.g., 500-2000) for speed.
    """
    def dynamicworld_green_mask_img(s, e):
        coll = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
            .filterDate(s, e) \
            .filterBounds(region) \
            .select("label")
        def to_green(img):
            # treat trees, grass, shrub, cultivation as green (1)
            return img.remap([0,1,2,4,7],[0,1,1,1,1],0).rename('green')
        green_mean = coll.map(lambda i: to_green(i)).mean().rename('green_fraction')
        return green_mean

    green_frac = dynamicworld_green_mask_img(start_iso, end_iso).clip(region)
    # optionally mask by mountains_mask if you have it in global scope
    try:
        green_frac = green_frac.updateMask(mountains_mask)
    except Exception:
        pass

    # reduce resolution by reprojecting (faster tiling)
    green_small = green_frac.reproject(crs='EPSG:3857', scale=scale)
    mapid = green_small.getMapId(vis_params)
    return mapid

@st.cache_data(show_spinner=False)
def compute_coarse_mgci(start_iso, end_iso, region, scale=1000):
    """
    Compute MGCI (coarse) quickly using large scale. Returns (green_area_m2, mountain_area_m2).
    """
    # build green_fraction image (mean over period)
    coll = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
        .filterDate(start_iso, end_iso) \
        .filterBounds(region) \
        .select("label")
    def to_green(img):
        return img.remap([0,1,2,4,7],[0,1,1,1,1],0).rename('green')
    green_mean = coll.map(lambda i: to_green(i)).mean().rename('green_fraction')

    try:
        green_mean = green_mean.updateMask(mountains_mask)
    except Exception:
        pass

    pixel_area = ee.Image.pixelArea().rename('area')
    # compute total green area = sum(green_fraction * pixel_area)
    green_area_img = green_mean.multiply(pixel_area)
    green_area = ee.Number(green_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region.geometry(),
        scale=scale,
        maxPixels=1e13
    ).get('green_fraction')).getInfo()

    # compute mountain area (sum of pixel_area within mountains_mask)
    try:
        mountain_area_img = pixel_area.updateMask(mountains_mask)
        mountain_area = ee.Number(mountain_area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region.geometry(),
            scale=scale,
            maxPixels=1e13
        ).get('area')).getInfo()
    except Exception:
        mountain_area = None

    return green_area or 0.0, mountain_area or 0.0

# ---------------- UI: fast preview ----------------
st.markdown("### Fast preview (coarse, interactive)")
col1, col2 = st.columns([2,1])

with col2:
    st.info("This is a coarse preview designed to be very fast. Use 'Compute high-res' for detailed results.")
    if st.button("Compute high-res MGCI (slower)"):
        run_highres = True
    else:
        run_highres = False

# visualization params for MapID
vis_params_coarse = {'min': 0, 'max': 1, 'palette': ['#f4f4f4', '#006400']}

# get and display coarse map tiles (fast)
with st.spinner("Generating coarse preview map..."):
    try:
        mapid_coarse = get_coarse_green_fraction_mapid(start_date.isoformat(), end_date.isoformat(),
                                                      saudi, vis_params_coarse, scale=1000)
        m_fast = folium.Map(location=[23.5, 45], zoom_start=5, tiles="CartoDB positron")
        folium.TileLayer(
            tiles=mapid_coarse['tile_fetcher'].url_format,
            attr='GEE (coarse)',
            name='Coarse green fraction',
            overlay=True,
            opacity=0.85
        ).add_to(m_fast)
        folium.LayerControl().add_to(m_fast)
        # render quickly using st_folium
        st_folium(m_fast, width=900, height=500)
    except Exception as e:
        st.error(f"Coarse preview failed: {e}")

# compute and show coarse MGCI KPI right away (fast)
with st.spinner("Computing coarse MGCI (fast)…"):
    try:
        green_m2, mountain_m2 = compute_coarse_mgci(start_date.isoformat(), end_date.isoformat(), saudi, scale=1000)
        if mountain_m2 and mountain_m2 > 0:
            mgci_pct = green_m2 / mountain_m2 * 100.0
            st.metric(label="Coarse MGCI (preview)", value=f"{mgci_pct:.2f} %")
            st.write(f"Mountain area (coarse) = {mountain_m2/1e6:,.1f} km²; green area (coarse) = {green_m2/1e6:,.1f} km²")
        else:
            st.warning("Could not compute mountain area at coarse scale.")
    except Exception as e:
        st.error(f"Coarse MGCI calc failed: {e}")

# ---------------- Optional: per-region aggregation + lightweight AI clustering ----------------
st.markdown("### Lightweight AI insight: clustering provinces by mountain green fraction")
if st.button("Run regional clustering (fast)"):
    with st.spinner("Aggregating per-region stats and clustering..."):
        try:
            # get admin1 regions (FAO GAUL level1)
            provinces = ee.FeatureCollection("FAO/GAUL/2015/level1").filterBounds(saudi)
            # reduce each province to mean green_fraction (coarse)
            def province_green(feat):
                gf = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1") \
                        .filterDate(start_date.isoformat(), end_date.isoformat()) \
                        .filterBounds(feat.geometry()) \
                        .select("label") \
                        .map(lambda i: i.remap([0,1,2,4,7],[0,1,1,1,1],0)).mean().rename('green_fraction')
                # mask by mountains when possible
                try:
                    gf = gf.updateMask(mountains_mask)
                except Exception:
                    pass
                mean_val = ee.Number(gf.reduceRegion(reducer=ee.Reducer.mean(), geometry=feat.geometry(), scale=1000, maxPixels=1e13).get('green_fraction'))
                return feat.set({'green_fraction': mean_val})
            provinces_stats = provinces.map(province_green)

            # bring a small table client-side (safe: few features)
            prov_info = provinces_stats.select(['ADM1_NAME','green_fraction']).getInfo()
            rows = []
            for f in prov_info['features']:
                name = f['properties'].get('ADM1_NAME') or f['properties'].get('NAME_1') or "unknown"
                v = f['properties'].get('green_fraction')
                rows.append({'province': name, 'green_fraction': (v if v is not None else 0.0)})
            import pandas as pd
            df_prov = pd.DataFrame(rows).dropna().reset_index(drop=True)

            # run a tiny KMeans (k=3) on green fraction
            k = min(3, max(2, len(df_prov)//3))
            if len(df_prov) >= 3:
                km = KMeans(n_clusters=k, random_state=0).fit(df_prov[['green_fraction']])
                df_prov['cluster'] = km.labels_.astype(int)
                st.dataframe(df_prov.sort_values('green_fraction'))
                # simple chart
                chart = alt.Chart(df_prov).mark_bar().encode(
                    x='province',
                    y='green_fraction',
                    color='cluster:N',
                    tooltip=['province','green_fraction','cluster']
                ).properties(width=800, height=300)
                st.altair_chart(chart)
            else:
                st.info("Not enough provinces found to cluster.")
        except Exception as e:
            st.error(f"Regional clustering failed: {e}")

# ---------------- High-res explicit compute (only when user asked) ----------------
if run_highres:
    st.markdown("## High-resolution MGCI (explicit request)")
    st.warning("High-resolution computation can take several minutes. This runs at finer scale (e.g., 30m).")
    if st.button("Start high-res now"):
        start_time = time.time()
        with st.spinner("Running high-res MGCI at 30m... this may take multiple minutes..."):
            try:
                highres_green_m2, highres_mountain_m2 = compute_coarse_mgci(start_date.isoformat(), end_date.isoformat(), saudi, scale=30)
                if highres_mountain_m2 > 0:
                    mgci_high = highres_green_m2 / highres_mountain_m2 * 100.0
                    st.success(f"High-res MGCI = {mgci_high:.2f}% (computed at ~30m)")
                    st.write(f"Time elapsed: {time.time() - start_time:.0f} s")
                else:
                    st.error("High-res mountain area is zero.")
            except Exception as e:
                st.error(f"High-res computation failed: {e}")
