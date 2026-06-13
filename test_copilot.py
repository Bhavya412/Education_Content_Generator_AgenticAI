import os
import sys
import unittest

# Ensure project directories are in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db, log_activity, get_recent_activities, clear_database
from services.tts_service import clean_markdown_for_tts, text_to_speech
from core.engine import classify_intent

class TestStudyCopilot(unittest.TestCase):
    
    def setUp(self):
        # Override DB path for testing
        os.environ["DATABASE_PATH"] = "test_copilot.db"
        clear_database()
        
    def tearDown(self):
        # Clean up database file
        if os.path.exists("test_copilot.db"):
            try:
                os.remove("test_copilot.db")
            except PermissionError:
                pass
                
    def test_database_logging(self):
        """Test if the SQLite database initializes and logs activities successfully."""
        log_activity("test_action", "This is a test details logging.")
        activities = get_recent_activities(limit=5)
        self.assertTrue(len(activities) > 0)
        self.assertEqual(activities[0]["action_type"], "test_action")
        self.assertEqual(activities[0]["details"], "This is a test details logging.")
        
    def test_sessions_and_messages(self):
        """Test chat sessions and messages CRUD operations."""
        from db.database import create_session, get_sessions, save_message, get_messages, update_session_pdf, get_session_details
        
        # 1. Create a session
        create_session("sess_123", "Test Session Title")
        sessions = get_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "sess_123")
        self.assertEqual(sessions[0]["title"], "Test Session Title")
        
        # 2. Update session PDF details
        update_session_pdf("sess_123", "test.pdf", "File text content", "hash_abc")
        details = get_session_details("sess_123")
        self.assertEqual(details["pdf_name"], "test.pdf")
        self.assertEqual(details["pdf_text"], "File text content")
        self.assertEqual(details["pdf_hash"], "hash_abc")
        
        # 3. Save and get messages
        save_message("sess_123", "user", "Hello study agent")
        save_message("sess_123", "assistant", "Hello student", msg_type="chat")
        
        messages = get_messages("sess_123")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello study agent")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Hello student")
        self.assertEqual(messages[1]["type"], "chat")
        
    def test_markdown_cleaning_for_tts(self):
        """Test if markdown parser strips formatting symbols before sending to gTTS."""
        raw_markdown = "## Heading\nThis is **bold** and *italic* text with a [link](https://example.com) and `code`."
        cleaned = clean_markdown_for_tts(raw_markdown)
        self.assertNotIn("##", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("[link]", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertIn("bold", cleaned)
        
    def test_tts_service(self):
        """Test if TTS generates a valid stream of audio bytes."""
        text = "Hello world, this is a test audio generation."
        audio_stream = text_to_speech(text)
        self.assertIsNotNone(audio_stream)
        # Verify it has byte contents
        audio_bytes = audio_stream.read()
        self.assertTrue(len(audio_bytes) > 0)
        
    def test_intent_classification(self):
        """Test if command router correctly classifies basic text intents."""
        self.assertEqual(classify_intent("generate quiz"), "quiz")
        self.assertEqual(classify_intent("can you make a quiz from this page?"), "quiz")
        self.assertEqual(classify_intent("create flashcards"), "flashcard")
        self.assertEqual(classify_intent("summarize content"), "summary")
        self.assertEqual(classify_intent("play audio summary"), "audio")
        self.assertEqual(classify_intent("what is the capital of France?"), "chat")

if __name__ == "__main__":
    unittest.main()
