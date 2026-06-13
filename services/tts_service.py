import io
import re
from gtts import gTTS

def clean_markdown_for_tts(text: str) -> str:
    """
    Removes Markdown formatting elements (headers, bold/italic symbols, bullet points)
    so that the Text-to-Speech voice reads only the plain text.
    """
    # Remove headers (e.g. ## Header -> Header)
    text = re.sub(r'#+\s+', '', text)
    # Remove bold and italics formatting (*text* or **text**)
    text = re.sub(r'\*+', '', text)
    # Remove lists symbols (e.g. - item -> item)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Remove inline code backticks (`code` -> code)
    text = re.sub(r'`+', '', text)
    # Remove markdown link formatting ([text](url) -> text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove extra whitespace and lines
    text = re.sub(r'\n+', '. ', text)
    return text.strip()

def text_to_speech(text: str) -> io.BytesIO:
    """
    Converts text to speech using gTTS and returns an in-memory BytesIO buffer containing MP3 data.
    """
    cleaned_text = clean_markdown_for_tts(text)
    # Limit to reasonable length if it's exceptionally long to prevent timeouts
    cleaned_text = cleaned_text[:3000]
    
    tts = gTTS(text=cleaned_text, lang='en', slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp
