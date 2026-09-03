import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# 1. Global Page Configuration
st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🚀",
    layout="wide"
)

# 2. Professional UI Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        background-color: #f0f2f6; 
        border-radius: 5px; 
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #FF4B4B !important; 
        color: white !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Sidebar - Settings & Monetization
with st.sidebar:
    st.title("💰 Premium Access")
    st.success("### Unlock Pro Features")
    st.write("To get unlimited AI processing power, send **20 USDT (TRC20)** to:")
    st.code("ENTER_YOUR_WALET_ADDRESS_HERE", language="text")
    st.caption("Contact: support@yourglobaldomain.com")
    
    st.divider()
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key:", type="password", help="Get your free key from Google AI Studio")
    st.info("🔗 [Get Your API Key Here](https://aistudio.google.com/)")
    
    st.divider()
    st.caption("Powered by Google Gemini Pro | v1.0")

# 4. Main Application Interface
st.title("🎬 AI Global Content Factory")
st.markdown("#### Repurpose YouTube Videos into Viral Content Instantly")

# Layout Columns
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🔗 Method 1: Video Link")
    youtube_url = st.text_input("Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")

with col2:
    st.markdown("### ⌨️ Method 2: Manual Transcript")
    manual_text = st.text_area("Paste Transcript manually (Failsafe):", placeholder="Paste the text here if auto-fetch is blocked...", height=100)

# Guide for Users
with st.expander("❓ How to get Video Transcript from YouTube?"):
    st.write("1. Open the video on YouTube.")
    st.write("2. Click '... More' under the video title.")
    st.write("3. Select 'Show Transcript'.")
    st.write("4. Copy all text and paste it into Method 2 above.")

# 5. Core Logic & AI Processing
if st.button("🚀 Generate Professional Content"):
    if not api_key:
        st.error("❌ API Key is missing! Please enter it in the sidebar.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            final_content = ""
            
            # Step 1: Data Acquisition
            if manual_text:
                final_content = manual_text
            elif youtube_url:
                with st.spinner("⏳ Accessing YouTube servers..."):
                    try:
                        # Extract Video ID using Regex
                        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                            final_content = " ".join([entry['text'] for entry in transcript_data])
                        else:
                            st.error("❌ Invalid YouTube URL format.")
                    except:
                        st.error("⚠️ YouTube blocked automated access. Please use Method 2 (Manual Paste).")
            
            # Step 2: AI Generation
            if final_content:
                with st.spinner("🤖 AI Content Architect is working..."):
                    prompt = f"""
                    You are an expert content strategist. Based on the following transcript, create:
                    1. A long-form professional Blog Post (SEO optimized with H1, H2 tags).
                    2. 5 Viral Twitter/X Posts (with emojis and hashtags).
                    3. A professional LinkedIn Article Summary.
                    
                    Transcript: {final_content}
                    
                    Language: Professional English. Format: Markdown.
                    """
                    response = model.generate_content(prompt)
                    
                    st.balloons()
                    st.divider()
                    
                    # Step 3: Organized Display
                    tab1, tab2, tab3 = st.tabs(["📝 Blog Post", "🐦 Twitter Bundle", "💼 LinkedIn Article"])
                    
                    with tab1:
                        st.markdown(response.text)
                    
                    with tab2:
                        st.info("Ready-to-post threads for X")
                        st.write(response.text)
                        
                    with tab3:
                        st.write(response.text)
                    
                    # Step 4: Download Option
                    st.download_button(
                        label="📥 Download All Results",
                        data=response.text,
                        file_name="ai_generated_content.txt",
                        mime="text/plain"
                    )
                    
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# 6. Global Footer
st.divider()
st.markdown("<p style='text-align: center;'>© 2024 AI Global Content Factory | Built for Success</p>", unsafe_allow_html=True)
