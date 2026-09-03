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

st.write("Paste your API key above.")

try:

```
client = genai.Client(
    api_key=api_key
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello in one short sentence."
)

st.success("Gemini is connected successfully.")

st.write(response.text)
```

except Exception as error:

```
st.warning(
    "Enter a valid Gemini API key to test the connection."
)
```
