import streamlit as st
from google import genai

st.title("AI Global Content Factory")

api_key = st.text_input("Gemini API Key", type="password")

st.write("Application is ready.")
