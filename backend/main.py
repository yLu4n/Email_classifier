import os
import io
import re
import string
import PyPDF2
import google.generativeai as genai
import sqlite3


from typing import Optional
from fastapi import FastAPI, Depends, Form, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import SessionLocal, Email

from .classifier import classify_email_with_gemini

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except Exception:
    NLTK_AVAILABLE = False


app = FastAPI(title="Email Classifier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if NLTK_AVAILABLE:
    try:
        nltk.data.find("tokenizers/punkt")
    except:
        nltk.download("punkt")
    try:
        nltk.data.find("corpora/stopwords")
    except:
        nltk.download("stopwords")

    try:
        STOPWORDS_PT = set(stopwords.words("portuguese"))
    except Exception:
        STOPWORDS_PT = set()
else:
    STOPWORDS_PT = set()

PROD_KEYWORDS = [
    "solicit", "solicita", "solicitação", "por favor", "precis", "erro", "problema",
    "anexo", "status", "atualiz", "suport", "ticket", "reuni", "urgente", "duvid",
    "dúvid", "pedido", "encaminh", "document", "enviado", "enviar", "aplica", "ajuda"
]

frontend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

def extract_text_from_pdf_bytes(b: bytes) -> str:
    text = ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(b))
        for p in reader.pages:
            page_text = p.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        try:
            text = b.decode("utf-8", errors="ignore")
        except:
            text = ""
    return text

def extract_text_from_txt_bytes(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except:
        return b.decode("latin-1", errors="ignore")

def preprocess(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    
    if NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(text, language="portuguese")
            tokens = [t for t in tokens if t not in STOPWORDS_PT]
            return " ".join(tokens)
        except Exception:
            return text
    else:
        tokens = [t for t in text.split() if t not in STOPWORDS_PT]
        return " ".join(tokens)

def classify_by_keywords(text: str) -> dict:
    if not text:
        return {"category": "Improdutivo", "score": 0, "confidence": 0.5, "keywords": {}}
    
    lowered = text.lower()
    matches = {}
    score = 0
    for kw in PROD_KEYWORDS:
        if kw in lowered:
            count = lowered.count(kw)
            matches[kw] = count
            score += count
    
    category = "Produtivo" if score > 0 else "Improdutivo"
    
    if score == 0:
        confidence = 0.5
    else:
        confidence = min(0.99, 0.5 + 0.12 * score)
    
    return {
        "category": category,
        "score": score,
        "confidence": round(confidence, 2),
        "keywords": matches
    }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/classify")
async def classify_email(text: str = Form(...), db: Session = Depends(get_db)):
    categoria, resposta = classify_email_with_gemini(text)
    
    email = Email(texto=text, categoria=categoria, resposta=resposta)
    db.add(email)
    db.commit()
    db.refresh(email)
    
    return{
        "id": email.id,
        "texto": email.texto,
        "categoria": email.categoria,
        "resposta": email.resposta,
        "created_at": email.created_at
    }

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    emails = db.query(Email).order_by(Email.created_at.desc()).all()
    return [
        {
            "id": email.id,
            "texto": email.texto,
            "categoria": email.categoria,
            "resposta": email.resposta,
            "created_at": email.created_at
        }for email in emails
    ]