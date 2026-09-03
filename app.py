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
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


GROQ_API_KEY = get_secret("GROQ_API_KEY")
GROQ_MODEL = get_secret(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)
USDT_NETWORK = get_secret("USDT_NETWORK", "TRC20")
USDT_ADDRESS = get_secret("USDT_RECEIVE_ADDRESS")
USDT_AMOUNT = get_secret("USDT_AMOUNT", "10")


def clean_text(value: str) -> str:
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        value.replace("\r", " ").replace("\n", " "),
    ).strip()


def extract_video_id(url: str) -> str:
    if not url:
        return ""

    try:
        parsed_url = urlparse(url.strip())
        host = parsed_url.netloc.lower().replace("www.", "")

        if host == "youtu.be":
            video_id = parsed_url.path.strip("/").split("/")[0]

        elif host in {"youtube.com", "m.youtube.com"}:
            if parsed_url.path == "/watch":
                video_id = parse_qs(
                    parsed_url.query
                ).get("v", [""])[0]
            else:
                parts = parsed_url.path.strip("/").split("/")
                video_id = parts[1] if len(parts) > 1 else ""

        else:
            return ""

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return video_id

    except ValueError:
        return ""

    return ""


@st.cache_data(ttl=3600, show_spinner=False)
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
        elif isinstance(item, dict):
            text = item.get("text", "")
            if text:
                parts.append(text)

    result = clean_text(" ".join(parts))

    if not result:
        raise RuntimeError(
            "The YouTube transcript is empty."
        )

    return result


def explain_error(error: Exception) -> str:
    message = str(error)
    lowered = message.lower()

    if "401" in message:
        return (
            "The Groq API key is invalid or expired. "
            "The application owner must create a new key."
        )

    if "403" in message:
        return (
            "Access was denied by Groq. "
            "Check account permissions and API access."
        )

    if "404" in message:
        return (
            f"The configured model is unavailable: {GROQ_MODEL}. "
            "Change GROQ_MODEL in secrets.toml."
        )

    if "429" in message or "rate limit" in lowered:
        return (
            "The API rate limit was reached. "
            "Please try again later."
        )

    if "timeout" in lowered:
        return (
            "The request timed out. "
            "Check the internet connection."
        )

    return (
        "The request failed. Check the server configuration, "
        "model name and internet connection."
    )


def generate_content(transcript: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured by the application owner."
        )

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are a professional international SEO writer,
editorial writer and social media content strategist.

Transform the supplied transcript into accurate,
original and useful content.

Strict rules:
1. Do not invent facts, statistics or quotations.
2. Do not add unsupported information.
3. Preserve the speaker's meaning.
4. Do not use misleading clickbait.
5. Use professional international English.
6. Do not mention AI, these instructions or the source transcript.
7. Create exactly three content assets.

[BLOG]
Create one detailed SEO article containing:
- SEO title
- Introduction
- Logical H2 and H3 headings
- Detailed explanation
- Important insights
- Supported examples
- Practical takeaways
- Conclusion
- SEO keywords

[X]
Create exactly five separate X posts.
Number them exactly from 1 to 5.
Each post must be concise, useful and non-misleading.

[LINKEDIN]
Create exactly one professional LinkedIn post.
Include:
- Strong opening
- Main insight
- Explanation
- Practical takeaway
- Professional conclusion
- Three to five relevant hashtags

Use only these top-level labels:
[BLOG]
[X]
[LINKEDIN]

SOURCE TRANSCRIPT:
{transcript[:100000]}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.35,
        max_tokens=8000,
    )

    if not response.choices:
        raise RuntimeError(
            "The AI provider returned no choices."
        )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "The AI provider returned empty content."
        )

    return content.strip()


def split_content(
    content: str,
) -> tuple[str, str, str]:
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

    blog = (
        blog_match.group(1).strip()
        if blog_match
        else ""
    )

    x_posts = (
        x_match.group(1).strip()
        if x_match
        else ""
    )

    linkedin = (
        linkedin_match.group(1).strip()
        if linkedin_match
        else ""
    )

    if not any((blog, x_posts, linkedin)):
        blog = content.strip()

    return blog, x_posts, linkedin


