import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_groq_client(api_key=None):
    """
    Initializes and returns an OpenAI client configured for Groq.
    Order of lookup:
    1. api_key argument (passed from Streamlit session state / input)
    2. GROQ_API_KEY environment variable
    """
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key or key == "gsk_your_groq_api_key_here":
        raise ValueError(
            "Groq API Key is not set. "
            "Please configure GROQ_API_KEY in your .env file or enter it in the sidebar."
        )
    
    return OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1"
    )
