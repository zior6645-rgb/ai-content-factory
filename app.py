import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# Professional Page Setup
st.set_page_config(
    page_title="Global AI Content Factory",
    page_icon="🚀",
    layout="wide"
)

# Professional Header & CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 5px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar - Wallet & API Configuration
with st.sidebar:
    st.title("💰 Premium Access")
    st.success("### Professional License")
    st.write("For unlimited AI processing, send **20 USDT (TRC20)** to:")
    st.code("YOUR_WALLET_ADDRESS_HERE", language="text") # آدرس تترت را اینجا بگذار
    st.caption("Verification takes 1-2 hours. Contact: support@globalai.com")
    
    st.divider()
    st.header("⚙️ Configuration")
    raw_key = st.text_input("Enter Gemini API Key:", type="password")
    api_key = raw_key.strip() if raw_key else None
    st.info("🔗 [Get Key: Google AI Studio](https://aistudio.google.com/)")
    
    st.divider()
    st.caption("v2.1 Stable | Powered by Google Gemini")

# Main Interface
st.title("🎬 Global AI Content Factory")
st.markdown("#### Transform YouTube Videos into Viral Articles & Social Posts")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔗 Method 1: Auto-Link")
    url = st.text_input("YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

with col2:
    st.markdown("### ⌨️ Method 2: Manual Paste (Failsafe)")
    manual_text = st.text_area("Paste Transcript here:", placeholder="Copy from YouTube 'Show Transcript'...", height=100)

st.divider()

# Execution Logic
if st.button("🚀 Generate High-Quality Content Bundle"):
    if not api_key:
        st.error("❌ Configuration Error: Please enter your API Key in the sidebar.")
    else:
        try:
            # Fixing the Connection Issue
            genai.configure(api_key=api_key)
            # Use 'gemini-1.5-flash' - ensured compatibility
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            final_transcript = ""
            
            if manual_text:
                final_transcript = manual_text
            elif url:
                with st.spinner("⏳ Extracting video script..."):
                    try:
                        video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url).group(1)
                        srt = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                        final_transcript = " ".join([t['text'] for t in srt])
                    except:
                        st.error("⚠️ YouTube blocked auto-fetch. Please use **Method 2 (Manual Paste)**.")
            
            if final_transcript:
                with st.spinner("🤖 AI Architect is writing your content..."):
                    prompt = f"Analyze this transcript: {final_transcript}. Create: 1. A Professional Blog Post. 2. 5 Viral Tweets. 3. A LinkedIn Summary. Language: Professional English."
                    response = model.generate_content(prompt)
                    
                    st.balloons()
                    tab1, tab2, tab3 = st.tabs(["📝 Blog Post", "🐦 Twitter/X", "💼 LinkedIn"])
                    with tab1:
                        st.markdown(response.text)
                    with tab2:
                        st.write(response.text)
                    with tab3:
                        st.write(response.text)
                    
                    st.download_button("📥 Download Results", response.text, file_name="ai_content.txt")
            else:
                st.warning("⚠️ No data detected. Please provide a link or transcript.")
                
        except Exception as e:
            st.error(f"System Error: {str(e)}")

st.divider()
st.markdown("<p style='text-align: center;'>© 2024 AI Global Content Factory | International Edition</p>", unsafe_allow_html=True)
