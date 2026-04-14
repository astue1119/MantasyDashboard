import streamlit as st

st.set_page_config(page_title="Fantasy Dashboard", layout="wide")

st.title("🏈 Fantasy Football Dashboard")

st.write("Use the sidebar to navigate between pages.")

import os
st.write("Files in directory:", os.listdir())