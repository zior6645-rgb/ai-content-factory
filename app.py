```python
import re
import streamlit as st
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide"
)


# =========================================================
# FUNCTIONS
# =========================================================

def get_video_id(url):
    """Extract YouTube video ID."""

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


def clean_text(text):
    """Clean unnecessary spaces."""

    if not text:
        return ""

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_transcript(video_id):
    """Get YouTube transcript."""

    api = YouTubeTranscriptApi()

    # Try English and Persian.
    languages = ["en", "fa"]

    transcript = api.fetch(
        video_id,
        languages=languages
    )

    texts = []

    for item in transcript:
        if hasattr(item, "text"):
            texts.append(item.text)
        else:
            try:
                texts.append(item["text"])
            except Exception:
                pass

    result = clean_text(" ".join(texts))

    if not result:
        raise Exception("Transcript is empty.")

    return result


def generate_content(api_key, transcript, model_name):
    """Generate content with Gemini."""

    client = genai.Client(
        api_key=api_key
    )

    # Prevent extremely large requests.
    transcript = transcript[:100000]

    prompt = f"""
You are an expert international content strategist,
SEO writer, social media writer and professional editor.

Analyze the YouTube transcript below.

Do NOT invent facts.
Do NOT create unsupported claims.
Keep the meaning of the original content.
Write in professional international English.

TRANSCRIPT
========================

{transcript}

========================

Create THREE separate outputs.

OUTPUT 1 — BLOG

Create a professional SEO-friendly blog article.

Include:

- SEO title
- Introduction
- H2/H3 headings
- Detailed useful content
- Practical takeaways
- Conclusion
- SEO keywords

OUTPUT 2 — X POSTS

Create exactly 5 independent X/Twitter posts.

Each post should:
- Have a strong hook
- Provide useful information
- Be concise
- Use emojis naturally
- Avoid fake claims
- Avoid deceptive clickbait

OUTPUT 3 — LINKEDIN

Create one professional LinkedIn post.

Include:
- Strong opening
- Main insight
- Explanation
- Practical takeaway
- Professional ending
- A few relevant hashtags

IMPORTANT:

Return ONLY this structure:

[BLOG]
blog content

[X]
1. post
2. post
3. post
4. post
5. post

[LINKEDIN]
LinkedIn content
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    if not response:
        raise Exception("Gemini returned no response.")

    if not response.text:
        raise Exception("Gemini returned empty text.")

    return response.text


def split_content(text):
    """Split Gemini response into three sections."""

    blog = ""
    x_posts = ""
    linkedin = ""

    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\]|\Z)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        text,
        re.DOTALL | re.IGNORECASE
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

    st.title("⚙️ Settings")

    st.markdown("### 🔑 Gemini API Key")

    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="Paste your Gemini API key here"
    )

    api_key = api_key.strip()

    st.markdown(
        "Get your API key from "
        "[Google AI Studio](https://aistudio.google.com/)"
    )

    st.divider()

    st.markdown("### 🤖 Gemini Model")

    model_name = st.text_input(
        "Model name",
        value="gemini-3.7-flash",
        help="Enter a Gemini model available to your API key."
    )

    model_name = model_name.strip()

    st.divider()

    st.markdown("### 💎 Premium")

    st.info(
        "Premium features can be added later, "
        "including higher limits, more content formats "
        "and additional AI models."
    )

    st.divider()

    st.caption("AI Global Content Factory")
    st.caption("Version 2.1")


# =========================================================
# HEADER
# =========================================================

st.title("🎬 AI Global Content Factory")

st.subheader(
    "Turn YouTube knowledge into professional content with AI."
)

st.write(
    "Generate SEO blog posts, X/Twitter posts and LinkedIn content "
    "from a YouTube transcript."
)


# =========================================================
# INPUT
# =========================================================

col1, col2 = st.columns(2)

with col1:

    st.markdown("### 🔗 YouTube URL")

    youtube_url = st.text_input(
        "YouTube video",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX"
    )

    st.caption(
        "You can use a normal YouTube URL, Shorts, live URL or youtu.be."
    )


with col2:

    st.markdown("### 📝 Manual Transcript")

    manual_text = st.text_area(
        "Transcript",
        placeholder=(
            "Paste the YouTube transcript here if automatic "
            "transcript retrieval does not work."
        ),
        height=160
    )


# =========================================================
# GENERATE
# =========================================================

st.divider()

generate = st.button(
    "🚀 Generate Content",
    type="primary",
    use_container_width=True
)


if generate:

    # -----------------------------------------------------
    # API KEY
    # -----------------------------------------------------

    if not api_key:

        st.error(
            "❌ Please enter your Gemini API key in the sidebar."
        )

        st.stop()


    # -----------------------------------------------------
    # MODEL
    # -----------------------------------------------------

    if not model_name:

        st.error(
            "❌ Please enter a Gemini model name."
        )

        st.stop()


    # -----------------------------------------------------
    # TRANSCRIPT
    # -----------------------------------------------------

    transcript = ""

    # Manual transcript has priority.
    if manual_text.strip():

        transcript = clean_text(manual_text)

        st.success(
            f"Manual transcript loaded: {len(transcript):,} characters."
        )

    elif youtube_url.strip():

        video_id = get_video_id(youtube_url)

        if not video_id:

            st.error(
                "❌ Invalid YouTube URL."
            )

            st.stop()

        with st.spinner(
            "🔎 Getting YouTube transcript..."
        ):

            try:

                transcript = get_transcript(video_id)

                st.success(
                    f"Transcript found: {len(transcript):,} characters."
                )

            except Exception as error:

                st.error(
                    "⚠️ Automatic transcript retrieval failed."
                )

                st.info(
                    "Please copy the transcript from YouTube "
                    "and paste it into the Manual Transcript box."
                )

                with st.expander("Technical error"):

                    st.code(
                        str(error)
                    )

                st.stop()

    else:

        st.warning(
            "Please enter a YouTube URL or paste a transcript."
        )

        st.stop()


    # -----------------------------------------------------
    # CHECK TRANSCRIPT
    # -----------------------------------------------------

    if len(transcript) < 50:

        st.warning(
            "The transcript is too short."
        )

        st.stop()


    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    with st.spinner(
        "🤖 Gemini is generating your content..."
    ):

        try:

            result = generate_content(
                api_key=api_key,
                transcript=transcript,
                model_name=model_name
            )

        except Exception as error:

            error_message = str(error)

            st.error(
                "❌ Gemini could not generate the content."
            )

            st.warning(
                "Check your API key and model name."
            )

            with st.expander("Technical error"):

                st.code(error_message)

            st.stop()


    # -----------------------------------------------------
    # SPLIT
    # -----------------------------------------------------

    blog, x_posts, linkedin = split_content(result)


    # -----------------------------------------------------
    # RESULTS
    # -----------------------------------------------------

    st.success(
        "🎉 Content generated successfully!"
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "📝 Blog",
            "𝕏 X / Twitter",
            "💼 LinkedIn"
        ]
    )


    # -----------------------------------------------------
    # BLOG
    # -----------------------------------------------------

    with tab1:

        if blog:

            st.markdown(blog)

            st.download_button(
                "📥 Download Blog",
                data=blog,
                file_name="blog_post.md",
                mime="text/markdown",
                use_container_width=True
            )

        else:

            st.warning(
                "Blog output was not detected."
            )


    # -----------------------------------------------------
    # X
    # -----------------------------------------------------

    with tab2:

        if x_posts:

            st.markdown(x_posts)

            st.download_button(
                "📥 Download X Posts",
                data=x_posts,
                file_name="x_posts.txt",
                mime="text/plain",
                use_container_width=True
            )

        else:

            st.warning(
                "X/Twitter output was not detected."
            )


    # -----------------------------------------------------
    # LINKEDIN
    # -----------------------------------------------------

    with tab3:

        if linkedin:

            st.markdown(linkedin)

            st.download_button(
                "📥 Download LinkedIn",
                data=linkedin,
                file_name="linkedin_post.md",
                mime="text/markdown",
                use_container_width=True
            )

        else:

            st.warning(
                "LinkedIn output was not detected."
            )


    # -----------------------------------------------------
    # COMPLETE DOWNLOAD
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
        "📦 Download Complete Content Bundle",
        data=complete_content,
        file_name="content_bundle.txt",
        mime="text/plain",
        use_container_width=True
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AI Global Content Factory • Built with Streamlit and Gemini"
)
```
