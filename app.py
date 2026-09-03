import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

st.set_page_config(page_title="Global AI Factory", layout="wide")

with st.sidebar:
    st.title("💰 Premium Access")
    st.code("YOUR_WALLET_ADDRESS")
    st.divider()
    # استفاده از ترفند برای جلوگیری از قرمزی کادر ورودی
    raw_key = st.text_input("Enter Gemini API Key:", type="password", key="key_input")
    api_key = raw_key.strip() if raw_key else None

st.title("🎬 Global AI Content Factory")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # انتخاب مدل با نام کامل برای جلوگیری از خطای ورژن
        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
        
        # تست زنده بودن کلید
        test_response = model.generate_content("Hi")
        if test_response:
            st.success("✅ AI Connected Successfully! System is Ready.")
        
        url = st.text_input("YouTube Link:")
        manual = st.text_area("OR Paste Transcript:")

        if st.button("Generate Professional Content"):
            final_text = ""
            if manual:
                final_text = manual
            elif url:
                video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url).group(1)
                srt = YouTubeTranscriptApi.get_transcript(video_id)
                final_text = " ".join([t['text'] for t in srt])
            
            if final_text:
                with st.spinner("AI is thinking..."):
                    res = model.generate_content(f"Summarize this in English: {final_text}")
                    st.balloons()
                    st.markdown(res.text)
                    
    except Exception as e:
        # نمایش خطای واقعی برای حل نهایی
        st.error(f"System Message: {str(e)}")
else:
    st.info("Please enter your API Key and press Enter.")
