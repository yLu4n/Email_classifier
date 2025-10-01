import os
import re
import string
import fitz
import csv
import io

from typing import Optional
from fastapi import FastAPI, Depends, Form, UploadFile, File, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from datetime import datetime, time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import or_

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

def extract_text_from_txt_bytes(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except:
        return b.decode("latin-1", errors="ignore")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/classify")
async def classify_email(
    text: Optional[str] = Form(None), 
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)):
    
    content_text = None
    
    if file is not None:
        try:
            raw = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao ler o arquivo: {e}")

        filename = (file.filename or "").lower()
        if filename.endswith(".pdf"):
            try:
                doc = fitz.open(stream=raw, filetype="pdf")
                pages_text = []
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    page_text = page.get_text("text").strip()
                    if page_text:
                        pages_text.append(page_text)
                content_text = "\n".join(pages_text).strip()
                    
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Erro ao extrair texto do PDF: {e}")
        elif filename.endswith(".txt"):
            try:
                content_text = extract_text_from_txt_bytes(raw).strip()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Erro ao extrair o texto do TXT: {e}")
        else:
            raise HTTPException(status_code=400, detail="Formato de arquivo não suportado. Use .txt ou .pdf")
    
    if not content_text:
        content_text = (text or "").strip()
    
    if not content_text:
        raise HTTPException(status_code=400, detail="Nenhum texto fornecido para análise (arquivo vazio ou campo de texto em branco).")

    
    categoria, resposta = classify_email_with_gemini(content_text)
    
    email = Email(texto=content_text, categoria=categoria, resposta=resposta)
    db.add(email)
    db.commit()
    db.refresh(email)
    
    return{
        "id": email.id,
        "texto": email.texto,
        "categoria": email.categoria,
        "resposta": email.resposta,
        "created_at": email.created_at.isoformat()
    }

def apply_history_filters(query, keyword: Optional[str], category: Optional[str],
                          start_date: Optional[str], end_date: Optional[str]):
    if keyword and keyword.strip():
        k = keyword.strip()
        query = query.filter(or_(Email.texto.ilike(f"%{k}%"), Email.resposta.ilike(f"%{k}%")))

    if category and category.strip():
        c = category.strip()
        query = query.filter(Email.categoria.ilike(f"%{c}%"))

    if start_date and start_date.strip():
        try:
            sd = datetime.strptime(start_date.strip(), "%Y-%m-%d")
            # início do dia
            sd = datetime.combine(sd.date(), time.min)
            query = query.filter(Email.created_at >= sd)
        except Exception:
            pass

    if end_date and end_date.strip():
        try:
            ed = datetime.strptime(end_date.strip(), "%Y-%m-%d")
            # fim do dia
            ed = datetime.combine(ed.date(), time.max)
            query = query.filter(Email.created_at <= ed)
        except Exception:
            pass

    return query

@app.get("/api/history")
def get_history(
    keyword: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Email)
    q = apply_history_filters(q, keyword, category, start_date, end_date)
    emails = q.order_by(Email.created_at.desc()).all()

    return [
        {
            "id": e.id,
            "texto": e.texto,
            "categoria": e.categoria,
            "resposta": e.resposta,
            "created_at": e.created_at.isoformat()
        } for e in emails
    ]


@app.get("/api/history/export/csv")
def export_csv(db: Session = Depends(get_db)):
    emails = db.query(Email).order_by(Email.created_at.desc()).all()
    
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["ID", "Texto", "Categoria", "Resposta", "Data"])
    for e in emails:
        writer.writerow([e.id, e.texto, e.categoria, e.resposta, e.created_at])
    
    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=history.csv"}
    )

@app.get("/api/history/export/pdf")
def export_pdf(db: Session = Depends(get_db)):
    emails = db.query(Email).order_by(Email.created_at.desc()).all()
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    for e in emails:
        c.drawString(30, y, f"{e.created_at}: [{e.categoria}] {e.texto[:80]}...") # resumo
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=history.pdf"})