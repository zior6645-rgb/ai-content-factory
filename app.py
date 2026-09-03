import os
import re
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import streamlit as st
from groq import Groq


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


GROQ_API_KEY = get_secret("GROQ_API_KEY")
GROQ_MODEL = get_secret("GROQ_MODEL", "llama-3.3-70b-versatile")
USDT_NETWORK = get_secret("USDT_NETWORK", "TRC20")
USDT_ADDRESS = get_secret("USDT_RECEIVE_ADDRESS")
USDT_AMOUNT = get_secret("USDT_AMOUNT", "10")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def extract_video_id(url: str) -> str:
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())
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

        return video_id if re.fullmatch(
            r"[A-Za-z0-9_-]{11}", video_id
        ) else ""

    except ValueError:
        return ""


def fetch_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    transcript = YouTubeTranscriptApi().fetch(
        video_id,
        languages=["en", "fa"],
    )

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


def generate_content(transcript: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured by the application owner."
        )

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are an international SEO writer and content strategist.

Transform the transcript into accurate, useful and original content.

Strict rules:
- Do not invent facts, statistics or quotations.
- Do not add information that is not supported by the transcript.
- Preserve the speaker's meaning.
- Do not use misleading clickbait.
- Write in professional international English.
- Do not mention AI, the transcript or these instructions.
- Create exactly three assets.

[BLOG]
Create one detailed SEO article containing:
SEO Title
Introduction
H2 and H3 headings
Detailed explanation
Important insights
Supported examples
Practical takeaways
Conclusion
SEO keywords

[X]
Create exactly five concise X posts.
Number them 1 through 5.
Each post must contain one useful idea and a strong hook.

[LINKEDIN]
Create exactly one professional LinkedIn post.
Include a strong opening, main insight, explanation,
practical takeaway, conclusion and 3 to 5 hashtags.

Use only these labels:
[BLOG]
[X]
[LINKEDIN]

SOURCE TRANSCRIPT:
{transcript[:100000]}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_tokens=8000,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("The AI provider returned empty content.")

    return content.strip()


def split_content(content: str) -> tuple[str, str, str]:
    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\]|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        content,
        re.IGNORECASE | re.DOTALL,
    )

    blog = blog_match.group(1).strip() if blog_match else ""
    x_posts = x_match.group(1).strip() if x_match else ""
    linkedin = linkedin_match.group(1).strip() if linkedin_match else ""

    if not any((blog, x_posts, linkedin)):
        blog = content.strip()

    return blog, x_posts, linkedin


def explain_error(error: Exception) -> str:
    message = str(error).lower()

    if "401" in message:
        return "The Groq API key is invalid or expired."

    if "403" in message:
        return "The Groq account does not have permission to use this API."

    if "404" in message:
        return f"The configured model is unavailable: {GROQ_MODEL}"

    if "429" in message or "rate limit" in message:
        return "The Groq rate limit or quota has been reached."

    if "timeout" in message:
        return "The request timed out. Check the internet connection."

    return "The request failed. Check the API key, model and network connection."


def render_payment_section() -> None:
    st.subheader("USDT Payment")

    if not USDT_ADDRESS:
        st.info("Payments are not configured by the application owner.")
        return

    st.write(f"Network: `{USDT_NETWORK}`")
    st.write(f"Amount: `{USDT_AMOUNT} USDT`")
    st.code(USDT_ADDRESS, language="text")

    try:
        import qrcode

        image = qrcode.make(USDT_ADDRESS)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        st.image(buffer.getvalue(), width=180)
    except ImportError:
        st.caption("QR code support is unavailable.")

    st.warning(
        "Send USDT only on the displayed network. "
        "A wrong network may cause permanent loss."
    )


st.title("🎬 AI Global Content Factory")
st.write(
    "Create an SEO article, five X posts and one LinkedIn post "
    "from a YouTube transcript."
)

with st.sidebar:
    st.header("Application Settings")
    st.caption("The AI API key is managed securely by the application owner.")

    with st.expander("Payment Details"):
        render_payment_section()

col1, col2 = st.columns(2)

with col1:
    youtube_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
        help="Supports videos, Shorts, Live and youtu.be links.",
    )

with col2:
    manual_transcript = st.text_area(
        "Manual Transcript",
        height=220,
        placeholder="Paste a transcript if automatic retrieval fails.",
    )

st.divider()

if st.button(
    "🚀 Generate Professional Content",
    type="primary",
    use_container_width=True,
):
    transcript = clean_text(manual_transcript)

    if not transcript and youtube_url.strip():
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error("The YouTube URL is invalid.")
            st.stop()

        with st.spinner("Fetching the YouTube transcript..."):
            try:
                transcript = fetch_transcript(video_id)
            except Exception as error:
                st.error("The transcript could not be retrieved.")
                st.info("Paste the transcript manually and try again.")
                st.code(str(error))
                st.stop()

    if not transcript:
        st.warning("Provide a YouTube URL or paste a transcript.")
        st.stop()

    if len(transcript) < 50:
        st.warning("The transcript is too short.")
        st.stop()

    with st.spinner("Creating professional content..."):
        try:
            result = generate_content(transcript)
        except Exception as error:
            st.error(explain_error(error))
            with st.expander("Technical details"):
                st.code(str(error))
            st.stop()

    blog, x_posts, linkedin = split_content(result)

    st.success("Content generated successfully.")

    tab_blog, tab_x, tab_linkedin = st.tabs(
        ["📝 Blog", "𝕏 X Posts", "💼 LinkedIn"]
    )

    with tab_blog:
        if blog:
            st.markdown(blog)
            st.download_button(
                "Download Blog",
                blog,
                "blog_post.md",
                "text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("No Blog section was detected.")

    with tab_x:
        if x_posts:
            st.markdown(x_posts)
            st.download_button(
                "Download X Posts",
                x_posts,
                "x_posts.txt",
                "text/plain",
                use_container_width=True,
            )
        else:
            st.warning("No X section was detected.")

    with tab_linkedin:
        if linkedin:
            st.markdown(linkedin)
            st.download_button(
                "Download LinkedIn Post",
                linkedin,
                "linkedin_post.md",
                "text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("No LinkedIn section was detected.")

    complete_bundle = (
        f"BLOG\n\n{blog}\n\n"
        f"X POSTS\n\n{x_posts}\n\n"
        f"LINKEDIN\n\n{linkedin}"
    )

    st.download_button(
        "📦 Download Complete Bundle",
        complete_bundle,
        "content_bundle.txt",
        "text/plain",
        use_container_width=True,
    )