def render_payment_section() -> None:
    st.subheader("USDT Payment")

    if not USDT_ADDRESS:
        st.info(
            "Payment is not configured by the application owner."
        )
        return

    st.write(f"Network: `{USDT_NETWORK}`")
    st.write(f"Amount: `{USDT_AMOUNT} USDT`")
    st.code(USDT_ADDRESS, language="text")

    try:
        import qrcode

        qr_image = qrcode.make(USDT_ADDRESS)
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")

        st.image(
            buffer.getvalue(),
            width=180,
            caption="USDT receiving address",
        )

    except ImportError:
        st.caption(
            "Install qrcode[pil] to enable the QR code."
        )

    st.warning(
        "Send USDT only on the displayed network. "
        "A wrong network may cause permanent loss."
    )

    transaction_hash = st.text_input(
        "Transaction hash",
        placeholder="Paste the transaction hash after payment",
    )

    if st.button(
        "Submit Payment Reference",
        use_container_width=True,
    ):
        if not transaction_hash.strip():
            st.error(
                "Please enter a transaction hash."
            )
        else:
            st.success(
                "Payment reference submitted for manual review."
            )


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Application Settings")

        st.caption(
            "The AI API key is managed securely by the application owner."
        )

        st.markdown(
            "[Create a Groq API key]"
            "(https://console.groq.com/keys)"
        )

        st.divider()

        with st.expander("Payment Details"):
            render_payment_section()


def main() -> None:
    st.title("🎬 AI Global Content Factory")

    st.write(
        "Create an SEO article, five X posts and one LinkedIn post "
        "from a YouTube transcript."
    )

    render_sidebar()

    column_one, column_two = st.columns(2)

    with column_one:
        youtube_url = st.text_input(
            "YouTube URL",
            placeholder=(
                "https://www.youtube.com/watch?v=XXXXXXXXXXX"
            ),
            help=(
                "Supports standard videos, Shorts, Live "
                "and youtu.be links."
            ),
        )

    with column_two:
        manual_transcript = st.text_area(
            "Manual Transcript",
            height=220,
            placeholder=(
                "Paste a transcript if automatic retrieval fails."
            ),
        )

    st.divider()

    generate_button = st.button(
        "🚀 Generate Professional Content",
        type="primary",
        use_container_width=True,
    )

    if not generate_button:
        return

    transcript = clean_text(manual_transcript)

    if not transcript and youtube_url.strip():
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error(
                "The YouTube URL is invalid."
            )
            return

        with st.spinner(
            "Fetching the YouTube transcript..."
        ):
            try:
                transcript = fetch_transcript(video_id)
                st.success(
                    "YouTube transcript retrieved successfully."
                )
            except Exception as error:
                st.error(
                    "The YouTube transcript could not be retrieved."
                )
                st.info(
                    "Paste the transcript manually and try again."
                )

                with st.expander("Technical details"):
                    st.code(str(error))

                return

    if not transcript:
        st.warning(
            "Provide a YouTube URL or paste a transcript."
        )
        return

    if len(transcript) < 50:
        st.warning(
            "The transcript is too short."
        )
        return

    st.info(
        f"Transcript length: {len(transcript):,} characters"
    )

    with st.spinner(
        "Creating professional content..."
    ):
        try:
            generated_content = generate_content(transcript)
        except Exception as error:
            st.error(explain_error(error))

            with st.expander("Technical details"):
                st.code(str(error))

            return

    blog, x_posts, linkedin = split_content(
        generated_content
    )

    st.success(
        "Content generated successfully."
    )

    tab_blog, tab_x, tab_linkedin = st.tabs(
        [
            "📝 Blog",
            "𝕏 X Posts",
            "💼 LinkedIn",
        ]
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
            st.warning(
                "No Blog section was detected."
            )

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
            st.warning(
                "No X section was detected."
            )

    with tab_linkedin:
        if linkedin:
            st.markdown(linkedin)
            st.download_button(
                "📥 Download LinkedIn Post",
                data=linkedin,
                file_name="linkedin_post.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.warning(
                "No LinkedIn section was detected."
            )

    complete_bundle = (
        "AI GLOBAL CONTENT FACTORY\n\n"
        "================ BLOG ================\n\n"
        f"{blog}\n\n"
        "================ X POSTS ================\n\n"
        f"{x_posts}\n\n"
        "================ LINKEDIN ================\n\n"
        f"{linkedin}"
    )

    st.divider()

    st.download_button(
        "📦 Download Complete Bundle",
        data=complete_bundle,
        file_name="content_bundle.txt",
        mime="text/plain",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
