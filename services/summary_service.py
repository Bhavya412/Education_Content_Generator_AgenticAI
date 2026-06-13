from core.groq_client import get_groq_client
from db.database import save_summary, get_summary

def generate_summary(text, pdf_hash, api_key=None, force_regenerate=False):
    """
    Generates a comprehensive study summary from the study text using Groq Llama-3.1-8b-instant.
    Caches the summary text in SQLite.
    """
    if not force_regenerate:
        cached_summary = get_summary(pdf_hash)
        if cached_summary:
            return cached_summary

    client = get_groq_client(api_key)
    
    # Truncate text to keep response times low
    truncated_text = text[:20000]

    system_prompt = (
        "You are an expert tutor. Create a comprehensive, clear, and well-structured "
        "summary of the study material using Markdown. Use bold terms, headers, and bullet points."
    )
    
    user_prompt = f"""
Summarize the following study material. Your summary should include:
1. A brief overview of the main topic.
2. Key terms and their definitions.
3. Core concepts explained simply.
4. Top 3-5 key takeaways.

Study Material:
{truncated_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )

    summary_text = response.choices[0].message.content.strip()
    save_summary(pdf_hash, summary_text)
    return summary_text
