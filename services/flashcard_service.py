import json
from core.groq_client import get_groq_client
from db.database import save_flashcards, get_flashcards

def generate_flashcards(text, pdf_hash, api_key=None, force_regenerate=False):
    """
    Generates a set of 5-8 study flashcards (Front/Back) from the study text using Groq Llama-3.1-8b-instant.
    Caches the flashcards in SQLite using the PDF hash.
    """
    if not force_regenerate:
        cached_cards = get_flashcards(pdf_hash)
        if cached_cards:
            return cached_cards

    client = get_groq_client(api_key)
    
    # Truncate text to keep response times low
    truncated_text = text[:15000]

    system_prompt = (
        "You are an expert tutor. Create a set of flashcards from the study material. "
        "You must respond ONLY with a valid JSON object matching the requested schema."
    )
    
    user_prompt = f"""
Based on the study material below, generate a list of exactly 6 flashcards for key concepts.
Each flashcard must have a "front" (a question, key term, or concept) and a "back" (the answer, explanation, or definition).

The output MUST be a JSON object with a single key "flashcards" containing a list of cards.
Each card must use the following schema:
{{
  "flashcards": [
    {{
      "front": "What is ...?",
      "back": "It is a concept that..."
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
        cards_list = data.get("flashcards", data)
        if not isinstance(cards_list, list):
            cards_list = [cards_list]
        
        save_flashcards(pdf_hash, cards_list)
        return cards_list
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse flashcard response as JSON: {content}") from e
