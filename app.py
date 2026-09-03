import streamlit as st
import re
from google import genai

st.set_page_config(
page_title="AI Global Content Factory",
page_icon="🎬",
layout="wide"
)

st.sidebar.title("Settings")

api_key = st.sidebar.text_input(
"Gemini API Key",
type="password",
placeholder="Paste your Gemini API key"
)

api_key = api_key.strip()

st.sidebar.markdown(
"[Get Gemini API Key](https://aistudio.google.com/apikey)"
)

st.sidebar.divider()
st.sidebar.caption("AI Global Content Factory")
st.sidebar.caption("Version 1.0")

def extract_video_id(url):
if not url:
return None

```
url = url.strip()

patterns = [
    r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
    r"youtu\.be/([A-Za-z0-9_-]{11})",
    r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
    r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
    r"youtube\.com/live/([A-Za-z0-9_-]{11})"
]

for pattern in patterns:
    match = re.search(pattern, url)

    if match:
        return match.group(1)

return None
```

def clean_text(text):
if not text:
return ""

```
text = text.replace("\r", " ")
text = text.replace("\n", " ")
text = re.sub(r"\s+", " ", text)

return text.strip()
```

def get_transcript(video_id):
from youtube_transcript_api import YouTubeTranscriptApi

```
api = YouTubeTranscriptApi()

transcript = api.fetch(
    video_id,
    languages=["en", "fa"]
)

parts = []

for item in transcript:
    if hasattr(item, "text"):
        parts.append(item.text)

result = clean_text(" ".join(parts))

if not result:
    raise Exception("Transcript is empty.")

return result
```

def generate_content(api_key, transcript):
from google.genai import types

```
client = genai.Client(
    api_key=api_key
)

transcript = transcript[:80000]

prompt = """
```

You are a professional international content strategist,
SEO writer and social media content creator.

Analyze the transcript below.

Rules:

* Do not invent facts.
* Do not make unsupported claims.
* Preserve the original meaning.
* Write professional international English.
* Make the content useful and original.
* Avoid misleading clickbait.

TRANSCRIPT:

""" + transcript + """

Create the following:

1. BLOG

Create a detailed SEO-friendly blog article with:

* SEO title
* Introduction
* H2/H3 headings
* Detailed useful content
* Practical takeaways
* Conclusion
* SEO keywords

2. X / TWITTER

Create exactly 5 concise posts.
Each post must have a strong hook and useful information.

3. LINKEDIN

Create one professional LinkedIn post with:

* Strong opening
* Main insight
* Explanation
* Practical takeaway
* Professional ending
* 3 to 5 hashtags

Return exactly this format:

[BLOG]

Blog article

[X]

1. Post one
2. Post two
3. Post three
4. Post four
5. Post five

[LINKEDIN]

LinkedIn post
"""

```
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=8000
    )
)

if response is None:
    raise Exception("Gemini returned no response.")

if not response.text:
    raise Exception("Gemini returned empty text.")

return response.text
```

def split_content(text):
blog = ""
x_posts = ""
linkedin = ""

```
blog_match = re.search(
    r"\[BLOG\](.*?)(?=\[X\]|\Z)",
    text,
    re.IGNORECASE | re.DOTALL
)

x_match = re.search(
    r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
    text,
    re.IGNORECASE | re.DOTALL
)

linkedin_match = re.search(
    r"\[LINKEDIN\](.*)",
    text,
    re.IGNORECASE | re.DOTALL
)

if blog_match:
    blog = blog_match.group(1).strip()

if x_match:
    x_posts = x_match.group(1).strip()

if linkedin_match:
    linkedin = linkedin_match.group(1).strip()

if not blog and not x_posts and not linkedin:
    blog = text.strip()

return blog, x_posts, linkedin
```

st.title("AI Global Content Factory")

st.subheader(
"Transform YouTube content into professional AI content."
)

st.write(
"Generate SEO blog posts, X/Twitter posts and LinkedIn content."
)

col1, col2 = st.columns(2)

with col1:
st.subheader("YouTube URL")

```
youtube_url = st.text_input(
    "Paste YouTube URL",
    placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX"
)
```

with col2:
st.subheader("Manual Transcript")

```
manual_transcript = st.text_area(
    "Paste transcript here",
    placeholder="Paste the YouTube transcript here...",
    height=180
)
```

st.divider()

generate_button = st.button(
"Generate Content",
type="primary",
use_container_width=True
)

if generate_button:

```
if not api_key:
    st.error(
        "Please enter your Gemini API key in the sidebar."
    )
    st.stop()

transcript = ""

if manual_transcript.strip():

    transcript = clean_text(
        manual_transcript
    )

elif youtube_url.strip():

    video_id = extract_video_id(
        youtube_url
    )

    if not video_id:
        st.error(
            "Invalid YouTube URL."
        )
        st.stop()

    with st.spinner(
        "Fetching YouTube transcript..."
    ):

        try:
            transcript = get_transcript(
                video_id
            )

        except Exception as error:

            st.error(
                "Automatic transcript retrieval failed."
            )

            st.info(
                "Please copy the transcript from YouTube "
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
        "Please enter a YouTube URL or paste a transcript."
    )

    st.stop()

if len(transcript) < 50:

    st.warning(
        "The transcript is too short."
    )

    st.stop()

with st.spinner(
    "Gemini is generating your content..."
):

    try:

        result = generate_content(
            api_key,
            transcript
        )

    except Exception as error:

        st.error(
            "Gemini could not generate the content."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(error)
            )

        st.stop()

blog, x_posts, linkedin = split_content(
    result
)

st.success(
    "Content generated successfully."
)

tab1, tab2, tab3 = st.tabs(
    [
        "Blog",
        "X / Twitter",
        "LinkedIn"
    ]
)

with tab1:

    st.markdown(blog)

    st.download_button(
        "Download Blog",
        blog,
        "blog_post.md",
        "text/markdown",
        use_container_width=True
    )

with tab2:

    st.markdown(x_posts)

    st.download_button(
        "Download X Posts",
        x_posts,
        "x_posts.txt",
        "text/plain",
        use_container_width=True
    )

with tab3:

    st.markdown(linkedin)

    st.download_button(
        "Download LinkedIn",
        linkedin,
        "linkedin_post.md",
        "text/markdown",
        use_container_width=True
    )

complete_bundle = (
    "AI GLOBAL CONTENT FACTORY\n\n"
    "BLOG\n\n"
    + blog
    + "\n\nX / TWITTER\n\n"
    + x_posts
    + "\n\nLINKEDIN\n\n"
    + linkedin
)

st.download_button(
    "Download Complete Bundle",
    complete_bundle,
    "content_bundle.txt",
    "text/plain",
    use_container_width=True
)
```

st.divider()

st.caption(
"AI Global Content Factory | Powered by Streamlit and Gemini"
)
