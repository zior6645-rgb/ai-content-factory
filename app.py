import hashlib
import os
import re
import secrets
import sqlite3
from datetime import datetime
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import streamlit as st
from groq import Groq


DATABASE_FILE = "content_factory.db"


def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


GROQ_API_KEY = get_setting("GROQ_API_KEY")
GROQ_MODEL = get_setting(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)
USDT_NETWORK = get_setting("USDT_NETWORK", "TRC20")
USDT_ADDRESS = get_setting("USDT_RECEIVE_ADDRESS")
USDT_AMOUNT = get_setting("USDT_AMOUNT", "10")


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                blog TEXT NOT NULL,
                x_posts TEXT NOT NULL,
                linkedin TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_hash TEXT NOT NULL,
                network TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, saved_hash = stored_hash.split("$", 1)
    except ValueError:
        return False

    current_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()

    return secrets.compare_digest(current_hash, saved_hash)


def create_user(
    username: str,
    email: str,
    password: str,
) -> tuple[bool, str]:
    if len(username.strip()) < 3:
        return False, "Username must contain at least 3 characters."

    if "@" not in email or "." not in email:
        return False, "Enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO users
                (username, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    username.strip(),
                    email.strip().lower(),
                    hash_password(password),
                    datetime.utcnow().isoformat(),
                ),
            )

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "Username or email already exists."


