import re

import streamlit as st
from google import genai


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 AI Global Content Factory")
st.subheader("Transform YouTube knowledge into professional content")

st.write(
    "Generate high-quality Blog, X/Twitter and LinkedIn content "
    "from a YouTube transcript."
)

st.divider()

api_key = st.text_input(
    "🔑 Gemini API Key",
    type="password",
    placeholder="Paste your Gemini API key here",
)

st.caption("Your API key is used only for the current Streamlit session.")

st.divider()

youtube_url = st.text_input(
    "🔗 YouTube URL",
    placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
)

manual_transcript = st.text_area(
    "📝 YouTube Transcript",
    placeholder=(
        "Paste the transcript here. Manual transcript is recommended "
        "when automatic YouTube access is unavailable."
    ),
    height=260,
)

generate_button = st.button(
    "🚀 Generate Content",
    type="primary",
    use_container_width=True,
)


def extract_video_id(url):
    if not url:
        return ""

    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url.strip())

        if match:
            return match.group(1)

    return ""


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_transcript(video_id):
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()

    transcript = api.fetch(
        video_id,
        languages=["en", "fa"],
    )

    parts = []

    for item in transcript:
        if hasattr(item, "text"):
            parts.append(item.text)

    result = clean_text(" ".join(parts))

    if not result:
        raise Exception("The YouTube transcript is empty.")

    return result


def generate_content(api_key_value, transcript_value):
    client = genai.Client(api_key=api_key_value)

    transcript_value = transcript_value[:100000]

    prompt = """
You are an expert international content strategist,
SEO writer, editorial writer and social media content creator.

Your job is to transform the supplied YouTube transcript
into useful, professional and original content.

IMPORTANT RULES:

* Do not invent facts.
* Do not create unsupported claims.
* Do not misrepresent the original speaker.
* Preserve the meaning of the source.
* Clearly distinguish opinions from factual claims.
* Avoid misleading clickbait.
* Do not fabricate statistics, quotations or sources.
* Write professional international English.
* Make the content useful and readable.
* Do not mention that you are an AI.
* Do not add information that cannot reasonably be supported by the transcript.

CREATE THREE CONTENT ASSETS.

========================
BLOG
====

Create a professional SEO-friendly article.

Include:

1. SEO-friendly title
2. Introduction
3. Logical H2/H3 headings
4. Detailed explanation
5. Important insights
6. Practical takeaways
7. Conclusion
8. SEO keywords

The article should be informative and natural.

========================
X / TWITTER
===========

Create exactly 5 separate X/Twitter posts.

Each post must:

* Have a strong opening
* Communicate one useful idea
* Be concise
* Be easy to read
* Use emojis naturally where appropriate
* Avoid misleading claims
* Avoid excessive hashtags

Number them 1 through 5.

========================
LINKEDIN
========

Create one professional LinkedIn post.

Include:

* Strong opening
* Main insight
* Explanation
* Practical takeaway
* Professional closing
* 3 to 5 relevant hashtags

========================
OUTPUT FORMAT
=============

Use exactly these three labels:

[BLOG]

[X]

[LINKEDIN]

Do not add any other section labels.

========================
SOURCE TRANSCRIPT
=================

""" + transcript_value

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    if response is None:
        raise Exception("Gemini returned no response.")

    result = response.text

    if not result:
        raise Exception("Gemini returned an empty response.")

    return result


def split_content(result):
    blog = ""
    x_posts = ""
    linkedin = ""

    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\])",
        result,
        re.IGNORECASE | re.DOTALL,
    )

    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\])",
        result,
        re.IGNORECASE | re.DOTALL,
    )

    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        result,
        re.IGNORECASE | re.DOTALL,
    )

    if blog_match:
        blog = blog_match.group(1).strip()

    if x_match:
        x_posts = x_match.group(1).strip()

    if linkedin_match:
        linkedin = linkedin_match.group(1).strip()

    if not blog and not x_posts and not linkedin:
        blog = result.strip()

    return blog, x_posts, linkedin


if generate_button:
    key = api_key.strip()

    if not key:
        st.error("❌ Please enter your Gemini API key.")
        st.stop()

    transcript = clean_text(manual_transcript)

    if not transcript and youtube_url.strip():
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error("❌ The YouTube URL is not valid.")
            st.stop()

        with st.spinner("🔎 Fetching YouTube transcript..."):
            try:
                transcript = get_transcript(video_id)

            except Exception as error:
                st.error("⚠️ Automatic YouTube transcript retrieval failed.")
                st.info(
                    "Please copy the transcript from YouTube and paste it "
                    "into the Transcript box."
                )

                with st.expander("Technical details"):
                    st.code(str(error))

                st.stop()

    if not transcript:
        st.warning("Please enter a YouTube URL or paste a transcript.")
        st.stop()

    if len(transcript) < 50:
        st.warning(
            "The transcript is too short. Please provide more content."
        )
        st.stop()

    st.info(
        "Transcript loaded: "
        + format(len(transcript), ",")
        + " characters."
    )

    with st.spinner("🤖 Gemini is creating your content..."):
        try:
            result = generate_content(key, transcript)

        except Exception as error:
            error_message = str(error)

            st.error("❌ Gemini could not generate the content.")

            if "401" in error_message:
                st.warning("Your Gemini API key may be invalid.")
            elif "403" in error_message:
                st.warning(
                    "The API request was rejected. Check your Gemini API "
                    "key and access."
                )
            elif "429" in error_message:
                st.warning(
                    "The API rate limit was reached. Please wait and try again."
                )
            else:
                st.warning("Please review the technical details below.")

            with st.expander("Technical details"):
                st.code(error_message)

            st.stop()

    blog, x_posts, linkedin = split_content(result)

    st.success("🎉 Your content has been generated successfully!")

    tab_blog, tab_x, tab_linkedin = st.tabs(
        ["📝 Blog", "𝕏 X / Twitter", "💼 LinkedIn"]
    )

    with tab_blog:
        st.markdown(blog)

        st.download_button(
            "📥 Download Blog",
            blog,
            file_name="blog_post.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with tab_x:
        st.markdown(x_posts)

        st.download_button(
            "📥 Download X Posts",
            x_posts,
            file_name="x_posts.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with tab_linkedin:
        st.markdown(linkedin)

        st.download_button(
            "📥 Download LinkedIn",
            linkedin,
            file_name="linkedin_post.md",
            mime="text/markdown",
            use_container_width=True,
        )

    complete_bundle = (
        "AI GLOBAL CONTENT FACTORY\n\n"
        "================================\n"
        "BLOG\n"
        "================================\n\n"
        + blog
        + "\n\n"
        "================================\n"
        "X / TWITTER\n"
        "================================\n\n"
        + x_posts
        + "\n\n"
        "================================\n"
        "LINKEDIN\n"
        "================================\n\n"
        + linkedin
    )

    st.divider()

    st.download_button(
        "📦 Download Complete Content Bundle",
        complete_bundle,
        file_name="content_bundle.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.divider()

st.caption("AI Global Content Factory • Powered by Streamlit + Gemini")
