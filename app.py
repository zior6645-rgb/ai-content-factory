import streamlit as st
from google import genai

st.set_page_config(page_title="AI Global Content Factory", page_icon="🎬")

st.title("AI Global Content Factory")

api_key = st.text_input("Gemini API Key", type="password")

button = st.button("Test Gemini", type="primary")

if button:
key = api_key.strip()
if key == "":
st.error("Please enter your Gemini API key.")
else:
client = genai.Client(api_key=key)
response = client.models.generate_content(
model="gemini-2.5-flash",
contents="Say hello in one short sentence."
)
st.success("Gemini connection is working.")
st.write(response.text)
