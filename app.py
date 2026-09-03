```python
import re
import streamlit as st
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


# =========================================================
# FUNCTIONS
# =========================================================

def extract_video_id(url: str):
    """Extract the 11-character YouTube video ID."""

    if not url:
        return None

    url = url.strip()

    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


def clean_text(text: str):
    """Clean transcript text."""

    if not text:
        return ""

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def fetch_transcript(video_id: str):
    """Fetch YouTube transcript."""

    api = YouTubeTranscriptApi()

    # Try English first, then Persian.
    transcript = api.fetch(
        video_id,
        languages=["en", "fa"],
    )

    result = []

    for item in transcript:
        if hasattr(item, "text"):
            result.append(item.text)

    text = clean_text(" ".join(result))

    if not text:
        raise Exception("The transcript is empty.")

    return text


def generate_with_gemini(api_key: str, transcript: str):
    """Generate content using Gemini."""

    client = genai.Client(
        api_key=api_key
    )

    # Keep request size reasonable.
    transcript = transcript[:100000]

    prompt = f"""
You are a professional international content strategist,
SEO writer and social media content creator.

Analyze the following YouTube transcript.

IMPORTANT RULES:
- Do not invent facts.
- Do not make unsupported claims.
- Preserve the meaning of the original transcript.
- Write in professional international English.
- Make the content useful and original.
- Avoid misleading clickbait.

========================
YOUTUBE TRANSCRIPT
========================

{transcript}

========================
TASK
========================

Create THREE separate content assets.

1. BLOG

Create an SEO-friendly article containing:

- Title
- Introduction
- H2/H3 headings
- Detailed useful content
- Practical takeaways
- Conclusion
- SEO keywords

2. X / TWITTER

Create exactly 5 separate posts.

Each post must:
- Have a strong hook
- Provide useful information
- Be concise
- Use emojis naturally
- Avoid misleading claims

3. LINKEDIN

Create one professional LinkedIn post containing:

- Strong opening
- Main insight
- Explanation
- Practical takeaway
- Professional ending
- 3 to 5 relevant hashtags

========================
OUTPUT FORMAT
========================

[BLOG]

Write the complete blog here.

[X]

1. Post one
2. Post two
3. Post three
4. Post four
5. Post five

[LINKEDIN]

Write the complete LinkedIn post here.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=10000,
        ),
    )

    if not response:
        raise Exception("Gemini returned no response.")

    if not response.text:
        raise Exception("Gemini returned empty text.")

    return response.text


def split_result(text: str):
    """Split Gemini result."""

    blog = ""
    x_posts = ""
    linkedin = ""

    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if blog_match:
        blog = blog_match.group(1).strip()

    if x_match:
        x_posts = x_match.group(1).strip()

    if linkedin_match:
        linkedin = linkedin_match.group(1).strip()

    # Fallback
    if not blog and not x_posts and not linkedin:
        blog = text.strip()

    return blog, x_posts, linkedin


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("⚙️ Settings")

    st.subheader("🔑 Gemini API Key")

    api_key = st.text_input(
        "Enter your API key",
        type="password",
        placeholder="Paste Gemini API key",
    ).strip()

    st.markdown(
        "[Get your Gemini API key from Google AI Studio](https://aistudio.google.com/)"
    )

    st.divider()

    st.subheader("💎 Premium")

    st.info(
        "Premium features can be added later, "
        "including higher limits and additional content tools."
    )

    st.divider()

    st.caption("AI Global Content Factory")
    st.caption("Version 3.0")


# =========================================================
# MAIN PAGE
# =========================================================

st.title("🎬 AI Global Content Factory")

st.write(
    "Transform YouTube content into professional "
    "Blog, X/Twitter and LinkedIn content."
)


# =========================================================
# INPUTS
# =========================================================

col1, col2 = st.columns(2)

with col1:

    st.subheader("🔗 YouTube URL")

    youtube_url = st.text_input(
        "Paste YouTube URL",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
    )

    st.caption(
        "Use a YouTube video, Shorts, live video or youtu.be link."
    )


with col2:

    st.subheader("📝 Manual Transcript")

    manual_transcript = st.text_area(
        "Paste transcript",
        placeholder=(
            "If YouTube transcript retrieval fails, "
            "paste the transcript here."
        ),
        height=180,
    )


# =========================================================
# BUTTON
# =========================================================

st.divider()

generate_button = st.button(
    "🚀 Generate Content",
    type="primary",
    use_container_width=True,
)


# =========================================================
# PROCESS
# =========================================================

if generate_button:

    # -----------------------------------------------------
    # API KEY CHECK
    # -----------------------------------------------------

    if not api_key:

        st.error(
            "❌ Please enter your Gemini API key in the sidebar."
        )

        st.stop()


    # -----------------------------------------------------
    # GET TRANSCRIPT
    # -----------------------------------------------------

    transcript = ""

    # Manual transcript has priority.
    if manual_transcript.strip():

        transcript = clean_text(
            manual_transcript
        )

        st.success(
            f"Manual transcript loaded: "
            f"{len(transcript):,} characters."
        )

    # Automatic YouTube transcript.
    elif youtube_url.strip():

        video_id = extract_video_id(
            youtube_url
        )

        if not video_id:

            st.error(
                "❌ The YouTube URL is not valid."
            )

            st.stop()

        with st.spinner(
            "🔎 Fetching YouTube transcript..."
        ):

            try:

                transcript = fetch_transcript(
                    video_id
                )

                st.success(
                    f"Transcript retrieved successfully: "
                    f"{len(transcript):,} characters."
                )

            except Exception as error:

                st.error(
                    "⚠️ YouTube transcript could not be retrieved."
                )

                st.info(
                    "Copy the transcript from YouTube "
                    "and paste it into the Manual Transcript box."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.code(
                        str(error)
                    )

                st.stop()

    else:

        st.warning(
            "Please provide a YouTube URL "
            "or paste a transcript."
        )

        st.stop()


    # -----------------------------------------------------
    # TRANSCRIPT VALIDATION
    # -----------------------------------------------------

    if len(transcript) < 50:

        st.warning(
            "The transcript is too short. "
            "Please provide more content."
        )

        st.stop()


    # -----------------------------------------------------
    # GEMINI GENERATION
    # -----------------------------------------------------

    with st.spinner(
        "🤖 Gemini is generating your content..."
    ):

        try:

            result = generate_with_gemini(
                api_key,
                transcript
            )

        except Exception as error:

            error_text = str(error)

            st.error(
                "❌ Gemini could not generate the content."
            )

            if "401" in error_text or "API key" in error_text.lower():

                st.warning(
                    "Your API key may be invalid. "
                    "Check the key in the sidebar."
                )

            elif "403" in error_text:

                st.warning(
                    "The API request was rejected. "
                    "Check your API key and Google AI Studio access."
                )

            elif "429" in error_text:

                st.warning(
                    "The API rate limit was reached. "
                    "Wait a little and try again."
                )

            else:

                st.warning(
                    "Please check the technical details below."
                )

            with st.expander(
                "Technical details"
            ):

                st.code(
                    error_text
                )

            st.stop()


    # -----------------------------------------------------
    # SPLIT CONTENT
    # -----------------------------------------------------

    blog, x_posts, linkedin = split_result(
        result
    )


    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    st.success(
        "🎉 Content generated successfully!"
    )

    tab_blog, tab_x, tab_linkedin = st.tabs(
        [
            "📝 Blog",
            "𝕏 X / Twitter",
            "💼 LinkedIn",
        ]
    )


    # -----------------------------------------------------
    # BLOG
    # -----------------------------------------------------

    with tab_blog:

        if blog:

            st.markdown(blog)

            st.download_button(
                "📥 Download Blog",
                blog,
                "blog_post.md",
                "text/markdown",
                use_container_width=True,
            )

        else:

            st.warning(
                "Blog content was not detected."
            )


    # -----------------------------------------------------
    # X POSTS
    # -----------------------------------------------------

    with tab_x:

        if x_posts:

            st.markdown(x_posts)

            st.download_button(
                "📥 Download X Posts",
                x_posts,
                "x_posts.txt",
                "text/plain",
                use_container_width=True,
            )

        else:

            st.warning(
                "X posts were not detected."
            )


    # -----------------------------------------------------
    # LINKEDIN
    # -----------------------------------------------------

    with tab_linkedin:

        if linkedin:

            st.markdown(linkedin)

            st.download_button(
                "📥 Download LinkedIn",
                linkedin,
                "linkedin_post.md",
                "text/markdown",
                use_container_width=True,
            )

        else:

            st.warning(
                "LinkedIn content was not detected."
            )


    # -----------------------------------------------------
    # COMPLETE FILE
    # -----------------------------------------------------

    complete_content = f"""
AI GLOBAL CONTENT FACTORY
=========================

BLOG
====

{blog}


X / TWITTER
===========

{x_posts}


LINKEDIN
========

{linkedin}
"""

    st.divider()

    st.download_button(
        "📦 Download Complete Bundle",
        complete_content,
        "content_bundle.txt",
        "text/plain",
        use_container_width=True,
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AI Global Content Factory • Powered by Streamlit + Gemini"
)
```
