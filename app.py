import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# Page Config
st.set_page_config(page_title="AI Global Content Factory", layout="wide")

# Sidebar
with st.sidebar:
    st.title("💰 Premium Access")
    st.success("Send **20 USDT** to:")
    st.code("YOUR_WALLET_ADDRESS")
    st.divider()
    # استفاده از استایل برای حذف کادر قرمز احتمالی
    raw_key = st.text_input("Enter Gemini API Key:", type="password")
    api_key = raw_key.strip() if raw_key else None

st.title("🎬 AI Global Content Factory")

if api_key:
    try:
        # پیکربندی با آخرین استاندارد
        genai.configure(api_key=api_key)
        
        # استفاده از مدل 1.5 Flash که جایگزین نسخه های قبلی شده است
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # تست اتصال
        response = model.generate_content("Hi")
        st.success("✅ AI Connected Successfully!")
        
        url = st.text_input("YouTube Video Link:")
        manual_text = st.text_area("OR Paste Transcript manually:")

        if st.button("Generate Content"):
            final_source = ""
            if manual_text:
                final_source = manual_text
            elif url:
                video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url).group(1)
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                final_source = " ".join([t['text'] for t in transcript])
            
            if final_source:
                with st.spinner("Creating your content..."):
                    res = model.generate_content(f"Analyze this: {final_source}. Create a Blog Post and 5 Tweets in English.")
                    st.balloons()
                    st.markdown(res.text)
                    
    except Exception as e:
        # نمایش خطای دقیق برای حل مشکل
        st.error(f"Status: {str(e)}")
else:
    st.info("Please enter your API Key in the sidebar and press Enter.")
