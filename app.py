import streamlit as st
import re
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
page_title="AI Global Content Factory",
page_icon="🎬",
layout="wide"
)

st.title("AI Global Content Factory")
st.write("Transform YouTube content into professional AI-generated content.")

with st.sidebar:
st.header("Settings")

```
api_key = st.text_input(
    "Gemini API Key",
    type="password",
    placeholder="Paste your Gemini API key"
)

api_key = api_key.strip()

st.markdown(
    "[Get a Gemini API key](https://aistudio.google.com/apikey)"
)

st.divider()
st.caption("AI Global Content Factory")
st.caption("Version 1.0")
```

def extract_video_id(url):
if not url:
return None

```
url = url.strip()

match = re.search(
    r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})",
    url
)

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
api = YouTubeTranscriptApi()

```
transcript = api.fetch(
    video_id,
    languages=["en", "fa"]
)

parts = []

for item in transcript:
    if hasattr(item, "text"):
        parts.append(item.text)

text = " ".join(parts)
text = clean_text(text)

if not text:
    raise Exception("Transcript is empty.")

return text
```

def generate_content(api_key, transcript):
client = genai.Client(api_key=api_key)

```
transcript = transcript[:80000]

prompt = """
```

You are an expert content writer and SEO strategist.

Analyze the YouTube transcript below and create useful,
accurate and original content.

Never invent facts.
Never create unsupported claims.
Preserve the meaning of the source.
Write in professional international English.

# SOURCE TRANSCRIPT

""" + transcript + """

=================

Create three sections.

SECTION 1: BLOG

Create:

* SEO title
* Introduction
* Headings
* Detailed article
* Practical takeaways
* Conclusion
* SEO keywords

SECTION 2: X POSTS

Create exactly 5 concise X/Twitter posts.
Each post should have a strong hook and useful information.

SECTION 3: LINKEDIN

Create one professional LinkedIn post with:

* Strong opening
* Main insight
* Explanation
* Practical takeaway
* Professional ending
* 3 to 5 hashtags

Use exactly this format:

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
    raise Exception("No response from Gemini.")

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

st.subheader("YouTube Content")

youtube_url = st.text_input(
"YouTube URL",
placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX"
)

st.subheader("Manual Transcript")

manual_transcript = st.text_area(
"Paste transcript here if automatic retrieval does not work",
height=180
)

generate = st.button(
"Generate Content",
type="primary",
use_container_width=True
)

if generate:

```
if not api_key:
    st.error("Please enter your Gemini API key.")
    st.stop()

transcript = ""

if manual_transcript.strip():
    transcript = clean_text(manual_transcript)

elif youtube_url.strip():

    video_id = extract_video_id(youtube_url)

    if not video_id:
        st.error("Invalid YouTube URL.")
        st.stop()

    with st.spinner("Fetching YouTube transcript..."):

        try:
            transcript = get_transcript(video_id)

        except Exception as error:
            st.error(
                "Could not automatically retrieve the transcript."
            )

            st.info(
                "Please paste the YouTube transcript manually."
            )

            with st.expander("Technical details"):
                st.code(str(error))

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

with st.spinner("Gemini is generating your content..."):

    try:
        result = generate_content(
            api_key,
            transcript
        )

    except Exception as error:

        st.error(
            "Gemini could not generate the content."
        )

        with st.expander("Technical details"):
            st.code(str(error))

        st.stop()

blog, x_posts, linkedin = split_content(result)

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

    if blog:
        st.markdown(blog)

        st.download_button(
            "Download Blog",
            blog,
            "blog_post.md",
            "text/markdown",
            use_container_width=True
        )

with tab2:

    if x_posts:
        st.markdown(x_posts)

        st.download_button(
            "Download X Posts",
            x_posts,
            "x_posts.txt",
            "text/plain",
            use_container_width=True
        )

with tab3:

    if linkedin:
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
    + "\n\n"
    "X / TWITTER\n\n"
    + x_posts
    + "\n\n"
    "LINKEDIN\n\n"
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
