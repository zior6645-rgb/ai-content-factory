import re
import streamlit as st
from google import genai
from google.genai import types
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
page_title="AI Global Content Factory",
page_icon="🎬",
layout="wide"
)

def extract_video_id(url):
if not url:
return None

```
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

def fetch_transcript(video_id):
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

result = clean_text(" ".join(parts))

if not result:
    raise Exception("The YouTube transcript is empty.")

return result
```

def generate_content(api_key, transcript):
client = genai.Client(api_key=api_key)

```
transcript = transcript[:100000]

prompt = f"""
```

You are an expert international content strategist,
SEO writer and social media content creator.

Analyze the YouTube transcript below.

Rules:

* Do not invent facts.
* Do not make unsupported claims.
* Preserve the original meaning.
* Write in professional international English.
* Make the content useful and original.
* Avoid misleading clickbait.

# YOUTUBE TRANSCRIPT

{transcript}

==================

Create THREE separate content assets.

1. BLOG

Create an SEO-friendly article with:

* SEO title
* Introduction
* H2 and H3 headings
* Detailed useful content
* Practical takeaways
* Conclusion
* SEO keywords

2. X / TWITTER

Create exactly 5 separate posts.

Each post must:

* Have a strong hook
* Provide useful information
* Be concise
* Use emojis naturally
* Avoid misleading claims

3. LINKEDIN

Create one professional LinkedIn post with:

* Strong opening
* Main insight
* Explanation
* Practical takeaway
* Professional ending
* 3 to 5 relevant hashtags

Return ONLY this structure:

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

```
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=10000
    )
)

if not response:
    raise Exception("Gemini returned no response.")

if not response.text:
    raise Exception("Gemini returned empty text.")

return response.text
```

def split_result(text):
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

with st.sidebar:

```
st.header("Settings")

st.subheader("Gemini API Key")

api_key = st.text_input(
    "Enter your Gemini API key",
    type="password",
    placeholder="Paste your API key here"
)

api_key = api_key.strip()

st.markdown(
    "Get your API key from "
    "[Google AI Studio](https://aistudio.google.com/)"
)

st.divider()

st.subheader("Premium")

st.info(
    "Premium features can be added later, "
    "including higher limits and additional content tools."
)

st.divider()

st.caption("AI Global Content Factory")
st.caption("Version 3.1")
```

st.title("AI Global Content Factory")

st.subheader(
"Turn YouTube content into professional AI-generated content."
)

st.write(
"Create SEO blog posts, X/Twitter posts and LinkedIn content "
"from a YouTube transcript."
)

col1, col2 = st.columns(2)

with col1:

```
st.markdown("### YouTube URL")

youtube_url = st.text_input(
    "Paste a YouTube URL",
    placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX"
)

st.caption(
    "Supports standard YouTube, Shorts, live and youtu.be URLs."
)
```

with col2:

```
st.markdown("### Manual Transcript")

manual_transcript = st.text_area(
    "Paste transcript",
    placeholder=(
        "If automatic transcript retrieval fails, "
        "paste the transcript here."
    ),
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

    st.success(
        f"Manual transcript loaded: {len(transcript):,} characters."
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

            transcript = fetch_transcript(
                video_id
            )

            st.success(
                f"Transcript retrieved: {len(transcript):,} characters."
            )

        except Exception as error:

            st.error(
                "Automatic YouTube transcript retrieval failed."
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

        error_text = str(error)

        st.error(
            "Gemini could not generate the content."
        )

        if "401" in error_text:

            st.warning(
                "The Gemini API key may be invalid."
            )

        elif "403" in error_text:

            st.warning(
                "The Gemini API request was rejected."
            )

        elif "429" in error_text:

            st.warning(
                "The Gemini API rate limit was reached. "
                "Please wait and try again."
            )

        else:

            st.warning(
                "Please check the technical details."
            )

        with st.expander(
            "Technical details"
        ):

            st.code(
                error_text
            )

        st.stop()


blog, x_posts, linkedin = split_result(
    result
)


st.success(
    "Content generated successfully!"
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
            data=blog,
            file_name="blog_post.md",
            mime="text/markdown",
            use_container_width=True
        )

    else:

        st.warning(
            "Blog content was not detected."
        )


with tab2:

    if x_posts:

        st.markdown(x_posts)

        st.download_button(
            "Download X Posts",
            data=x_posts,
            file_name="x_posts.txt",
            mime="text/plain",
            use_container_width=True
        )

    else:

        st.warning(
            "X posts were not detected."
        )


with tab3:

    if linkedin:

        st.markdown(linkedin)

        st.download_button(
            "Download LinkedIn",
            data=linkedin,
            file_name="linkedin_post.md",
            mime="text/markdown",
            use_container_width=True
        )

    else:

        st.warning(
            "LinkedIn content was not detected."
        )


complete_content = f"""
```

AI GLOBAL CONTENT FACTORY

# BLOG

{blog}

# X / TWITTER

{x_posts}

# LINKEDIN

{linkedin}
"""

```
st.divider()


st.download_button(
    "Download Complete Bundle",
    data=complete_content,
    file_name="content_bundle.txt",
    mime="text/plain",
    use_container_width=True
)
```

st.divider()

st.caption(
"AI Global Content Factory | Powered by Streamlit and Gemini"
)
