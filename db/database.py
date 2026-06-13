import sqlite3
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Get database path from environment variable or default to copilot.db
DB_PATH = os.getenv("DATABASE_PATH", "copilot.db")

def get_connection():
    """Returns a SQLite connection and ensures the parent directory exists."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Activities table to track user queries & agent responses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                details TEXT NOT NULL
            )
        """)
        
        # Quizzes table to store generated MCQs associated with PDF hash
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_hash TEXT UNIQUE NOT NULL,
                quiz_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Flashcards table to store Front/Back Q&A format cards
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_hash TEXT UNIQUE NOT NULL,
                cards_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Summaries table to store summaries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_hash TEXT UNIQUE NOT NULL,
                summary_text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sessions table for ChatGPT-style session management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                pdf_name TEXT,
                pdf_text TEXT,
                pdf_hash TEXT,
                user_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Schema migration: check if user_id column exists, if not add it
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
        
        # Messages table to store chat history per session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'chat',
                msg_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()

def log_activity(action_type, details):
    """Logs a user/agent activity to the database."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO activities (action_type, details) VALUES (?, ?)",
                (action_type, details)
            )
            conn.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")

def get_recent_activities(limit=10):
    """Retrieves the last N activities logged in the database."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT timestamp, action_type, details FROM activities ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error retrieving activities: {e}")
        return []

def save_quiz(pdf_hash, quiz_data):
    """Saves or updates quiz JSON data for a specific PDF hash."""
    try:
        quiz_str = json.dumps(quiz_data) if isinstance(quiz_data, (list, dict)) else quiz_data
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO quizzes (pdf_hash, quiz_data) VALUES (?, ?)",
                (pdf_hash, quiz_str)
            )
            conn.commit()
            log_activity("save_quiz", f"Saved quiz for PDF hash: {pdf_hash[:8]}...")
    except Exception as e:
        print(f"Error saving quiz: {e}")

def get_quiz(pdf_hash):
    """Retrieves quiz data for a specific PDF hash, returns parsed JSON or None."""
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT quiz_data FROM quizzes WHERE pdf_hash = ?", (pdf_hash,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["quiz_data"])
    except Exception as e:
        print(f"Error getting quiz: {e}")
    return None

def save_flashcards(pdf_hash, cards_data):
    """Saves or updates flashcard JSON data for a specific PDF hash."""
    try:
        cards_str = json.dumps(cards_data) if isinstance(cards_data, (list, dict)) else cards_data
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO flashcards (pdf_hash, cards_data) VALUES (?, ?)",
                (pdf_hash, cards_str)
            )
            conn.commit()
            log_activity("save_flashcards", f"Saved flashcards for PDF hash: {pdf_hash[:8]}...")
    except Exception as e:
        print(f"Error saving flashcards: {e}")

def get_flashcards(pdf_hash):
    """Retrieves flashcard data for a specific PDF hash, returns parsed JSON or None."""
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT cards_data FROM flashcards WHERE pdf_hash = ?", (pdf_hash,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["cards_data"])
    except Exception as e:
        print(f"Error getting flashcards: {e}")
    return None

def save_summary(pdf_hash, summary_text):
    """Saves or updates summary text for a specific PDF hash."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO summaries (pdf_hash, summary_text) VALUES (?, ?)",
                (pdf_hash, summary_text)
            )
            conn.commit()
            log_activity("save_summary", f"Saved summary for PDF hash: {pdf_hash[:8]}...")
    except Exception as e:
        print(f"Error saving summary: {e}")

def get_summary(pdf_hash):
    """Retrieves summary text for a specific PDF hash."""
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT summary_text FROM summaries WHERE pdf_hash = ?", (pdf_hash,))
            row = cursor.fetchone()
            if row:
                return row["summary_text"]
    except Exception as e:
        print(f"Error getting summary: {e}")
    return None

# Chat Session Management CRUD API
def create_session(session_id, title="New Chat", pdf_name=None, pdf_text=None, pdf_hash=None, user_id=None):
    """Creates a new chat session in the database."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, title, pdf_name, pdf_text, pdf_hash, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, title, pdf_name, pdf_text, pdf_hash, user_id)
            )
            conn.commit()
            log_activity("create_session", f"Created session: {session_id[:8]}... Title: {title} User: {user_id}")
    except Exception as e:
        print(f"Error creating session: {e}")

def update_session_pdf(session_id, pdf_name, pdf_text, pdf_hash):
    """Updates the PDF details associated with a chat session."""
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET pdf_name = ?, pdf_text = ?, pdf_hash = ? WHERE session_id = ?",
                (pdf_name, pdf_text, pdf_hash, session_id)
            )
            conn.commit()
            log_activity("update_session_pdf", f"Linked PDF '{pdf_name}' to session {session_id[:8]}...")
    except Exception as e:
        print(f"Error updating session PDF: {e}")

def update_session_title(session_id, title):
    """Updates the title of a chat session."""
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE session_id = ?",
                (title, session_id)
            )
            conn.commit()
    except Exception as e:
        print(f"Error updating session title: {e}")

def get_sessions(user_id=None):
    """Retrieves all chat sessions sorted by creation time (descending). Filtered by user_id if provided."""
    try:
        with get_connection() as conn:
            if user_id:
                cursor = conn.execute(
                    "SELECT session_id, title, pdf_name, pdf_text, pdf_hash, created_at FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT session_id, title, pdf_name, pdf_text, pdf_hash, created_at FROM sessions ORDER BY created_at DESC"
                )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return []

def get_session_details(session_id):
    """Retrieves metadata of a specific chat session."""
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT session_id, title, pdf_name, pdf_text, pdf_hash FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        print(f"Error getting session details: {e}")
    return None

def delete_session(session_id):
    """Deletes a chat session and all its associated messages."""
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            log_activity("delete_session", f"Deleted session: {session_id[:8]}...")
    except Exception as e:
        print(f"Error deleting session: {e}")

def save_message(session_id, role, content, msg_type="chat", msg_data=None):
    """Saves a message associated with a session to the database."""
    try:
        if isinstance(msg_data, (list, dict)):
            msg_data_str = json.dumps(msg_data)
        else:
            msg_data_str = msg_data
            
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, msg_type, msg_data) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, msg_type, msg_data_str)
            )
            conn.commit()
    except Exception as e:
        print(f"Error saving message: {e}")

def get_messages(session_id):
    """Retrieves all messages for a specific session sorted by ID (chronological)."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT role, content, msg_type, msg_data FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            messages = []
            for row in cursor.fetchall():
                d = dict(row)
                if d["msg_data"]:
                    try:
                        d["data"] = json.loads(d["msg_data"])
                    except json.JSONDecodeError:
                        d["data"] = d["msg_data"]
                else:
                    d["data"] = None
                d["type"] = d["msg_type"]
                messages.append(d)
            return messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

def clear_database():
    """Drops/clears all tables in the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS messages")
            cursor.execute("DROP TABLE IF EXISTS sessions")
            cursor.execute("DROP TABLE IF EXISTS activities")
            cursor.execute("DROP TABLE IF EXISTS quizzes")
            cursor.execute("DROP TABLE IF EXISTS flashcards")
            cursor.execute("DROP TABLE IF EXISTS summaries")
            conn.commit()
        init_db()
        log_activity("clear_db", "Database cleared and re-initialized.")
    except Exception as e:
        print(f"Error clearing database: {e}")
