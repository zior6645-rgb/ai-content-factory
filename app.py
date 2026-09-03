import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# 1. Page Configuration
st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🚀",
    layout="wide"
)

# 2. Sidebar - Monetization & Settings
with st.sidebar:
    st.title("💰 Premium Access")
    st.success("### Professional License")
    st.write("For unlimited AI processing power, send **20 USDT (TRC20)** to:")
    st.code("YOUR_WALLET_ADDRESS_HERE", language="text")
    st.caption("Verification: 1-2 hours. Contact: support@yourdomain.com")
    
    st.divider()
    st.header("⚙️ API Configuration")
    raw_key = st.text_input("Enter Gemini API Key:", type="password")
    api_key = raw_key.strip() if raw_key else None
    st.info("🔗 [Get Free API Key](https://aistudio.google.com/)")
    
    st.divider()
    st.caption("Version 2.0 | Global Release")

# 3. Main Interface
st.title("🎬 AI Global Content Factory")
st.markdown("#### Repurpose YouTube Videos into Viral Content Instantly")

# Helper function to extract Video ID
def get_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# 4. Input Section
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔗 Option A: Auto-Fetch")
    url = st.text_input("YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

with col2:
    st.markdown("### ⌨️ Option B: Manual Paste")
    manual_text = st.text_area("Paste Transcript (Failsafe):", placeholder="Copy from YouTube 'Show Transcript'...", height=100)

st.divider()

# 5. Core Execution Logic
if st.button("🚀 Generate High-Quality Content Bundle"):
    if not api_key:
        st.error("❌ Configuration Error: Please enter your API Key in the sidebar.")
    else:
        try:
            # Configure AI
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            final_transcript = ""
            
            # Step 1: Content Acquisition
            if manual_text:
                final_transcript = manual_text
            elif url:
                video_id = get_video_id(url)
                if video_id:
                    with st.spinner("⏳ Extracting video script..."):
                        try:
                            # Tries to fetch English transcript
                            srt = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                            final_transcript = " ".join([t['text'] for t in srt])
                        except:
                            st.error("⚠️ YouTube blocked automated access. Please use **Option B (Manual Paste)**.")
                else:
                    st.error("❌ Invalid YouTube Link format!")
            
            # Step 2: Content Generation
            if final_transcript:
                with st.spinner("🤖 AI Content Architect is working..."):
                    prompt = f"""
                    You are an expert content strategist. Based on this transcript: {final_transcript}
                    
                    Generate three distinct professional sections:
                    1. A Detailed SEO Blog Post (with H1, H2, H3 tags).
                    2. 5 Engaging Twitter Posts (with emojis and hashtags).
                    3. A Concise LinkedIn Article Summary.
                    
                    Output Language: English. Format: Professional Markdown.
                    """
                    response = model.generate_content(prompt)
                    
                    st.balloons()
                    
                    # Step 3: Professional Display in Tabs
                    tab1, tab2, tab3 = st.tabs(["📝 Blog Post", "🐦 Twitter/X", "💼 LinkedIn"])
                    
                    with tab1:
                        st.markdown(response.text)
                    with tab2:
                        st.write(response.text)
                    with tab3:
                        st.write(response.text)
                    
                    # Step 4: Download Feature
                    st.download_button(
                        label="📥 Download All Content",
                        data=response.text,
                        file_name="ai_content_factory.txt",
                        mime="text/plain"
                    )
            else:
                st.warning("⚠️ No data detected. Please provide a link or paste a transcript.")
                
        except Exception as e:
            st.error(f"System Error: {str(e)}")

# 6. Global Footer
st.divider()
st.markdown("<p style='text-align: center;'>© 2024 AI Global Content Factory | Built for Success</p>", unsafe_allow_html=True)
