import re
from core.groq_client import get_groq_client
from db.database import log_activity
from services.quiz_service import generate_quiz
from services.flashcard_service import generate_flashcards
from services.summary_service import generate_summary
from services.tts_service import text_to_speech

def classify_intent(query: str) -> str:
    """
    Classifies user intent using keyword matching.
    Returns: 'quiz', 'flashcard', 'summary', 'audio', or 'chat'.
    """
    q = query.lower().strip()
    
    # Quiz checks: matches if "quiz", "mcq", or "test" is in the string, combined with a creation verb, or exact match.
    if "quiz" in q or "mcq" in q or "test" in q or "question" in q:
        if any(w in q for w in ["generate", "create", "make", "take", "give", "do", "start", "test", "practice", "new", "/"]) or q in ["quiz", "mcq", "test"]:
            return "quiz"
        
    # Flashcard checks
    if "flashcard" in q or "flash card" in q or "card" in q:
        if any(w in q for w in ["generate", "create", "make", "show", "give", "start", "study", "new", "/"]) or q in ["flashcard", "flashcards", "cards"]:
            return "flashcard"
        
    # Summary checks
    if "summar" in q or "overview" in q or "brief" in q or "outline" in q:
        if any(w in q for w in ["generate", "create", "make", "give", "write", "do", "summarise", "summarize", "/"]) or q in ["summary", "summarize", "summarise"]:
            return "summary"
        
    # Audio checks
    if "audio" in q or "speech" in q or "tts" in q or "listen" in q or "read aloud" in q or "voice" in q:
        if any(w in q for w in ["generate", "create", "make", "play", "convert", "do", "read", "/"]) or q == "audio":
            return "audio"
        
    return "chat"

def handle_chat_fallback(query: str, context: str, history: list, api_key: str = None) -> str:
    """
    Answers general user questions grounding response in PDF context.
    """
    client = get_groq_client(api_key)
    
    truncated_context = context[:15000] if context else "No study material uploaded yet."
    
    system_prompt = (
        "You are an AI Study Copilot, an advanced educational agent.\n"
        "Your goal is to help students learn effectively. "
        "You have access to their study material (extracted from an uploaded PDF).\n\n"
        f"Study Material Context:\n{truncated_context}\n\n"
        "Guidelines:\n"
        "1. Rely on the study material context as much as possible.\n"
        "2. If the user asks something outside the context, answer using your general knowledge but note that it wasn't in the document.\n"
        "3. Provide structured, clean, and formatting-rich Markdown responses.\n"
        "4. Be concise, academic, and encouraging."
    )
    
    # Construct message thread
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append last 6 history turns to save tokens and keep latency low
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": query})
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

def process_user_input(
    query: str,
    pdf_text: str,
    pdf_hash: str,
    chat_history: list,
    api_key: str = None,
    force_regenerate: bool = False
) -> dict:
    """
    Routes user prompt to the appropriate service handler.
    Returns a response dictionary with fields:
    - intent: (str) the detected intent
    - response: (str or list) data returned by the service
    - audio_data: (BytesIO) raw mp3 data, only if intent is 'audio'
    """
    intent = classify_intent(query)
    
    # Check if a PDF is required for the requested command
    if intent in ["quiz", "flashcard", "summary", "audio"] and (not pdf_text or not pdf_text.strip()):
        return {
            "intent": "error",
            "response": (
                "⚠️ It looks like you want me to perform a study task, but no study material "
                "with readable text has been successfully loaded.\n\n"
                "Please verify that:\n"
                "1. You have uploaded a PDF in the sidebar.\n"
                "2. The PDF contains digital text layer (it isn't a scanned image/picture without OCR).\n\n"
                "Check the sidebar: if the word count is 0, the document is scanned and cannot be read."
            )
        }
        
    try:
        if intent == "quiz":
            log_activity("quiz", f"Quiz generation requested (PDF Hash: {pdf_hash[:8]})")
            quiz_data = generate_quiz(pdf_text, pdf_hash, api_key, force_regenerate)
            return {
                "intent": "quiz",
                "response": quiz_data
            }
            
        elif intent == "flashcard":
            log_activity("flashcard", f"Flashcard generation requested (PDF Hash: {pdf_hash[:8]})")
            cards_data = generate_flashcards(pdf_text, pdf_hash, api_key, force_regenerate)
            return {
                "intent": "flashcard",
                "response": cards_data
            }
            
        elif intent == "summary":
            log_activity("summary", f"Summary generation requested (PDF Hash: {pdf_hash[:8]})")
            summary_text = generate_summary(pdf_text, pdf_hash, api_key, force_regenerate)
            return {
                "intent": "summary",
                "response": summary_text
            }
            
        elif intent == "audio":
            log_activity("audio", f"Audio generation requested (PDF Hash: {pdf_hash[:8]})")
            # Fetch summary first
            summary_text = generate_summary(pdf_text, pdf_hash, api_key, force_regenerate)
            audio_buffer = text_to_speech(summary_text)
            return {
                "intent": "audio",
                "response": "🔊 Generated audio summary! You can play it below:",
                "audio_data": audio_buffer
            }
            
        else: # general chat fallback
            log_activity("chat", f"General chat query: '{query[:40]}...'")
            chat_response = handle_chat_fallback(query, pdf_text, chat_history, api_key)
            return {
                "intent": "chat",
                "response": chat_response
            }
            
    except Exception as e:
        error_msg = f"An error occurred while processing your request: {str(e)}"
        log_activity("error", f"Error processing query '{query[:30]}': {str(e)}")
        return {
            "intent": "error",
            "response": error_msg
        }
