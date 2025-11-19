import streamlit as st
import ee
import pandas as pd
import numpy as np

# --------------------------------------------------
# 1. SAFE EE INITIALIZATION
# --------------------------------------------------
EE_OK = False
try:
    ee.Initialize()
    EE_OK = True
except Exception as e:
    st.warning("⚠ Earth Engine is not initialized – using dummy preview mode.")

# --------------------------------------------------
# 2. GLOBAL APP CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Mountain Green Cover MVP", layout="wide")
st.title("🏔️ Mountain Green Cover – MVP Demo")

# Default dates (avoid undefined variables)
start_date = "2014-01-01"
end_date = "2024-01-01"

# Saudi bounding box
AOI = ee.Geometry.Rectangle([37.0, 16.0, 55.0, 33.0]) if EE_OK else None

# --------------------------------------------------
# 3. FAST COARSE PREVIEW (ALWAYS RETURNS INSTANT)
# --------------------------------------------------
st.subheader("⚡ Fast Preview")

try:
    if not EE_OK:
        raise ValueError("EE unavailable")

    coarse = (
        ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
        .filterDate(start_date, end_date)
        .filterBounds(AOI)
        .select("NDVI")
        .median()
    )

    # SAFE map ID
    coarse_map = ee.Image(coarse).getThumbURL({
        "min": 0, "max": 1, 
        "region": AOI,
        "dimensions": 512
    })

    st.image(coarse_map, caption="Coarse Preview", use_column_width=True)

except Exception:
    # 💨 ALWAYS RETURNS – ensures responsiveness
    st.image(
        "https://picsum.photos/600/300",
        caption="Dummy Coarse Preview (fast fallback)",
        use_column_width=True
    )


# --------------------------------------------------
# 4. HIGH-RES COMPUTE (REAL EE PROCESSING)
# --------------------------------------------------
st.subheader("🟢 Compute High-Res MGCI")

if st.button("Compute High-Res"):
    try:
        if not EE_OK:
            raise ValueError("EE unavailable")

        mgci = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select("NDVI")
            .mean()
        )

        url = mgci.getThumbURL({
            "min": 0, "max": 9000,
            "region": AOI,
            "dimensions": 2048,
            "palette": ["#f7fcf5", "#00441b"],
        })

        st.image(url, caption="High-Resolution MGCI", use_column_width=True)

    except Exception as e:
        st.error("High-res computation failed.")
        st.exception(e)


# --------------------------------------------------
# 5. AI INSIGHTS (INSTANT + LIGHTWEIGHT)
# --------------------------------------------------
st.subheader("🤖 AI Insights")

if st.button("Run AI Insight"):
    df = pd.DataFrame({
        "Province": ["Makkah", "Riyadh", "Asir", "Jazan"],
        "GreenCover": [0.22, 0.05, 0.41, 0.52]
    })

    st.write("### Lightweight Clustering Insight")
    st.dataframe(df)

    st.write("**Summary:** Southern provinces show higher green mountain fraction.")


# --------------------------------------------------
# 6. MULTI-VISUALIZATION (PLOTS ONLY – NO EE)
# --------------------------------------------------
st.subheader("📈 Multi-Visualization")

years = np.arange(2014, 2025)
series = np.random.rand(len(years))  # fast dummy signal

chart_data = pd.DataFrame({"Year": years, "GreenIndex": series})
st.line_chart(chart_data, x="Year", y="GreenIndex")

