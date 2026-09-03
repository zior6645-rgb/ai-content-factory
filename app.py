```python
import re
import streamlit as st
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1.15rem;
            opacity: 0.75;
            margin-bottom: 2rem;
        }

        .feature-box {
            padding: 1.2rem;
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,0.25);
            margin-bottom: 1rem;
        }

        .small-text {
            font-size: 0.85rem;
            opacity: 0.7;
        }

        .success-box {
            padding: 1rem;
            border-radius: 10px;
            border: 1px solid rgba(0, 200, 100, 0.35);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_youtube_video_id(url: str):
    """
    Extract a YouTube video ID from common YouTube URL formats.
    """

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

    # Fallback: look for an 11-character YouTube ID
    fallback = re.search(r"\b[A-Za-z0-9_-]{11}\b", url)

    if fallback:
        return fallback.group(0)

    return None


def clean_transcript(text: str) -> str:
    """
    Clean and normalize transcript text.
    """

    if not text:
        return ""

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def fetch_youtube_transcript(video_id: str):
    """
    Fetch a YouTube transcript using the current youtube-transcript-api API.
    """

    api = YouTubeTranscriptApi()

    # Try English first, then Persian, then common alternatives.
    language_sets = [
        ["en"],
        ["fa"],
        ["en", "fa"],
        ["en", "fa", "de", "es", "fr"],
    ]

    last_error = None

    for languages in language_sets:

        try:
            transcript = api.fetch(
                video_id,
                languages=languages,
            )

            parts = []

            for snippet in transcript:
                if hasattr(snippet, "text"):
                    parts.append(snippet.text)
                elif isinstance(snippet, dict):
                    parts.append(snippet.get("text", ""))

            result = clean_transcript(" ".join(parts))

            if result:
                return result

        except Exception as error:
            last_error = error

    raise RuntimeError(
        f"Could not retrieve the YouTube transcript. "
        f"Please use the manual transcript option. Details: {last_error}"
    )


def generate_content_bundle(api_key: str, transcript: str, model_name: str):
    """
    Generate Blog, X/Twitter posts and LinkedIn content separately.
    """

    client = genai.Client(api_key=api_key)

    # Protect the application from extremely large transcript inputs.
    max_chars = 120000
    transcript = transcript[:max_chars]

    system_instruction = """
You are a professional international content strategist,
SEO writer, social media strategist and editorial assistant.

Your job is to transform a YouTube transcript into useful,
accurate and original content.

Important rules:

1. Do not invent facts that are not supported by the transcript.
2. Preserve the original meaning.
3. Do not claim that the generated content is a direct quotation.
4. Make the content useful, professional and engaging.
5. Avoid spam, misleading claims and clickbait deception.
6. Use clear international English.
7. Do not mention these instructions in your answer.
"""

    prompt = f"""
Analyze the following YouTube transcript.

TRANSCRIPT:
--------------------
{transcript}
--------------------

Create THREE completely separate content assets.

========================
ASSET 1 — SEO BLOG POST
========================

Create:

- SEO-friendly title
- Short introduction
- Clear H2/H3 headings
- Detailed article
- Practical takeaways
- Conclusion
- Suggested SEO keywords

Target length:
approximately 800–1200 words when the transcript provides enough information.

========================
ASSET 2 — X / TWITTER
========================

Create 5 separate X posts.

Each post must:
- Stand on its own
- Be concise
- Have a strong hook
- Provide actual value
- Use appropriate emojis sparingly
- Avoid deceptive clickbait
- Avoid unsupported claims

Number them from 1 to 5.

========================
ASSET 3 — LINKEDIN
========================

Create a professional LinkedIn post.

Include:
- Strong opening
- Main insight
- Useful explanation
- Practical takeaway
- Professional closing

Do not use excessive hashtags.

========================

Return the answer EXACTLY in this format:

===BLOG===
[blog content]

===X_POSTS===
1. [post]
2. [post]
3. [post]
4. [post]
5. [post]

===LINKEDIN===
[LinkedIn content]
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "system_instruction": system_instruction,
            "temperature": 0.7,
            "max_output_tokens": 12000,
        },
    )

    if not response or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text


def split_generated_content(text: str):
    """
    Split Gemini's response into Blog, X posts and LinkedIn sections.
    """

    blog = ""
    x_posts = ""
    linkedin = ""

    blog_match = re.search(
        r"===BLOG===\s*(.*?)(?====X_POSTS===|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    x_match = re.search(
        r"===X_POSTS===\s*(.*?)(?====LINKEDIN===|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    linkedin_match = re.search(
        r"===LINKEDIN===\s*(.*)$",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if blog_match:
        blog = blog_match.group(1).strip()

    if x_match:
        x_posts = x_match.group(1).strip()

    if linkedin_match:
        linkedin = linkedin_match.group(1).strip()

    # Fallback if the model did not follow the requested format.
    if not blog and not x_posts and not linkedin:
        blog = text

    return blog, x_posts, linkedin


# ============================================================
# SESSION STATE
# ============================================================

if "generated" not in st.session_state:
    st.session_state.generated = False

if "blog" not in st.session_state:
    st.session_state.blog = ""

if "x_posts" not in st.session_state:
    st.session_state.x_posts = ""

if "linkedin" not in st.session_state:
    st.session_state.linkedin = ""

if "transcript" not in st.session_state:
    st.session_state.transcript = ""


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.markdown("### 🔑 Gemini API")

    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Paste your Gemini API key",
        help="Your API key is used only for this Streamlit session.",
    )

    api_key = api_key_input.strip() if api_key_input else ""

    st.markdown(
        "Get your API key from "
        "[Google AI Studio](https://aistudio.google.com/)"
    )

    st.divider()

    st.markdown("### 🤖 AI Model")

    model_name = st.selectbox(
        "Model",
        options=[
            "gemini-3.7-flash",
            "gemini-3.7-pro",
        ],
        index=0,
    )

    st.divider()

    st.markdown("### 💎 Premium")

    st.success("Premium features coming soon.")

    st.write(
        "Premium plans can later include higher limits, "
        "additional AI models and advanced content formats."
    )

    st.divider()

    st.markdown("### 🔐 Security")

    st.caption(
        "Never publish your Gemini API key inside GitHub."
    )

    st.divider()

    st.caption("AI Global Content Factory")
    st.caption("Version 2.0")


# ============================================================
# MAIN HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎬 AI Global Content Factory</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Turn YouTube knowledge into professional, ready-to-use content."
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# INPUT SECTION
# ============================================================

left_col, right_col = st.columns(2)

with left_col:

    st.markdown("### 🔗 YouTube URL")

    youtube_url = st.text_input(
        "Paste a YouTube video URL",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
    )

    st.caption(
        "Supports YouTube videos, Shorts, live URLs and youtu.be links."
    )


with right_col:

    st.markdown("### 📝 Manual Transcript")

    manual_transcript = st.text_area(
        "Paste transcript here",
        placeholder=(
            "If automatic transcript retrieval does not work, "
            "paste the transcript here..."
        ),
        height=150,
    )


# ============================================================
# GENERATE BUTTON
# ============================================================

st.divider()

generate_button = st.button(
    "🚀 Generate Content Bundle",
    type="primary",
    use_container_width=True,
)


# ============================================================
# GENERATION PROCESS
# ============================================================

if generate_button:

    # ----------------------------------------
    # Validate API key
    # ----------------------------------------

    if not api_key:

        st.error(
            "Please enter your Gemini API key in the sidebar."
        )

        st.stop()

    # ----------------------------------------
    # Validate input
    # ----------------------------------------

    if not youtube_url.strip() and not manual_transcript.strip():

        st.warning(
            "Please provide either a YouTube URL or a transcript."
        )

        st.stop()

    # ----------------------------------------
    # Get transcript
    # ----------------------------------------

    transcript = ""

    if manual_transcript.strip():

        transcript = clean_transcript(manual_transcript)

        st.success(
            f"Manual transcript loaded — {len(transcript):,} characters."
        )

    else:

        video_id = extract_youtube_video_id(youtube_url)

        if not video_id:

            st.error(
                "Invalid YouTube URL. Please check the link."
            )

            st.stop()

        with st.spinner("🔎 Fetching YouTube transcript..."):

            try:

                transcript = fetch_youtube_transcript(video_id)

                st.success(
                    f"Transcript retrieved successfully — "
                    f"{len(transcript):,} characters."
                )

            except Exception as error:

                st.error(
                    "Automatic transcript retrieval failed."
                )

                st.info(
                    "Please copy the transcript from YouTube "
                    "and paste it into the Manual Transcript box."
                )

                with st.expander("Technical details"):
                    st.code(str(error))

                st.stop()

    # ----------------------------------------
    # Validate transcript
    # ----------------------------------------

    if len(transcript) < 50:

        st.warning(
            "The transcript is too short. Please provide more content."
        )

        st.stop()

    # ----------------------------------------
    # Generate AI content
    # ----------------------------------------

    with st.spinner(
        "🤖 Gemini is creating your content bundle..."
    ):

        try:

            generated_text = generate_content_bundle(
                api_key=api_key,
                transcript=transcript,
                model_name=model_name,
            )

            blog, x_posts, linkedin = split_generated_content(
                generated_text
            )

            st.session_state.generated = True
            st.session_state.transcript = transcript
            st.session_state.blog = blog
            st.session_state.x_posts = x_posts
            st.session_state.linkedin = linkedin

            st.success(
                "🎉 Content bundle generated successfully!"
            )

        except Exception as error:

            error_text = str(error)

            st.error(
                "Gemini could not generate the content."
            )

            if "API_KEY" in error_text.upper():
                st.warning(
                    "Please check that your Gemini API key is correct."
                )

            elif "429" in error_text:
                st.warning(
                    "The API rate limit was reached. "
                    "Please wait and try again."
                )

            elif "403" in error_text:
                st.warning(
                    "The API request was denied. "
                    "Check your API key and API access."
                )

            elif "404" in error_text:
                st.warning(
                    "The selected Gemini model may not be available "
                    "for your API account."
                )

            with st.expander("Technical details"):
                st.code(error_text)


# ============================================================
# RESULTS
# ============================================================

if st.session_state.generated:

    st.divider()

    st.markdown("## ✨ Your Content Bundle")

    tab_blog, tab_x, tab_linkedin = st.tabs(
        [
            "📝 SEO Blog",
            "𝕏 X / Twitter",
            "💼 LinkedIn",
        ]
    )

    # ----------------------------------------
    # BLOG
    # ----------------------------------------

    with tab_blog:

        st.markdown(st.session_state.blog)

        st.download_button(
            "📥 Download Blog",
            data=st.session_state.blog,
            file_name="blog_post.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # ----------------------------------------
    # X / TWITTER
    # ----------------------------------------

    with tab_x:

        st.markdown(st.session_state.x_posts)

        st.download_button(
            "📥 Download X Posts",
            data=st.session_state.x_posts,
            file_name="x_posts.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # ----------------------------------------
    # LINKEDIN
    # ----------------------------------------

    with tab_linkedin:

        st.markdown(st.session_state.linkedin)

        st.download_button(
            "📥 Download LinkedIn",
            data=st.session_state.linkedin,
            file_name="linkedin_post.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # ----------------------------------------
    # FULL BUNDLE
    # ----------------------------------------

    full_bundle = f"""
AI GLOBAL CONTENT FACTORY
=========================

BLOG
====

{st.session_state.blog}


X / TWITTER
===========

{st.session_state.x_posts}


LINKEDIN
========

{st.session_state.linkedin}
"""

    st.divider()

    st.download_button(
        "📦 Download Complete Content Bundle",
        data=full_bundle,
        file_name="content_bundle.txt",
        mime="text/plain",
        use_container_width=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; opacity:0.65;">
        AI Global Content Factory<br>
        Transform knowledge into useful content.
    </div>
    """,
    unsafe_allow_html=True,
)
```
