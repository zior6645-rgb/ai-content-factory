import streamlit as st

st.set_page_config(page_title="AI Global Content Factory", page_icon="🎬", layout="wide")

st.title("🎬 AI Global Content Factory")

st.write("Your application is working correctly.")

api_key = st.text_input("Gemini API Key", type="password")

transcript = st.text_area("YouTube Transcript", height=250)

st.button("Generate Content")
