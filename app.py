import hashlib
import os
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

SMTP_HOST = get_setting("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_setting("SMTP_PORT", "587"))
SMTP_EMAIL = get_setting("SMTP_EMAIL")
SMTP_APP_PASSWORD = get_setting("SMTP_APP_PASSWORD")

USDT_NETWORK = get_setting("USDT_NETWORK", "TRC20")
USDT_ADDRESS = get_setting("USDT_RECEIVE_ADDRESS")
USDT_AMOUNT = get_setting("USDT_AMOUNT", "10")


st.set_page_config(
    page_title="AI Global Content Factory",
    page_icon="🎬",
    layout="wide",
)


def now_utc() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def now_text() -> str:
    return now_utc().isoformat()


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
                referral_code TEXT UNIQUE NOT NULL,
                referred_by INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                referral_code TEXT,
                verification_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_sent_at TEXT NOT NULL,
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


def validate_email(email: str) -> bool:
    return bool(
        re.fullmatch(
            r"[^@\s]+@gmail\.com",
            email.strip().lower(),
        )
    )


def create_referral_code() -> str:
    return secrets.token_urlsafe(8).replace(
        "-",
        "",
    ).replace(
        "_",
        "",
    ).upper()[:10]


def create_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def send_verification_email(
    recipient_email: str,
    verification_code: str,
) -> None:
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError(
            "SMTP_EMAIL and SMTP_APP_PASSWORD are not configured."
        )

    message = EmailMessage()
    message["Subject"] = "AI Global Content Factory Verification Code"
    message["From"] = SMTP_EMAIL
    message["To"] = recipient_email
    message.set_content(
        f"""
Your verification code is: {verification_code}

This code expires in 10 minutes.
You have a maximum of five verification attempts.

If you did not create this account, ignore this email.
"""
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30,
    ) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.send_message(message)


def find_existing_user(
    username: str,
    email: str,
) -> sqlite3.Row | None:
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id
            FROM users
            WHERE username = ? OR email = ?
            """,
            (
                username.strip(),
                email.strip().lower(),
            ),
        ).fetchone()


def start_registration(
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

    if not validate_email(email):
        return False, "Use a valid Gmail address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain an uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain a lowercase letter."

    if not re.search(r"\d", password):
        return False, "Password must contain a number."

    existing_user = find_existing_user(username, email)

    if existing_user:
        return False, "Username or email already exists."

    with get_connection() as connection:
        inviter = None

        if referral_code:
            inviter = connection.execute(
                """
                SELECT id
                FROM users
                WHERE referral_code = ?
                """,
                (referral_code,),
            ).fetchone()

            if not inviter:
                return False, "The referral code is invalid."

        verification_code = create_verification_code()
        verification_hash = hashlib.sha256(
            verification_code.encode("utf-8")
        ).hexdigest()

        expires_at = (
            now_utc() + timedelta(minutes=10)
        ).isoformat()

        connection.execute(
            """
            DELETE FROM pending_registrations
            WHERE email = ?
            """,
            (email,),
        )

        connection.execute(
            """
            INSERT INTO pending_registrations
            (
                username,
                email,
                password_hash,
                referral_code,
                verification_hash,
                expires_at,
                attempts,
                last_sent_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                username,
                email,
                hash_password(password),
                referral_code or None,
                verification_hash,
                expires_at,
                now_text(),
                now_text(),
            ),
        )

    try:
        send_verification_email(email, verification_code)
    except Exception as error:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM pending_registrations
                WHERE email = ?
                """,
                (email,),
            )

        return False, str(error)

    return True, "A verification code was sent to your Gmail."


def resend_verification_code(email: str) -> tuple[bool, str]:
    email = email.strip().lower()

    with get_connection() as connection:
        pending = connection.execute(
            """
            SELECT *
            FROM pending_registrations
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if not pending:
            return False, "No pending registration was found."

        last_sent = datetime.fromisoformat(
            pending["last_sent_at"]
        )

        if now_utc() - last_sent < timedelta(seconds=60):
            return False, (
                "Wait at least 60 seconds before requesting "
                "another code."
            )

        verification_code = create_verification_code()
        verification_hash = hashlib.sha256(
            verification_code.encode("utf-8")
        ).hexdigest()

        expires_at = (
            now_utc() + timedelta(minutes=10)
        ).isoformat()

        connection.execute(
            """
            UPDATE pending_registrations
            SET verification_hash = ?,
                expires_at = ?,
                attempts = 0,
                last_sent_at = ?
            WHERE email = ?
            """,
            (
                verification_hash,
                expires_at,
                now_text(),
                email,
            ),
        )

    try:
        send_verification_email(email, verification_code)
    except Exception as error:
        return False, str(error)

    return True, "A new verification code was sent."


