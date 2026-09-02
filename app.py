import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# UI Configuration
st.set_page_config(page_title="AI Content Factory", page_icon="🚀")
st.title("🎬 Global AI Content Factory")
st.markdown("##### Convert YouTube Videos to Professional Articles & Social Posts")

# Sidebar for Settings
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    st.info("Get your free API key from: https://aistudio.google.com/")

# Main Logic
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    youtube_link = st.text_input("Paste YouTube Video URL here:")

    if youtube_link and "youtube.com" in youtube_link:
        try:
            video_id = youtube_link.split("v=")[1].split("&")[0]
            
            if st.button("Generate Content"):
                with st.spinner('Extracting video transcript...'):
                    # Fetching the transcript
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                    transcript = " ".join([t['text'] for t in transcript_list])
                
                with st.spinner('AI is generating your content...'):
                    # AI Prompt for Global Market
                    prompt = f"Based on this transcript: {transcript}, generate: 1. A professional Blog Post. 2. 5 Engaging Tweets. 3. A LinkedIn Summary. Everything must be in English."
                    response = model.generate_content(prompt)
                    st.success("Success!")
                    st.markdown(response.text)
        except Exception as e:
            st.error("Error: Make sure the video has Subtitles/CC enabled.")
else:
    st.warning("Please enter your API Key in the sidebar to begin.")
