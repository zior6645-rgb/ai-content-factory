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
"Transform a YouTube transcript into Blog, X and LinkedIn content."
)

st.divider()

api_key = st.text_input(
"🔑 Gemini API Key",
type="password",
placeholder="Paste your Gemini API key"
)

transcript = st.text_area(
"📝 YouTube Transcript",
placeholder="Paste the transcript here...",
height=300
)

generate = st.button(
"🚀 Generate Content",
type="primary",
use_container_width=True
)

if generate:
key = api_key.strip()
text = transcript.strip()

```
if key == "":
    st.error("Please enter your Gemini API key.")
    st.stop()

if text == "":
    st.error("Please paste a YouTube transcript.")
    st.stop()

if len(text) < 50:
    st.error("The transcript is too short.")
    st.stop()

prompt = """
```

You are a professional international content strategist,
SEO writer and social media content creator.

Analyze the YouTube transcript below.

Do not invent facts.
Do not make unsupported claims.
Preserve the meaning of the source.
Write useful, professional and original English content.

Create these three sections.

[BLOG]

Create an SEO-friendly article with:

* Title
* Introduction
* Useful headings
* Detailed explanation
* Practical takeaways
* Conclusion
* SEO keywords

[X]

Create exactly 5 separate X/Twitter posts.
Each post must:

* Have a strong hook
* Provide useful information
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

Use exactly these section labels:
[BLOG]
[X]
[LINKEDIN]

YOUTUBE TRANSCRIPT:
""" + text[:100000]

```
try:
    client = genai.Client(api_key=key)

    with st.spinner("🤖 Gemini is generating your content..."):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

    result = response.text

    if result:
        st.success("🎉 Content generated successfully!")

        st.markdown(result)

        st.download_button(
            "📥 Download Content",
            result,
            file_name="content_bundle.md",
            mime="text/markdown",
            use_container_width=True
        )

    else:
        st.error("Gemini returned an empty response.")

except Exception as error:
    st.error("Gemini could not generate the content.")
    st.code(str(error))
```

st.divider()

st.caption(
"AI Global Content Factory • Powered by Streamlit + Gemini"
)