def verify_registration_code(
    email: str,
    code: str,
) -> tuple[bool, str]:
    email = email.strip().lower()
    code = code.strip()

    if not re.fullmatch(r"\d{6}", code):
        return False, "Enter a six-digit verification code."

    submitted_hash = hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()

    with get_connection() as connection:
        pending = connection.execute(
            """
            SELECT *
            FROM pending_registrations
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if not pending:
            return False, "No pending registration was found."

        if pending["attempts"] >= 5:
            return False, (
                "Too many attempts. Request a new verification code."
            )

        if datetime.fromisoformat(
            pending["expires_at"]
        ) < now_utc():
            return False, (
                "The verification code expired. Request a new code."
            )

        if not secrets.compare_digest(
            pending["verification_hash"],
            submitted_hash,
        ):
            connection.execute(
                """
                UPDATE pending_registrations
                SET attempts = attempts + 1
                WHERE email = ?
                """,
                (email,),
            )
            return False, "The verification code is incorrect."

        referral_code = pending["referral_code"]
        referred_by = None

        if referral_code:
            inviter = connection.execute(
                """
                SELECT id
                FROM users
                WHERE referral_code = ?
                """,
                (referral_code,),
            ).fetchone()

            if inviter:
                referred_by = inviter["id"]

        new_code = create_referral_code()

        while connection.execute(
            """
            SELECT id
            FROM users
            WHERE referral_code = ?
            """,
            (new_code,),
        ).fetchone():
            new_code = create_referral_code()

        connection.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password_hash,
                referral_code,
                referred_by,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                pending["username"],
                pending["email"],
                pending["password_hash"],
                new_code,
                referred_by,
                now_text(),
            ),
        )

        connection.execute(
            """
            DELETE FROM pending_registrations
            WHERE email = ?
            """,
            (email,),
        )

    return True, "Email verified. Your account is ready."


def authenticate(
    identifier: str,
    password: str,
) -> sqlite3.Row | None:
    identifier = identifier.strip()

    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE username = ? OR email = ?
            """,
            (
                identifier,
                identifier.lower(),
            ),
        ).fetchone()

    if user and verify_password(
        password,
        user["password_hash"],
    ):
        return user

    return None


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
            "GROQ_API_KEY is not configured."
        )

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
You are a professional international SEO writer,
editorial writer and social media strategist.

Transform the transcript into accurate, useful and original content.

Rules:
- Do not invent facts, statistics or quotations.
- Do not add unsupported information.
- Preserve the speaker's meaning.
- Avoid misleading clickbait.
- Write in professional international English.
- Create exactly three assets.

[BLOG]
Create one detailed SEO article with a title,
introduction, H2 and H3 headings, insights,
supported examples, practical takeaways,
conclusion and SEO keywords.

[X]
Create exactly five concise X posts.
Number them exactly from 1 to 5.

[LINKEDIN]
Create exactly one professional LinkedIn post
with a strong opening, insight, explanation,
practical takeaway, conclusion and 3 to 5 hashtags.

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
    with get_connection() as connection:
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
                now_text(),
            ),
        )


