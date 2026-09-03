import os
import re
from urllib.parse import parse_qs, urlparse

import streamlit as st
from google import genai
from google.genai import errors


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


def extract_video_id(url: str) -> str:
    if not url:
        return ""

    try:
        parsed_url = urlparse(url.strip())
        host = parsed_url.netloc.lower().removeprefix("www.")

        if host == "youtu.be":
            video_id = parsed_url.path.strip("/").split("/")[0]

        elif host in {"youtube.com", "m.youtube.com"}:
            if parsed_url.path == "/watch":
                video_id = parse_qs(parsed_url.query).get("v", [""])[0]
            else:
                parts = parsed_url.path.strip("/").split("/")
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

    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def validate_api_key(api_key: str) -> tuple[bool, str]:
    api_key = api_key.strip()

    if not api_key:
        return False, "The API key field is empty."

    if len(api_key) < 20:
        return False, "The API key is too short."

    if any(character.isspace() for character in api_key):
        return False, "The API key contains spaces or line breaks."

    if api_key.lower() in {
        "your_api_key",
        "your-gemini-api-key",
        "paste-your-api-key-here",
    }:
        return False, "Replace the placeholder with a real API key."

    return True, ""


def test_gemini_connection(api_key: str) -> tuple[bool, str]:
    is_valid, validation_message = validate_api_key(api_key)

    if not is_valid:
        return False, validation_message

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: OK",
        )

        if response is None or not response.text:
            return False, "The API returned an empty response."

        return True, "The API key works correctly."

    except errors.ClientError as error:
        return False, explain_api_error(error)

    except errors.ServerError:
        return False, (
            "Google Gemini is temporarily unavailable. "
            "Try again later."
        )

    except Exception as error:
        return False, explain_api_error(error)


def explain_api_error(error: Exception) -> str:
    raw_message = str(error)
    message = raw_message.lower()

    status_code = getattr(error, "code", None)

    if status_code == 400 or "400" in message:
        return (
            "Google rejected the request. "
            "Check the model name, API configuration and request format."
        )

    if status_code == 401 or "401" in message:
        return (
            "The API key is invalid, expired or incorrectly copied. "
            "Create a new key in Google AI Studio."
        )

    if status_code == 403 or "403" in message:
        return (
            "Access was denied. Check that the Gemini API is enabled "
            "and that the selected Google project allows this API."
        )

    if status_code == 404 or "404" in message:
        return (
            "The selected Gemini model was not found or is unavailable "
            "for this account."
        )

    if status_code == 429 or "429" in message or "quota" in message:
        return (
            "The API quota or rate limit was reached. "
            "Wait and try again, or check billing and quota settings."
        )

    if "timeout" in message or "timed out" in message:
        return (
            "The request timed out. Check your internet connection, "
            "VPN and firewall."
        )

    if "api key" in message or "authentication" in message:
        return (
            "Authentication failed. Check that you copied the complete "
            "Gemini API key without quotes or spaces."
        )

    return (
        "The Gemini request failed. Check your internet connection, "
        "API access and Google AI Studio configuration."
    )


def fetch_youtube_transcript(video_id: str) -> str:
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


def generate_content(api_key: str, transcript: str) -> str:
    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a professional international content strategist, SEO writer,
editorial writer and social media content creator.

Transform the supplied transcript into original, useful content.

Rules:
1. Do not invent facts, statistics or quotations.
2. Do not make unsupported claims.
3. Preserve the meaning of the source.
4. Do not misrepresent the speaker.
5. Avoid misleading clickbait.
6. Use professional international English.
7. Do not mention that you are an AI.
8. Use only information supported by the transcript.
9. Create exactly three assets.

[BLOG]
Create one detailed SEO-friendly article with:
- SEO title
- Introduction
- Logical H2 and H3 headings
- Detailed explanation
- Important insights
- Supported practical examples
- Practical takeaways
- Conclusion
- SEO keywords

[X]
Create exactly five separate X posts.
Number them from 1 to 5.
Each post must be concise, useful and non-misleading.

[LINKEDIN]
Create exactly one professional LinkedIn post with:
- Strong opening
- Main insight
- Explanation
- Practical takeaway
- Professional conclusion
- Three to five relevant hashtags

Use only these labels:
[BLOG]
[X]
[LINKEDIN]

