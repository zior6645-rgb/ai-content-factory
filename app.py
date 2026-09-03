import streamlit as st
from google import genai

st.set_page_config(
page_title="AI Global Content Factory",
page_icon="🎬"
)

st.title("AI Global Content Factory")

api_key = st.text_input(
"Gemini API Key",
type="password"
)

st.write("Enter your Gemini API key and press the button.")

button = st.button(
"Test Gemini",
type="primary"
)

st.write("Button ready.")
