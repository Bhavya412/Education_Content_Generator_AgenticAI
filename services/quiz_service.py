import json
from core.groq_client import get_groq_client
from db.database import save_quiz, get_quiz

def generate_quiz(text, pdf_hash, api_key=None, force_regenerate=False):
    """
    Generates a 5-question MCQ quiz from the study text using Groq Llama-3.1-8b-instant.
    Caches the quiz in SQLite using the PDF hash.
    """
    if not force_regenerate:
        cached_quiz = get_quiz(pdf_hash)
        if cached_quiz:
            return cached_quiz

    client = get_groq_client(api_key)
    
    # Truncate text to fit within standard token limits and keep Groq response times low
    truncated_text = text[:15000]

    system_prompt = (
        "You are an expert tutor. Create a quiz from the material provided. "
        "You must respond ONLY with a valid JSON object matching the requested schema."
    )
    
    user_prompt = f"""
Based on the study material below, generate a multiple-choice quiz with exactly 5 questions.
Each question must have 4 options (A, B, C, D), a correct answer (must be either "A", "B", "C", or "D"), and a short explanation.

The output MUST be a JSON object with a single key "quiz" containing a list of questions.
Each question must use the following schema:
{{
  "quiz": [
    {{
      "question": "Question text here?",
      "options": {{
        "A": "Option A content",
        "B": "Option B content",
        "C": "Option C content",
        "D": "Option D content"
      }},
      "answer": "A",
      "explanation": "Explanation here."
    }}
  ]
}}

Study Material:
{truncated_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        quiz_list = data.get("quiz", data)
        if not isinstance(quiz_list, list):
            # If the format is not list, attempt to handle direct list wrapping
            quiz_list = [quiz_list]
        
        save_quiz(pdf_hash, quiz_list)
        return quiz_list
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse quiz response as JSON: {content}") from e
