import re
import streamlit as st
from google import genai

st.set_page_config(
page_title="AI Global Content Factory",
page_icon="🎬",
layout="wide"
)

st.title("🎬 AI Global Content Factory")
st.subheader("Turn YouTube knowledge into professional content")

st.write(
"Create a Blog article, X posts and a LinkedIn post from a YouTube transcript."
)

st.divider()

api_key = st.text_input(
"🔑 Gemini API Key",
type="password",
placeholder="Paste your Gemini API key here"
)

st.caption("Your API key is used only for the current session.")

youtube_url = st.text_input(
"🔗 YouTube URL",
placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX"
)

manual_transcript = st.text_area(
"📝 Transcript",
placeholder="Paste the YouTube transcript here...",
height=220
)

generate = st.button(
"🚀 Generate Content",
type="primary",
use_container_width=True
)

if generate:

```
if api_key.strip() == "":
    st.error("Please enter your Gemini API key.")
    st.stop()

transcript = manual_transcript.strip()

if transcript == "":
    st.warning(
        "Please paste a YouTube transcript. "
        "Automatic transcript retrieval will be added in the next version."
    )
    st.stop()

if len(transcript) < 50:
    st.warning("The transcript is too short.")
    st.stop()

try:

    client = genai.Client(
        api_key=api_key.strip()
    )

    prompt = f"""
```

You are an expert international content strategist,
SEO writer and social media content creator.

Analyze the following YouTube transcript.

Do not invent facts.
Do not add unsupported claims.
Preserve the meaning of the source.
Write professional, useful and original English content.

TRANSCRIPT:
{transcript[:100000]}

Create exactly these three sections.

[BLOG]

Create a professional SEO-friendly article with:

Title
Introduction
Several useful headings
Detailed explanation
Practical takeaways
Conclusion
SEO keywords

[X]

Create exactly 5 separate X/Twitter posts.

Each post should:

* Have a strong hook
* Give useful information
* Be concise
* Use emojis naturally
* Avoid misleading claims

[LINKEDIN]

Create one professional LinkedIn post with:

* Strong opening
* Main insight
* Explanation
* Practical takeaway
* Professional ending
* 3 to 5 relevant hashtags

Return only the three sections using exactly:
[BLOG]
[X]
[LINKEDIN]
"""

```
    with st.spinner("🤖 Gemini is generating your content..."):

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

    result = response.text

    if result is None:
        st.error("Gemini returned an empty response.")
        st.stop()

    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\])",
        result,
        re.IGNORECASE | re.DOTALL
    )

    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\])",
        result,
        re.IGNORECASE | re.DOTALL
    )

    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        result,
        re.IGNORECASE | re.DOTALL
    )

    blog = ""
    x_posts = ""
    linkedin = ""

    if blog_match:
        blog = blog_match.group(1).strip()

    if x_match:
        x_posts = x_match.group(1).strip()

    if linkedin_match:
        linkedin = linkedin_match.group(1).strip()

    st.success("🎉 Content generated successfully!")

    tab1, tab2, tab3 = st.tabs(
        [
            "📝 Blog",
            "𝕏 X / Twitter",
            "💼 LinkedIn"
        ]
    )

    with tab1:

        st.markdown(blog)

        st.download_button(
            "📥 Download Blog",
            blog,
            file_name="blog_post.md",
            mime="text/markdown",
            use_container_width=True
        )

    with tab2:

        st.markdown(x_posts)

        st.download_button(
            "📥 Download X Posts",
            x_posts,
            file_name="x_posts.txt",
            mime="text/plain",
            use_container_width=True
        )

    with tab3:

        st.markdown(linkedin)

        st.download_button(
            "📥 Download LinkedIn",
            linkedin,
            file_name="linkedin_post.md",
            mime="text/markdown",
            use_container_width=True
        )

    complete_content = (
        "AI GLOBAL CONTENT FACTORY\n\n"
        "================ BLOG ================\n\n"
        + blog
        + "\n\n"
        "================ X / TWITTER ================\n\n"
        + x_posts
        + "\n\n"
        "================ LINKEDIN ================\n\n"
        + linkedin
    )

    st.divider()

    st.download_button(
        "📦 Download Complete Bundle",
        complete_content,
        file_name="content_bundle.txt",
        mime="text/plain",
        use_container_width=True
    )

except Exception as error:

    st.error("Gemini could not generate the content.")

    st.code(str(error))
```

st.divider()

st.caption(
"AI Global Content Factory • Powered by Streamlit + Gemini"
)
