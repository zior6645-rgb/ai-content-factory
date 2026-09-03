import re
from urllib.parse import parse_qs, urlparse

import streamlit as st
from google import genai


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


def extract_video_id(url: str) -> str:
    if not url:
        return ""

    url = url.strip()

    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")

        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        elif host in {"youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            else:
                parts = parsed.path.strip("/").split("/")
                video_id = parts[1] if len(parts) >= 2 else ""
        else:
            return ""

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return video_id

    except ValueError:
        return ""

    return ""


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def fetch_youtube_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=["en", "fa"])

    parts = []

    for item in transcript:
        if hasattr(item, "text"):
            parts.append(item.text)
        elif isinstance(item, dict) and item.get("text"):
            parts.append(item["text"])

    result = clean_text(" ".join(parts))

    if not result:
        raise RuntimeError("The YouTube transcript is empty.")

    return result


def generate_ai_content(api_key: str, transcript: str) -> str:
    client = genai.Client(api_key=api_key)

    transcript = transcript[:100000]

    prompt = f"""
You are a professional international content strategist, SEO writer,
editorial writer and social media content creator.

Transform the supplied YouTube transcript into high-quality original content.

Rules:
1. Do not invent facts, statistics or quotations.
2. Do not make unsupported claims.
3. Preserve the meaning of the source.
4. Do not misrepresent the speaker.
5. Avoid misleading clickbait.
6. Write professional international English.
7. Do not mention that you are an AI.
8. Use only information supported by the transcript.
9. Create exactly three assets.

[BLOG]
Create a detailed SEO-friendly article with:
- SEO title
- Introduction
- Logical H2 and H3 headings
- Detailed explanation
- Important insights
- Practical examples only when supported
- Practical takeaways
- Conclusion
- SEO keywords

[X]
Create exactly five separate X/Twitter posts.
Number them from 1 to 5.
Each post must:
- Have a strong hook
- Communicate one useful idea
- Be concise and easy to read
- Use emojis naturally
- Avoid misleading claims
- Avoid excessive hashtags

[LINKEDIN]
Create exactly one professional LinkedIn post with:
- Strong opening
- Main insight
- Explanation
- Practical takeaway
- Professional conclusion
- Three to five relevant hashtags

Use exactly these three labels and do not create additional top-level labels:
[BLOG]
[X]
[LINKEDIN]

SOURCE TRANSCRIPT:
{transcript}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    if response is None or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text.strip()


def split_content(result: str) -> tuple[str, str, str]:
    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\]|\Z)",
        result,
        flags=re.IGNORECASE | re.DOTALL,
    )

    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
        result,
        flags=re.IGNORECASE | re.DOTALL,
    )

    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        result,
        flags=re.IGNORECASE | re.DOTALL,
    )

    blog = blog_match.group(1).strip() if blog_match else ""
    x_posts = x_match.group(1).strip() if x_match else ""
    linkedin = linkedin_match.group(1).strip() if linkedin_match else ""

    if not blog and not x_posts and not linkedin:
        blog = result.strip()

    return blog, x_posts, linkedin


def show_api_error(error: Exception) -> None:
    error_message = str(error)
    lower_error = error_message.lower()

    st.error("Gemini could not generate the content.")

    if "401" in error_message:
        st.warning("The Gemini API key may be invalid.")
    elif "403" in error_message:
        st.warning("Google rejected the request. Check API access.")
    elif "429" in error_message or "quota" in lower_error:
        st.warning("The API rate limit or quota may have been reached.")
    else:
        st.warning("An unexpected error occurred.")

    with st.expander("Technical details"):
        st.code(error_message)


st.title("🎬 AI Global Content Factory")
st.subheader("Transform YouTube knowledge into professional content")

st.write(
    "Create SEO articles, X/Twitter posts and LinkedIn content "
    "from a YouTube transcript."
)

with st.sidebar:
    st.header("⚙️ Settings")
    st.subheader("🔑 Gemini API")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Paste your API key",
    )

    st.caption("Your API key is used only for the current session.")
    st.markdown(
        "[Get a Gemini API key from Google AI Studio]"
        "(https://aistudio.google.com/apikey)"
    )

    st.divider()
    st.subheader("💎 Premium")
    st.info(
        "Premium features can be added later, including advanced "
        "content formats, higher limits and additional tools."
    )

    st.divider()
    st.caption("AI Global Content Factory")
    st.caption("Powered by Streamlit + Gemini")


col1, col2 = st.columns(2)

with col1:
    st.subheader("🔗 YouTube URL")

    youtube_url = st.text_input(
        "Paste YouTube URL",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
    )

    st.caption(
        "Supports videos, Shorts, Live and youtu.be links."
    )

with col2:
    st.subheader("📝 Manual Transcript")

    manual_transcript = st.text_area(
        "Paste transcript",
        placeholder=(
            "If automatic retrieval fails, paste the transcript here."
        ),
        height=220,
    )

st.divider()

generate_button = st.button(
    "🚀 Generate Professional Content",
    type="primary",
    use_container_width=True,
)

if generate_button:
    key = api_key.strip()

    if not key:
        st.error("Please enter your Gemini API key in the sidebar.")
        st.stop()

    transcript = clean_text(manual_transcript)

    if not transcript and youtube_url.strip():
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error("The YouTube URL is not valid.")
            st.stop()

        with st.spinner("🔎 Fetching YouTube transcript..."):
            try:
                transcript = fetch_youtube_transcript(video_id)
                st.success("YouTube transcript retrieved successfully.")
            except Exception as error:
                st.error("Automatic transcript retrieval failed.")
                st.info(
                    "Copy the transcript from YouTube and paste it "
                    "into the Manual Transcript box."
                )

                with st.expander("Technical details"):
                    st.code(str(error))

                st.stop()

    if not transcript:
        st.warning("Please provide a YouTube URL or paste a transcript.")
        st.stop()

    if len(transcript) < 50:
        st.warning(
            "The transcript is too short. Please provide more content."
        )
        st.stop()

    st.info(
        f"Transcript length: {len(transcript):,} characters"
    )

    with st.spinner("🤖 Gemini is creating your content..."):
        try:
            result = generate_ai_content(key, transcript)
        except Exception as error:
            show_api_error(error)
            st.stop()

    blog, x_posts, linkedin = split_content(result)

    st.success("🎉 Content generated successfully!")

    tab_blog, tab_x, tab_linkedin = st.tabs(
        ["📝 Blog", "𝕏 X / Twitter", "💼 LinkedIn"]
    )

    with tab_blog:
        if blog:
            st.markdown(blog)
            st.download_button(
                "📥 Download Blog",
                data=blog,
                file_name="blog_post.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("No Blog section was detected.")

    with tab_x:
        if x_posts:
            st.markdown(x_posts)
            st.download_button(
                "📥 Download X Posts",
                data=x_posts,
                file_name="x_posts.txt",
                mime="text/plain",
                use_container_width=True,
            )
        else:
            st.warning("No X/Twitter section was detected.")

    with tab_linkedin:
        if linkedin:
            st.markdown(linkedin)
            st.download_button(
                "📥 Download LinkedIn",
                data=linkedin,
                file_name="linkedin_post.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("No LinkedIn section was detected.")

    complete_bundle = (
        "AI GLOBAL CONTENT FACTORY\n\n"
        "========================================\n"
        "BLOG\n"
        "========================================\n\n"
        f"{blog}\n\n"
        "========================================\n"
        "X / TWITTER\n"
        "========================================\n\n"
        f"{x_posts}\n\n"
        "========================================\n"
        "LINKEDIN\n"
        "========================================\n\n"
        f"{linkedin}"
    )

    st.divider()

    st.download_button(
        "📦 Download Complete Content Bundle",
        data=complete_bundle,
        file_name="ai_global_content_factory_bundle.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.divider()
st.caption("AI Global Content Factory • Streamlit + Gemini")
