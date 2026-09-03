import streamlit as st
from google import genai

st.set_page_config(
page_title="AI Global Content Factory",
page_icon="🎬"
)

st.title("AI Global Content Factory")

st.write("Gemini connection test")

api_key = st.text_input(
"Gemini API Key",
type="password"
)

if st.button("Test Gemini"):

```
if not api_key.strip():
    st.error("Please enter your Gemini API key.")
    st.stop()

try:
    client = genai.Client(
        api_key=api_key.strip()
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello in one short sentence."
    )

    st.success("Gemini connection is working.")

    st.write(response.text)

except Exception as error:

    st.error("Gemini connection failed.")

    st.code(str(error))
```
