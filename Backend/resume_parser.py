import pdfplumber
import re
import spacy

nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    return re.sub(r"\n\s*", "\n", text.strip())

def extract_email(text):
    email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return email[0] if email else None

def extract_phone(text):
    phone = re.findall(r"\+?\d{10,13}", text)
    return phone[0] if phone else None

def extract_skills(text):
    doc = nlp(text)
    skills = [ent.text for ent in doc.ents if ent.label_ == "SKILL"]
    return list(set(skills))  # Remove duplicates
