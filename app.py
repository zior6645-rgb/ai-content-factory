import streamlit as st
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
import re

# Page Config
st.set_page_config(page_title="AI Global Factory", page_icon="⚡", layout="wide")

# Sidebar for Settings
with st.sidebar:
    st.title("⚙️ Configuration")
    # دریافت کلید مستقیماً از ویجت (بدون نیاز به Secrets برای سادگی فعلی)
    raw_key = st.text_input("Enter Groq API Key:", type="password")
    api_key = raw_key.strip() if raw_key else None
    st.info("🔗 [Get Groq Key](https://console.groq.com/keys)")
    st.divider()
    st.write("💰 **Premium Wallet:**")
    st.code("YOUR_USDT_ADDRESS") 

st.title("🎬 AI Global Content Factory")

if api_key:
    try:
        # تست کلید
        client = Groq(api_key=api_key)
        # یک پیام تست کوچک به گروک می‌فرستیم تا مطمئن شویم وصل شده
        st.success("✅ Groq AI is Connected!")
        
        col1, col2 = st.columns(2)
        with col1:
            url = st.text_input("YouTube URL:")
        with col2:
            manual = st.text_area("OR Paste Transcript manually:")

        if st.button("🚀 Generate Content"):
            final_text = ""
            if manual:
                final_text = manual
            elif url:
                with st.spinner("Extracting..."):
                    video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url).group(1)
                    srt = YouTubeTranscriptApi.get_transcript(video_id)
                    final_text = " ".join([t['text'] for t in srt])
            
            if final_text:
                with st.spinner("Llama 3 is writing..."):
                    chat_completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": f"Create a professional Blog Post and 5 Tweets from this: {final_text}"}],
                        model="llama-3.3-70b-versatile",
                    )
                    st.balloons()
                    st.markdown(chat_completion.choices[0].message.content)
            else:
                st.warning("Please provide a link or text.")

    except Exception as e:
        # اگر خطایی داد، اینجا به ما می‌گوید
        st.error(f"Groq Error: {str(e)}")
else:
    st.info("👈 Please enter your Groq API Key in the sidebar and press ENTER.")
