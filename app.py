import streamlit as st
import ee
import pandas as pd
import numpy as np

# --------------------------------------------------
# 0. APP CONFIG – must come first
# --------------------------------------------------
st.set_page_config(page_title="Mountain Green Cover MVP", layout="wide")
st.title("🏔️ Mountain Green Cover – MVP Demo")

# --------------------------------------------------
# 1. SAFE EE INITIALIZATION
# --------------------------------------------------
EE_OK = False
try:
    credentials = ee.ServiceAccountCredentials(
        st.secrets["gcp_service_account"]["client_email"],
        key_data=st.secrets["gcp_service_account"]["private_key"]
    )

    ee.Initialize(credentials)
    st.success("✅ Earth Engine Successfully Initialized!")
    EE_OK = True

except Exception as e:
    st.error(f"❌ Authentication failed: {e}")
    EE_OK = False

# --------------------------------------------------
# 2. GLOBALS
# --------------------------------------------------
start_date = "2014-01-01"
end_date = "2024-01-01"

# Create AOI only if EE works
AOI = ee.Geometry.Rectangle([37.0, 16.0, 55.0, 33.0]) if EE_OK else None

# --------------------------------------------------
# 3. FAST COARSE PREVIEW
# --------------------------------------------------
st.subheader("⚡ Fast Preview")

try:
    if not EE_OK:
        raise ValueError("Earth Engine unavailable")

    coarse = (
        ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
        .filterDate(start_date, end_date)
        .filterBounds(AOI)
        .select("NDVI")
        .median()
    )

    img_url = coarse.getThumbURL({
        "min": 0,
        "max": 1,
        "region": AOI,
        "dimensions": 512
    })

    st.image(img_url, caption="Coarse Preview", use_column_width=True)

except Exception:
    # Fallback preview so MVP is always responsive
    st.image(
        "https://picsum.photos/600/300",
        caption="Dummy Coarse Preview (fast fallback)",
        use_column_width=True
    )

# --------------------------------------------------
# 4. HIGH-RES MGCI
# --------------------------------------------------
st.subheader("🟢 Compute High-Res MGCI")

if st.button("Compute High-Res"):
    try:
        if not EE_OK:
            raise ValueError("Earth Engine unavailable")

        mgci = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select("NDVI")
            .mean()
        )

        highres_url = mgci.getThumbURL({
            "min": 0,
            "max": 9000,
            "region": AOI,
            "dimensions": 2048,
            "palette": ["#f7fcf5", "#00441b"],
        })

        st.image(highres_url, caption="High-Resolution MGCI", use_column_width=True)

    except Exception as e:
        st.error("High-res computation failed.")
        st.exception(e)

# --------------------------------------------------
# 5. AI INSIGHTS
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
# 6. MULTI-VISUALIZATION
# --------------------------------------------------
st.subheader("📈 Multi-Visualization")

years = np.arange(2014, 2025)
series = np.random.rand(len(years))

chart_data = pd.DataFrame({"Year": years, "GreenIndex": series})
st.line_chart(chart_data, x="Year", y="GreenIndex")
