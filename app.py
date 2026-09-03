import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# Setup
st.set_page_config(page_title="AI Factory", layout="wide")

with st.sidebar:
    st.title("💰 Premium")
    st.code("YOUR_WALLET_ADDRESS")
    st.divider()
    # استفاده از استایل ساده برای جلوگیری از قرمزی بی دلیل
    api_key = st.text_input("Enter Gemini API Key:", type="password")

st.title("🎬 AI Global Content Factory")

if api_key:
    try:
        # حذف هرگونه فاصله اضافی
        key = api_key.strip()
        genai.configure(api_key=key)
        
        # استفاده از مدل پایدار gemini-pro برای جلوگیری از خطای 404
        model = genai.GenerativeModel('gemini-pro')
        
        # یک تست بسیار سریع برای تایید کلید
        test_res = model.generate_content("test")
        st.success("✅ AI Connected Successfully!")
        
        url = st.text_input("YouTube Link:")
        manual = st.text_area("OR Paste Transcript:")

        if st.button("Generate Content"):
            final_text = ""
            if manual:
                final_text = manual
            elif url:
                video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url).group(1)
                srt = YouTubeTranscriptApi.get_transcript(video_id)
                final_text = " ".join([t['text'] for t in srt])
            
            if final_text:
                with st.spinner("AI is thinking..."):
                    res = model.generate_content(f"Summarize this: {final_text}")
                    st.balloons()
                    st.markdown(res.text)
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("Please enter your API Key and press Enter.")