def render_auth_page() -> None:
    st.title("AI Global Content Factory")

    register_tab, login_tab = st.tabs(
        ["Create Account", "Sign In"]
    )

    with register_tab:
        with st.form("register_form"):
            username = st.text_input(
                "Username",
                max_chars=30,
            )

            email = st.text_input(
                "Gmail Address",
                placeholder="yourname@gmail.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                help=(
                    "At least 8 characters, including uppercase, "
                    "lowercase and a number."
                ),
            )

            confirmation = st.text_input(
                "Confirm Password",
                type="password",
            )

            referral_code = st.text_input(
                "Referral Code",
                help="Optional. Leave empty if you do not have one.",
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )

        if submitted:
            if password != confirmation:
                st.error("Passwords do not match.")
            else:
                success, message = start_registration(
                    username,
                    email,
                    password,
                    referral_code,
                )

                if success:
                    st.session_state.pending_email = (
                        email.strip().lower()
                    )
                    st.success(message)
                else:
                    st.error(message)

        pending_email = st.session_state.get(
            "pending_email",
            "",
        )

        if pending_email:
            st.divider()
            st.subheader("Verify Your Gmail")

            st.info(
                f"Check Inbox, Spam and Promotions for: "
                f"{pending_email}"
            )

            code = st.text_input(
                "Six-Digit Verification Code",
                max_chars=6,
                placeholder="123456",
            )

            verify_col, resend_col = st.columns(2)

            with verify_col:
                verify_clicked = st.button(
                    "Verify Email",
                    use_container_width=True,
                )

            with resend_col:
                resend_clicked = st.button(
                    "Resend Code",
                    use_container_width=True,
                )

            if verify_clicked:
                success, message = verify_registration_code(
                    pending_email,
                    code,
                )

                if success:
                    st.success(message)
                    del st.session_state["pending_email"]
                else:
                    st.error(message)

            if resend_clicked:
                success, message = resend_verification_code(
                    pending_email,
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

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
            user = authenticate(
                identifier,
                password,
            )

            if user:
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.session_state.referral_code = user[
                    "referral_code"
                ]
                st.rerun()
            else:
                st.error(
                    "Invalid credentials or email is not verified."
                )


def render_payment(user_id: int) -> None:
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
            caption="USDT receiving address",
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
            with get_connection() as connection:
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
                        now_text(),
                    ),
                )

            st.success(
                "Payment reference submitted for review."
            )


def render_history(user_id: int) -> None:
    with get_connection() as connection:
        records = connection.execute(
            """
            SELECT *
            FROM content_history
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    if not records:
        st.info("Your content history is empty.")
        return

    for record in records:
        with st.expander(
            f"Generated on {record['created_at']}"
        ):
            st.markdown(record["blog"])
            st.markdown(record["x_posts"])
            st.markdown(record["linkedin"])

            st.download_button(
                "Download Complete Content",
                (
                    f"BLOG\n\n{record['blog']}\n\n"
                    f"X POSTS\n\n{record['x_posts']}\n\n"
                    f"LINKEDIN\n\n{record['linkedin']}"
                ),
                f"content_{record['id']}.txt",
                "text/plain",
                key=f"download_{record['id']}",
                use_container_width=True,
            )


def render_factory(user_id: int) -> None:
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
                "Paste a transcript if automatic retrieval fails."
            ),
        )

    if st.button(
        "Generate Professional Content",
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
                "Fetching the YouTube transcript..."
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
                "Provide a YouTube URL or paste a transcript."
            )
            st.stop()

        if len(transcript) < 50:
            st.warning("The transcript is too short.")
            st.stop()

        with st.spinner(
            "Creating professional content..."
        ):
            try:
                generated = generate_content(transcript)
            except Exception as error:
                st.error("Content generation failed.")
                st.code(str(error))
                st.stop()

        blog, x_posts, linkedin = split_content(generated)

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


def main() -> None:
    initialize_database()

    if "user_id" not in st.session_state:
        render_auth_page()
        return

    user_id = st.session_state.user_id
    username = st.session_state.username
    referral_code = st.session_state.referral_code

    with st.sidebar:
        st.write(f"Signed in as: **{username}**")
        st.write(f"Your referral code: `{referral_code}`")

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

    history_tab, factory_tab = st.tabs(
        ["Content History", "Content Factory"]
    )

    with history_tab:
        render_history(user_id)

    with factory_tab:
        render_factory(user_id)


if __name__ == "__main__":
    main()
