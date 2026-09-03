import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re

# 1. Global Page Configuration
st.set_page_config(
    page_title="AI Content Factory | Global Edition",
    page_icon="🚀",
    layout="wide"
)

# 2. Advanced Professional Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { 
        height: 60px; 
        background-color: #ffffff; 
        border: 1px solid #e0e0e0;
        border-radius: 10px; 
        font-weight: bold;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #FF4B4B !important; 
        color: white !important; 
        border: none;
    }
    div.stButton > button:first-child {
        background-color: #FF4B4B;
        color: white;
        border-radius: 10px;
        height: 3.5rem;
        font-weight: bold;
        font-size: 1.2rem;
        border: none;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #D43F3F;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Sidebar - Monetization & Settings
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2091/2091665.png", width=80)
    st.title("💰 Monetization")
    st.success("### Premium Membership")
    st.write("For unlimited AI processing and early access to new features, send **20 USDT (TRC20)** to:")
    st.code("ENTER_YOUR_WALLET_ADDRESS_HERE", language="text") # آدرس تترت رو اینجا بذار
    st.caption("Verification usually takes 1-2 hours. Contact support for help.")
    
    st.divider()
    st.header("⚙️ API Configuration")
    api_key = st.text_input("Enter Gemini API Key:", type="password", help="Get a free key from Google AI Studio")
    st.info("🔗 [Get Your API Key Here](https://aistudio.google.com/)")
    
    st.divider()
    st.markdown("Developed by **zior6645-rgb**")
    st.caption("Version 2.0 | Stable Release")

# 4. Main Header
st.title("🎬 AI Global Content Factory")
st.markdown("#### The All-in-One AI Engine to Repurpose Video into Viral Content")
st.divider()

# 5. Dual-Input Section
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🌐 Option A: YouTube Link")
    youtube_url = st.text_input("Auto-Fetch from URL:", placeholder="https://www.youtube.com/watch?v=...")

with col2:
    st.markdown("### ⌨️ Option B: Manual Transcript")
    manual_transcript = st.text_area("Paste Video Script (Failsafe):", placeholder="Copy transcript from YouTube and paste it here if auto-fetch is blocked...", height=100)

with st.expander("❓ How to get the transcript manually from YouTube?"):
    st.write("1. Open the video on YouTube.com")
    st.write("2. Click '... More' under the video title.")
    st.write("3. Click 'Show Transcript'.")
    st.write("4. Copy all text and paste it into Option B above.")

# 6. Core Engine Logic
if st.button("🚀 Generate Professional Content Bundle"):
    if not api_key:
        st.error("❌ Configuration Error: Please enter your API Key in the sidebar.")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            final_data = ""
            
            # Acquisition Logic
            if manual_transcript:
                final_data = manual_transcript
            elif youtube_url:
                with st.spinner("⏳ Connecting to YouTube services..."):
                    try:
                        # Improved Regex for Video ID
                        video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url).group(1)
                        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'fa'])
                        final_data = " ".join([entry['text'] for entry in transcript_data])
                    except Exception as e:
                        st.error("⚠️ YouTube blocked automated access. Please use **Option B (Manual Paste)**.")
            
            # AI Generation Logic
            if final_data:
                with st.spinner("🤖 AI content architect is analyzing the data..."):
                    prompt = f"""
                    You are a world-class content creator and SEO expert. Analyze the following transcript:
                    {final_data}
                    
                    Please produce three high-quality sections in professional English:
                    1. A Detailed Blog Post: SEO-optimized, engaging headings, and a clear conclusion.
                    2. Twitter/X Thread: 5 viral-style posts with relevant emojis and hashtags.
                    3. LinkedIn Article: Professional summary for a business audience.
                    
                    Format: Use clean Markdown.
                    """
                    response = model.generate_content(prompt)
                    
                    st.balloons()
                    st.divider()
                    
                    # 7. Organized Professional Display
                    tab1, tab2, tab3 = st.tabs(["📝 SEO Blog Post", "🐦 Twitter/X Bundle", "💼 LinkedIn Article"])
                    
                    with tab1:
                        st.markdown(response.text)
                    
                    with tab2:
                        st.info("Ready-to-post viral thread for X")
                        st.write(response.text)
                        
                    with tab3:
                        st.write(response.text)
                    
                    # 8. Export Feature
                    st.download_button(
                        label="📥 Download Content as Text File",
                        data=response.text,
                        file_name="ai_content_bundle.txt",
                        mime="text/plain"
                    )
            else:
                st.warning("⚠️ No data found. Please provide a YouTube link or paste the transcript manually.")
                    
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# 9. Footer
st.divider()
st.markdown("<p style='text-align: center; color: #7f8c8d;'>© 2024 AI Global Content Factory | Built for International Business</p>", unsafe_allow_html=True)
