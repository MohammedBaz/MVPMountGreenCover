import streamlit as st
from streamlit_folium import folium_static
import folium
import ee

# Streamlit page config
st.set_page_config(page_title="Saudi MGCI 2025", layout="wide")

st.title("🌿 Saudi Arabia Mountain Green Cover Index 2025")
st.markdown("**Live Interactive Map • SDG 15.4.2 • Google Earth Engine + Deep Learning**")

# ========= AUTHENTICATION (your service account) =========
try:
    credentials = ee.ServiceAccountCredentials(
        st.secrets["gcp_service_account"]["client_email"],
        key_data=st.secrets["gcp_service_account"]["private_key"]
    )
    
    ee.Initialize(credentials)
    st.success("✅ Earth Engine Successfully Initialized!")

except Exception as e:
    st.error(f"❌ Authentication failed: {e}")
    st.stop()
