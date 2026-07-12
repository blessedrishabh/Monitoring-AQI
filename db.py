"""
Database module for user authentication.
Uses Neon PostgreSQL for persistent user storage with bcrypt password hashing.
"""
import os
import secrets
import hashlib
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# How long a "remember me" login session stays valid before requiring re-login
SESSION_DURATION_DAYS = 30

# ── Connection Helper ─────────────────────────────────────────────────
def get_connection():
    """Get a PostgreSQL connection from the DATABASE_URL."""
    return psycopg2.connect(DATABASE_URL)

# ── Table Initialization ─────────────────────────────────────────────
def init_db():
    """Create the users table if it doesn't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    token_hash VARCHAR(64) UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS generated_emails (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    city VARCHAR(100) NOT NULL,
                    authority_email VARCHAR(255) NOT NULL,
                    subject VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    finally:
        conn.close()

# ── User CRUD ─────────────────────────────────────────────────────────
def create_user(full_name: str, email: str, password: str) -> dict | None:
    """
    Create a new user. Returns user dict on success, None if email already exists.
    Password is hashed with bcrypt before storage.
    """
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, full_name, email, created_at",
                (full_name, email.lower().strip(), password_hash)
            )
            user = dict(cur.fetchone())
        conn.commit()
        return user
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    finally:
        conn.close()

def authenticate_user(email: str, password: str) -> dict | None:
    """
    Authenticate a user by email and password.
    Returns user dict on success, None on failure.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, full_name, email, password_hash, created_at FROM users WHERE email = %s",
                (email.lower().strip(),)
            )
            row = cur.fetchone()
        if row is None:
            return None
        if bcrypt.checkpw(password.encode('utf-8'), row['password_hash'].encode('utf-8')):
            user = dict(row)
            del user['password_hash']  # Don't leak hash into session
            return user
        return None
    finally:
        conn.close()

# ── "Remember Me" Session Tokens ───────────────────────────────────────
def _hash_token(token: str) -> str:
    """Hash a raw token before storing/looking it up, same idea as a password."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def create_session(user_id: int) -> str:
    """
    Create a new login session for a user and return the raw token.
    Only the hash of this token is stored in the DB; the raw token
    is meant to be stashed in the browser (e.g. a URL query param).
    """
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DURATION_DAYS)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
                (token_hash, user_id, expires_at)
            )
        conn.commit()
        return token
    finally:
        conn.close()

def get_user_by_token(token: str) -> dict | None:
    """
    Look up the user tied to a session token. Returns None if the token
    is missing, invalid, or expired (and cleans up expired sessions).
    """
    if not token:
        return None
    token_hash = _hash_token(token)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.id, u.full_name, u.email, u.created_at, s.expires_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = %s
            """, (token_hash,))
            row = cur.fetchone()
        if row is None:
            return None
        expired = row['expires_at'] < datetime.utcnow()
        user = dict(row)
        del user['expires_at']
    finally:
        conn.close()

    if expired:
        delete_session(token)
        return None
    return user

def delete_session(token: str) -> None:
    """Invalidate a session token (used on logout or when it's expired)."""
    if not token:
        return
    token_hash = _hash_token(token)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
        conn.commit()
    finally:
        conn.close()

def get_user_count() -> int:
    """Get total number of registered users."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]
    except Exception:
        return 0
    finally:
        conn.close()

# ── Email Logging ─────────────────────────────────────────────────────
def log_generated_email(user_id: int, city: str, authority_email: str, subject: str, body: str) -> bool:
    """Store a generated email in the database to keep a record."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO generated_emails (user_id, city, authority_email, subject, body)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, city, authority_email, subject, body))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error logging email: {e}")
        return False
    finally:
        conn.close()

# Initialize the table on module import
try:
    init_db()
except Exception:
    pass  # Will fail gracefully if DB is unreachable; error shown at login time