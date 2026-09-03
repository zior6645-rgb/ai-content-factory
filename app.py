import streamlit as st
import requests
import json

# Page Config
st.set_page_config(page_title="AI Global Content Factory", page_icon="🚀", layout="wide")

# Professional Sidebar
with st.sidebar:
    st.title("💰 Membership")
    st.success("Professional Plan: Active")
    st.write("Send **20 USDT** to support us:")
    st.code("YOUR_WALLET_ADDRESS", language="text")
    st.divider()
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    st.info("Get it free: aistudio.google.com")

st.title("🎬 AI Global Content Factory")
st.markdown("#### Turn YouTube Knowledge into Viral Content (Stable Version)")

# Input Section
manual_text = st.text_area("Paste Video Transcript here:", height=200, placeholder="Copy text from YouTube 'Show Transcript' and paste it here...")

if st.button("🚀 Generate Professional Content"):
    if not api_key:
        st.error("Please enter your API Key in the sidebar.")
    elif not manual_text:
        st.warning("Please paste the transcript text first.")
    else:
        with st.spinner("AI is thinking..."):
            # Direct API Call to Google (No library needed, avoids 404)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key.strip()}"
            headers = {'Content-Type': 'application/json'}
            prompt = f"Using this transcript, create a professional Blog Post, 5 Tweets, and a LinkedIn summary in English: {manual_text}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }

            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                result = response.json()
                
                if response.status_code == 200:
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    st.balloons()
                    st.success("Content Generated Successfully!")
                    st.markdown(ai_response)
                else:
                    st.error(f"Google API Error: {result['error']['message']}")
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")

st.divider()
st.caption("© 2024 Global AI Factory | Powered by Google Gemini (Free Tier)")