SOURCE TRANSCRIPT:
{transcript[:100000]}
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
        re.IGNORECASE | re.DOTALL,
    )
    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
        result,
        re.IGNORECASE | re.DOTALL,
    )
    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        result,
        re.IGNORECASE | re.DOTALL,
    )

    blog = blog_match.group(1).strip() if blog_match else ""
    x_posts = x_match.group(1).strip() if x_match else ""
    linkedin = linkedin_match.group(1).strip() if linkedin_match else ""

    if not blog and not x_posts and not linkedin:
        blog = result.strip()

    return blog, x_posts, linkedin


st.title("🎬 AI Global Content Factory")
st.subheader("Transform YouTube knowledge into professional content")

with st.sidebar:
    st.header("Settings")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Paste your API key here",
        help=(
            "Create your key at https://aistudio.google.com/apikey. "
            "Paste the complete key without quotes or spaces. "
            "Your key is used only for the current session."
        ),
    )

    check_key_button = st.button(
        "Check API Key",
        use_container_width=True,
    )

    if check_key_button:
        with st.spinner("Checking the Gemini API key..."):
            is_valid, message = test_gemini_connection(api_key)

        if is_valid:
            st.success(message)
        else:
            st.error(message)

            with st.expander("What should be checked?"):
                st.markdown(
                    """
1. Create a new key in Google AI Studio.
2. Copy the entire key.
3. Remove quotes and spaces.
4. Confirm that the Gemini API is enabled.
5. Check quota, billing and network access.
                    """
                )

    st.divider()

    st.markdown(
        "[Create a Gemini API key]"
        "(https://aistudio.google.com/apikey)"
    )

col1, col2 = st.columns(2)

with col1:
    st.subheader("YouTube URL")

    youtube_url = st.text_input(
        "Paste YouTube URL",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
    )

with col2:
    st.subheader("Manual Transcript")

    manual_transcript = st.text_area(
        "Paste transcript",
        placeholder="Paste the transcript here if automatic retrieval fails.",
        height=220,
    )

st.divider()

generate_button = st.button(
    "🚀 Generate Professional Content",
    type="primary",
    use_container_width=True,
)

if generate_button:
    is_valid, validation_message = validate_api_key(api_key)

    if not is_valid:
        st.error(validation_message)
        st.info(
            "Use the question-mark help icon beside the API key field "
            "for instructions."
        )
        st.stop()

    transcript = clean_text(manual_transcript)

    if not transcript and youtube_url.strip():
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error("The YouTube URL is invalid.")
            st.stop()

        with st.spinner("Fetching the YouTube transcript..."):
            try:
                transcript = fetch_youtube_transcript(video_id)
            except Exception as error:
                st.error("The transcript could not be retrieved.")
                st.info(
                    "Paste the transcript manually and try again."
                )
                st.code(str(error))
                st.stop()

    if not transcript:
        st.warning("Provide a YouTube URL or paste a transcript.")
        st.stop()

    if len(transcript) < 50:
        st.warning("The transcript is too short.")
        st.stop()

    with st.spinner("Gemini is creating your content..."):
        try:
            generated_result = generate_content(api_key.strip(), transcript)
        except Exception as error:
            st.error("Gemini could not generate the content.")
            st.warning(explain_api_error(error))
            st.stop()

    blog, x_posts, linkedin = split_content(generated_result)

    st.success("Content generated successfully.")

    tab_blog, tab_x, tab_linkedin = st.tabs(
        ["Blog", "X Posts", "LinkedIn"]
    )

    with tab_blog:
        st.markdown(blog or "No Blog section was detected.")
        if blog:
            st.download_button(
                "Download Blog",
                blog,
                "blog_post.md",
                "text/markdown",
                use_container_width=True,
            )

    with tab_x:
        st.markdown(x_posts or "No X section was detected.")
        if x_posts:
            st.download_button(
                "Download X Posts",
                x_posts,
                "x_posts.txt",
                "text/plain",
                use_container_width=True,
            )

    with tab_linkedin:
        st.markdown(linkedin or "No LinkedIn section was detected.")
        if linkedin:
            st.download_button(
                "Download LinkedIn Post",
                linkedin,
                "linkedin_post.md",
                "text/markdown",
                use_container_width=True,
            )
