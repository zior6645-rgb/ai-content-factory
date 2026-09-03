import hashlib
import os
import random
import re
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import streamlit as st
from groq import Groq


DATABASE_FILE = "content_factory.db"


def setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


GROQ_API_KEY = setting("GROQ_API_KEY")
GROQ_MODEL = setting(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

SMTP_HOST = setting("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(setting("SMTP_PORT", "587"))
SMTP_EMAIL = setting("SMTP_EMAIL")
SMTP_APP_PASSWORD = setting("SMTP_APP_PASSWORD")

USDT_NETWORK = setting("USDT_NETWORK", "TRC20")
USDT_ADDRESS = setting("USDT_RECEIVE_ADDRESS")
USDT_AMOUNT = setting("USDT_AMOUNT", "10")


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                referral_code TEXT UNIQUE NOT NULL,
                referred_by INTEGER,
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (referred_by) REFERENCES users(id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS email_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                used INTEGER NOT NULL DEFAULT 0,
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
                amount TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        migrate_users(connection)


def migrate_users(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    }

    migrations = {
        "referral_code": (
            "ALTER TABLE users ADD COLUMN "
            "referral_code TEXT"
        ),
        "referred_by": (
            "ALTER TABLE users ADD COLUMN "
            "referred_by INTEGER"
        ),
        "email_verified": (
            "ALTER TABLE users ADD COLUMN "
            "email_verified INTEGER NOT NULL DEFAULT 0"
        ),
    }

    for column, statement in migrations.items():
        if column not in columns:
            try:
                connection.execute(statement)
            except sqlite3.OperationalError:
                pass


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120000,
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, saved_hash = stored.split("$", 1)
    except ValueError:
        return False

    current_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        120000,
    ).hex()

    return secrets.compare_digest(current_hash, saved_hash)


def create_referral_code() -> str:
    return secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()


def create_user(
    username: str,
    email: str,
    password: str,
    referral_code: str,
) -> tuple[bool, str]:
    username = username.strip()
    email = email.strip().lower()
    referral_code = referral_code.strip().upper()

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    with database() as connection:
        inviter = None

        if referral_code:
            inviter = connection.execute(
                """
                SELECT id FROM users
                WHERE referral_code = ?
                """,
                (referral_code,),
            ).fetchone()

            if not inviter:
                return False, "The referral code is invalid."

        new_code = create_referral_code()

        while connection.execute(
            """
            SELECT id FROM users
            WHERE referral_code = ?
            """,
            (new_code,),
        ).fetchone():
            new_code = create_referral_code()

        try:
            connection.execute(
                """
                INSERT INTO users
                (
                    username,
                    email,
                    password_hash,
                    referral_code,
                    referred_by,
                    email_verified,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    username,
                    email,
                    hash_password(password),
                    new_code,
                    inviter["id"] if inviter else None,
                    utc_now(),
                ),
            )
        except sqlite3.IntegrityError:
            return False, "Username or email already exists."

    return True, "Account created. Verify your email to continue."


def authenticate(
    identifier: str,
    password: str,
) -> sqlite3.Row | None:
    identifier = identifier.strip()

    with database() as connection:
        user = connection.execute(
            """
            SELECT * FROM users
            WHERE (username = ? OR email = ?)
            AND email_verified = 1
            """,
            (identifier, identifier.lower()),
        ).fetchone()

    if user and verify_password(password, user["password_hash"]):
        return user

    return None


def send_email_code(email: str, code: str) -> None:
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError(
            "SMTP_EMAIL and SMTP_APP_PASSWORD are not configured."
        )

    message = EmailMessage()
    message["Subject"] = "Your account verification code"
    message["From"] = SMTP_EMAIL
    message["To"] = email
    message.set_content(
        f"""
Your verification code is: {code}

This code expires in 10 minutes.
If you did not request this code, ignore this email.
"""
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30,
    ) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.send_message(message)


def create_email_code(email: str) -> None:
    code = f"{random.randint(0, 999999):06d}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    expires_at = (
        datetime.utcnow() + timedelta(minutes=10)
    ).isoformat()

    with database() as connection:
        connection.execute(
            """
            UPDATE email_codes
            SET used = 1
            WHERE email = ? AND used = 0
            """,
            (email.lower(),),
        )

        connection.execute(
            """
            INSERT INTO email_codes
            (
                email,
                code_hash,
                expires_at,
                attempts,
                used,
                created_at
            )
            VALUES (?, ?, ?, 0, 0, ?)
            """,
            (
                email.lower(),
                code_hash,
                expires_at,
                utc_now(),
            ),
        )

    send_email_code(email, code)


def verify_email_code(email: str, code: str) -> bool:
    code_hash = hashlib.sha256(
        code.strip().encode()
    ).hexdigest()

    with database() as connection:
        record = connection.execute(
            """
            SELECT * FROM email_codes
            WHERE email = ? AND used = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (email.lower(),),
        ).fetchone()

        if not record:
            return False

        if record["attempts"] >= 5:
            return False

        if datetime.fromisoformat(
            record["expires_at"]
        ) < datetime.utcnow():
            return False

        if not secrets.compare_digest(
            record["code_hash"],
            code_hash,
        ):
            connection.execute(
                """
                UPDATE email_codes
                SET attempts = attempts + 1
                WHERE id = ?
                """,
                (record["id"],),
            )
            return False

        connection.execute(
            """
            UPDATE email_codes
            SET used = 1
            WHERE id = ?
            """,
            (record["id"],),
        )

        connection.execute(
            """
            UPDATE users
            SET email_verified = 1
            WHERE email = ?
            """,
            (email.lower(),),
        )

    return True


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
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower().replace("www.", "")

        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        elif host in {"youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(
                    parsed.query
                ).get("v", [""])[0]
            else:
                parts = parsed.path.strip("/").split("/")
                video_id = parts[1] if len(parts) > 1 else ""
        else:
            return ""

        return (
            video_id
            if re.fullmatch(
                r"[A-Za-z0-9_-]{11}",
                video_id,
            )
            else ""
        )

    except ValueError:
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
You are a professional international SEO writer,
editorial writer and social media strategist.

Transform the transcript into accurate and useful content.

Rules:
- Do not invent facts, statistics or quotations.
- Do not add unsupported information.
- Preserve the speaker's meaning.
- Avoid misleading clickbait.
- Write in professional international English.
- Do not mention AI or these instructions.
- Create exactly three assets.

[BLOG]
Create one detailed SEO article with:
SEO title, introduction, H2 and H3 headings,
detailed explanation, insights, supported examples,
practical takeaways, conclusion and SEO keywords.

[X]
Create exactly five concise X posts.
Number them exactly from 1 to 5.

[LINKEDIN]
Create exactly one professional LinkedIn post
with an opening, insight, explanation, takeaway,
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


def save_history(
    user_id: int,
    source_text: str,
    blog: str,
    x_posts: str,
    linkedin: str,
) -> None:
    with database() as connection:
        connection.execute(
            """
            INSERT INTO content_history
            (
                user_id,
                source_text,
                blog,
                x_posts,
                linkedin,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                source_text,
                blog,
                x_posts,
                linkedin,
                utc_now(),
            ),
        )


def get_history(user_id: int) -> list[sqlite3.Row]:
    with database() as connection:
        return connection.execute(
            """
            SELECT *
            FROM content_history
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()


def save_payment(
    user_id: int,
    transaction_hash: str,
) -> None:
    with database() as connection:
        connection.execute(
            """
            INSERT INTO payment_references
            (
                user_id,
                transaction_hash,
                network,
                amount,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                transaction_hash.strip(),
                USDT_NETWORK,
                USDT_AMOUNT,
                "pending_review",
                utc_now(),
            ),
        )


def render_payment(user_id: int) -> None:
    st.subheader("USDT Payment")

    if not USDT_ADDRESS:
        st.info(
            "Payment is not configured by the application owner."
        )
        return

    st.write(f"Network: `{USDT_NETWORK}`")
    st.write(f"Amount: `{USDT_AMOUNT} USDT`")
    st.code(USDT_ADDRESS, language="text")

    try:
        import qrcode

        image = qrcode.make(USDT_ADDRESS)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        st.image(
            buffer.getvalue(),
            width=180,
            caption="USDT receiving address",
        )
    except ImportError:
        st.caption("QR code support is unavailable.")

    st.warning(
        "Send USDT only on the displayed network. "
        "A wrong network may cause permanent loss."
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
            save_payment(user_id, transaction_hash)
            st.success(
                "Payment reference submitted for manual review."
            )


def authentication_page() -> None:
    st.title("AI Global Content Factory")

    register_tab, login_tab = st.tabs(
        ["Create Account", "Sign In"]
    )

    with register_tab:
        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Gmail Address")
            password = st.text_input(
                "Password",
                type="password",
            )
            confirmation = st.text_input(
                "Confirm Password",
                type="password",
            )
            referral_code = st.text_input(
                "Referral Code",
                help="Enter a valid code from another user.",
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if submitted:
            if password != confirmation:
                st.error("Passwords do not match.")
            else:
                success, message = create_user(
                    username,
                    email,
                    password,
                    referral_code,
                )

                if not success:
                    st.error(message)
                else:
                    try:
                        create_email_code(email)
                        st.session_state.pending_email = (
                            email.strip().lower()
                        )
                        st.success(
                            "A verification code was sent to your Gmail."
                        )
                    except Exception as error:
                        st.error(
                            "The verification email could not be sent."
                        )
                        st.code(str(error))

    pending_email = st.session_state.get(
        "pending_email",
        "",
    )

    if pending_email:
        st.subheader("Verify Your Gmail")

        code = st.text_input(
            "Six-Digit Verification Code",
            max_chars=6,
            help="Enter the code sent to your Gmail address.",
        )

        if st.button(
            "Verify Email",
            use_container_width=True,
        ):
            if verify_email_code(pending_email, code):
                st.success(
                    "Email verified. You can now sign in."
                )
                del st.session_state["pending_email"]
            else:
                st.error(
                    "The code is invalid, expired or locked."
                )

    with login_tab:
        with st.form("login_form"):
            identifier = st.text_input(
                "Username or Gmail Address"
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
            user = authenticate(identifier, password)

            if user:
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.session_state.referral_code = user[
                    "referral_code"
                ]
                st.rerun()
            else:
                st.error(
                    "Invalid credentials or unverified email."
                )


def render_history(user_id: int) -> None:
    records = get_history(user_id)

    if not records:
        st.info("Your content history is empty.")
        return

    for record in records:
        with st.expander(
            f"Generated on {record['created_at']}"
        ):
            st.markdown(record["blog"])

            st.download_button(
                "Download Blog",
                record["blog"],
                f"blog_{record['id']}.md",
                "text/markdown",
                key=f"blog_{record['id']}",
            )

            st.markdown(record["x_posts"])

            st.download_button(
                "Download X Posts",
                record["x_posts"],
                f"x_posts_{record['id']}.txt",
                "text/plain",
                key=f"x_{record['id']}",
            )

            st.markdown(record["linkedin"])

            st.download_button(
                "Download LinkedIn Post",
                record["linkedin"],
                f"linkedin_{record['id']}.md",
                "text/markdown",
                key=f"linkedin_{record['id']}",
            )


def main() -> None:
    initialize_database()

    if "user_id" not in st.session_state:
        authentication_page()
        return

    user_id = st.session_state.user_id
    username = st.session_state.username
    referral_code = st.session_state.referral_code

    with st.sidebar:
        st.write(f"Signed in as: **{username}**")

        st.caption(
            f"Your referral code: `{referral_code}`"
        )

        if st.button(
            "Sign Out",
            use_container_width=True,
        ):
            st.session_state.clear()
            st.rerun()

        st.divider()

        with st.expander("USDT Payment"):
            render_payment(user_id)

    st.title("🎬 AI Global Content Factory")
    st.write(
        "Create an SEO article, five X posts and one "
        "LinkedIn post from a YouTube transcript."
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
                    result = generate_content(transcript)
                except Exception as error:
                    st.error(
                        "Content generation failed."
                    )
                    st.code(str(error))
                    st.stop()

            blog, x_posts, linkedin = split_content(result)

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
