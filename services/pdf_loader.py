import pdfplumber
import hashlib

def extract_pdf_text(file_obj) -> tuple[str, str]:
    """
    Extracts text from a PDF file-like object (e.g., Streamlit's UploadedFile).
    Returns a tuple of (extracted_text, pdf_hash).
    """
    # Reset file pointer
    file_obj.seek(0)
    
    # Read bytes to compute MD5 hash for database uniqueness/mapping
    file_bytes = file_obj.read()
    pdf_hash = hashlib.md5(file_bytes).hexdigest()
    
    # Reset file pointer for pdfplumber
    file_obj.seek(0)
    
    text_content = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
                
    full_text = "\n".join(text_content).strip()
    return full_text, pdf_hash