def authenticate_user(
    identifier: str,
    password: str,
) -> sqlite3.Row | None:
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ? OR email = ?
            """,
            (
                identifier.strip(),
                identifier.strip().lower(),
            ),
        ).fetchone()

    if user and verify_password(password, user["password_hash"]):
        return user

    return None


def save_history(
    user_id: int,
    source_text: str,
    blog: str,
    x_posts: str,
    linkedin: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO content_history
            (user_id, source_text, blog, x_posts, linkedin, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                source_text,
                blog,
                x_posts,
                linkedin,
                datetime.utcnow().isoformat(),
            ),
        )


def get_history(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, source_text, blog, x_posts, linkedin, created_at
            FROM content_history
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()


def save_payment_reference(
    user_id: int,
    transaction_hash: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO payment_references
            (user_id, transaction_hash, network, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                transaction_hash.strip(),
                USDT_NETWORK,
                "pending_review",
                datetime.utcnow().isoformat(),
            ),
        )


def clean_text(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        (value or "").replace("\r", " ").replace("\n", " "),
    ).strip()


def extract_video_id(url: str) -> str:
    if not url:
        return ""

    try:
        parsed_url = urlparse(url.strip())
        host = parsed_url.netloc.lower().replace("www.", "")

        if host == "youtu.be":
            video_id = parsed_url.path.strip("/").split("/")[0]
        elif host in {"youtube.com", "m.youtube.com"}:
            if parsed_url.path == "/watch":
                video_id = parse_qs(
                    parsed_url.query
                ).get("v", [""])[0]
            else:
                parts = parsed_url.path.strip("/").split("/")
                video_id = parts[1] if len(parts) > 1 else ""
        else:
            return ""

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return video_id

    except ValueError:
        return ""

    return ""


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_transcript(video_id: str) -> str:
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


def generate_content(transcript: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not configured by the owner."
        )

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are a professional international SEO writer and
social media content strategist.

Transform the transcript into accurate and useful content.

Rules:
- Do not invent facts, statistics or quotations.
- Do not add unsupported information.
- Preserve the speaker's meaning.
- Use professional international English.
- Create exactly three assets.

[BLOG]
Create one detailed SEO article with a title,
introduction, headings, insights, practical takeaways,
conclusion and SEO keywords.

[X]
Create exactly five concise X posts.
Number them from 1 to 5.

[LINKEDIN]
Create exactly one professional LinkedIn post
with a strong opening, insight, takeaway,
conclusion and 3 to 5 hashtags.

Use only these labels:
[BLOG]
[X]
[LINKEDIN]

SOURCE TRANSCRIPT:
{transcript[:100000]}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.35,
        max_tokens=8000,
    )

    if not response.choices:
        raise RuntimeError("The AI provider returned no result.")

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("The AI provider returned empty content.")

    return content.strip()


def split_content(
    content: str,
) -> tuple[str, str, str]:
    blog_match = re.search(
        r"\[BLOG\](.*?)(?=\[X\]|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )

    x_match = re.search(
        r"\[X\](.*?)(?=\[LINKEDIN\]|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )

    linkedin_match = re.search(
        r"\[LINKEDIN\](.*)",
        content,
        re.IGNORECASE | re.DOTALL,
    )

    blog = blog_match.group(1).strip() if blog_match else ""
    x_posts = x_match.group(1).strip() if x_match else ""
    linkedin = (
        linkedin_match.group(1).strip()
        if linkedin_match
        else ""
    )

    if not any((blog, x_posts, linkedin)):
        blog = content.strip()

    return blog, x_posts, linkedin


def show_authentication() -> None:
    st.title("AI Global Content Factory")
    st.subheader("Create an account or sign in")

    register_tab, login_tab = st.tabs(
        ["Create Account", "Sign In"]
    )

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input(
                "Password",
                type="password",
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = create_user(
                    username,
                    email,
                    password,
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

    with login_tab:
        with st.form("login_form"):
            identifier = st.text_input(
                "Username or Email"
            )
            password = st.text_input(
                "Password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Sign In",
                use_container_width=True,
            )

        if submitted:
            user = authenticate_user(
                identifier,
                password,
            )

            if user:
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.rerun()
            else:
                st.error(
                    "Invalid username, email or password."
                )


def render_payment_section(user_id: int) -> None:
    st.subheader("USDT Payment")

    if not USDT_ADDRESS:
        st.info(
            "Payment details are not configured by the owner."
        )
        return

    st.write(f"Network: `{USDT_NETWORK}`")
    st.write(f"Amount: `{USDT_AMOUNT} USDT`")
    st.code(USDT_ADDRESS, language="text")

    try:
        import qrcode

        qr_image = qrcode.make(USDT_ADDRESS)
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        st.image(
            buffer.getvalue(),
            width=180,
        )
    except ImportError:
        st.caption("QR code support is unavailable.")

    st.warning(
        "Send USDT only on the displayed network."
    )

    transaction_hash = st.text_input(
        "Transaction Hash",
        key="transaction_hash",
    )

    if st.button(
        "Submit Payment Reference",
        use_container_width=True,
    ):
        if not transaction_hash.strip():
            st.error("Enter a transaction hash.")
        else:
            save_payment_reference(
                user_id,
                transaction_hash,
            )
            st.success(
                "Payment reference submitted for review."
            )


def render_history(user_id: int) -> None:
    history = get_history(user_id)

    if not history:
        st.info("Your content history is empty.")
        return

    for item in history:
        created_at = item["created_at"][:19]

        with st.expander(
            f"Content generated on {created_at}"
        ):
            st.download_button(
                "Download Blog",
                item["blog"],
                f"blog_{item['id']}.md",
                "text/markdown",
                key=f"blog_{item['id']}",
            )

            st.markdown(item["blog"])

            st.download_button(
                "Download X Posts",
                item["x_posts"],
                f"x_posts_{item['id']}.txt",
                "text/plain",
                key=f"x_{item['id']}",
            )

            st.download_button(
                "Download LinkedIn Post",
                item["linkedin"],
                f"linkedin_{item['id']}.md",
                "text/markdown",
                key=f"linkedin_{item['id']}",
            )


def main() -> None:
    initialize_database()

    if "user_id" not in st.session_state:
        show_authentication()
        return

    user_id = st.session_state.user_id
    username = st.session_state.username

    with st.sidebar:
        st.write(f"Signed in as: **{username}**")

        if st.button(
            "Sign Out",
            use_container_width=True,
        ):
            st.session_state.clear()
            st.rerun()

        st.divider()

        with st.expander("USDT Payment"):
            render_payment_section(user_id)

    st.title("🎬 AI Global Content Factory")
    st.write(
        "Create an article, five X posts and one LinkedIn post."
    )

    history_tab, factory_tab = st.tabs(
        ["Content History", "Content Factory"]
    )

    with history_tab:
        render_history(user_id)

    with factory_tab:
        column_one, column_two = st.columns(2)

        with column_one:
            youtube_url = st.text_input(
                "YouTube URL",
                placeholder=(
                    "https://www.youtube.com/watch?v=XXXXXXXXXXX"
                ),
            )

        with column_two:
            manual_transcript = st.text_area(
                "Manual Transcript",
                height=220,
                placeholder=(
                    "Paste a transcript if retrieval fails."
                ),
            )

        if st.button(
            "🚀 Generate Content",
            type="primary",
            use_container_width=True,
        ):
            transcript = clean_text(manual_transcript)

            if not transcript and youtube_url.strip():
                video_id = extract_video_id(youtube_url)

                if not video_id:
                    st.error("The YouTube URL is invalid.")
                    st.stop()

                with st.spinner(
                    "Fetching the transcript..."
                ):
                    try:
                        transcript = fetch_transcript(video_id)
                    except Exception as error:
                        st.error(
                            "The transcript could not be retrieved."
                        )
                        st.code(str(error))
                        st.stop()

            if not transcript:
                st.warning(
                    "Provide a YouTube URL or transcript."
                )
                st.stop()

            if len(transcript) < 50:
                st.warning(
                    "The transcript is too short."
                )
                st.stop()

            with st.spinner(
                "Creating professional content..."
            ):
                try:
                    generated_content = generate_content(
                        transcript
                    )
                except Exception as error:
                    st.error(
                        "Content generation failed."
                    )
                    st.code(str(error))
                    st.stop()

            blog, x_posts, linkedin = split_content(
                generated_content
            )

            save_history(
                user_id,
                transcript,
                blog,
                x_posts,
                linkedin,
            )

            st.success(
                "Content generated and saved to your history."
            )

            blog_tab, x_tab, linkedin_tab = st.tabs(
                ["Blog", "X Posts", "LinkedIn"]
            )

            with blog_tab:
                st.markdown(blog)

            with x_tab:
                st.markdown(x_posts)

            with linkedin_tab:
                st.markdown(linkedin)


if __name__ == "__main__":
    main()
