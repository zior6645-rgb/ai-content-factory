import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# 1. Professional Page Configuration
st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🚀",
    layout="wide"
)

# 2. Sidebar - Settings & Monetization
with st.sidebar:
    st.title("💰 Premium Access")
    st.success("### Lifetime License")
    st.write("For unlimited AI power, send **20 USDT (TRC20)** to:")
    st.code("ENTER_YOUR_WALLET_ADDRESS_HERE", language="text")
    st.caption("Contact support for manual verification.")
    
    st.divider()
    st.header("⚙️ Configuration")
    # Using strip() to remove accidental spaces
    raw_key = st.text_input("Enter Gemini API Key:", type="password")
    api_key = raw_key.strip() if raw_key else None
    st.info("🔗 [Get Free API Key](https://aistudio.google.com/)")
    
    st.divider()
    st.caption("Version 1.1 | Developed by zior6645-rgb")

# 3. Main Interface
st.title("🎬 AI Global Content Factory")
st.markdown("#### Repurpose YouTube Knowledge into Viral Content")

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

# 5. Core Logic
if st.button("🚀 Generate High-Quality Content Bundle"):
    if not api_key:
        st.error("❌ Configuration Error: Please enter your API Key in the sidebar.")
    else:
        try:
            # Initialize AI
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            final_transcript = ""
            
            # Acquisition Logic
            if manual_text:
                final_transcript = manual_text
            elif url:
                video_id = get_video_id(url)
                if video_id:
                    with st.spinner("⏳ Extracting video script..."):
                        try:
                            srt = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'fa'])
                            final_transcript = " ".join([t['text'] for t in srt])
                        except:
                            st.error("⚠️ YouTube blocked auto-fetch. Please use **Option B (Manual Paste)**.")
                else:
                    st.error("❌ Invalid YouTube Link!")
            
            # AI Generation
            if final_transcript:
                with st.spinner("🤖 AI Content Architect is working..."):
                    prompt = f"""
                    Analyze the following transcript: {final_transcript}
                    
                    Create three distinct professional sections in English:
                    1. A Detailed Blog Post (SEO-optimized with headings).
                    2. 5 Viral Twitter Posts (with emojis).
                    3. A Concise LinkedIn Article Summary.
                    
                    Format: Use clean Markdown.
                    """
                    response = model.generate_content(prompt)
                    
                    st.balloons()
                    
                    # Display Results in Tabs
                    tab1, tab2, tab3 = st.tabs(["📝 Blog Post", "🐦 Twitter/X", "💼 LinkedIn"])
                    with tab1:
                        st.markdown(response.text)
                    with tab2:
                        st.write(response.text)
                    with tab3:
                        st.write(response.text)
                    
                    st.download_button("📥 Download Results", response.text, file_name="content_bundle.txt")
            else:
                st.warning("⚠️ No content found. Please provide a link or transcript.")
                
        except Exception as e:
            st.error(f"Connection Error: {e}")

# 6. Footer
st.divider()
st.markdown("<p style='text-align: center;'>© 2024 AI Global Content Factory | Built for Success</p>", unsafe_allow_html=True)
