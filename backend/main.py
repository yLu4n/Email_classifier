import os
import io
import re
import string
import PyPDF2
import openai

from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    import openai
    OPENAI_AVAILABLE = False
except Exception:
    OPENAI_AVAILABLE = False

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

def generate_response_template(original_text: str, category: str) -> str:
    
    api_key = os.getenv("OPENAI_API_KEY")
    if OPENAI_AVAILABLE and api_key:
        try:
            openai.api_key = api_key
            messages = [
                {"role": "system", 
                "content": "Você é um assistente que escreve respostas automáticas curtas, profissionais e objetivas para e-mails corporativos em português."},
                {"role": "user",
                        "content": f"Classificação: {category}\nE-mail:\n{original_text}\n\nGere uma resposta automática breve (2-4 frases) em português, profissional, adequada ao teor do e-mail"}
            ]
            resp = openai.ChatCompletion.create(
                model = "gpt-3.5-turbo",
                messages=messages,
                max_tokens = 180,
                temperature = 0.2,
            )
            return resp.choices[0].message["content"].strip()
        except Exception as e:
            print("OpenAI call failed:", e)
    
    if category.lower() == "produtivo":
        return(
            "Olá,\n\n"
            "Obrigado pelo seu contato. Recebemos sua solicitação e estamos analisando o caso."
            "Por favor, nos envie (se aplicável) número do pedido, prints ou anexos para agilizar a verificação."
            "Retornaremos em até 48 horas úteis.\n\nAtenciosamente, \nEquipe de Suporte."
        )
    else:
        return(
            "Olá,\n\n"
            "Obrigado pela mensagem! Agradecemos o contato. "
            "Se precisar de suporte ou tiver uma solicitação específica, por favor encaminhe os detalhes. "
            "Tenha um ótimo dia!\n\nAtenciosamente,\nEquipe"
        )

@app.post("/api/classify")
async def classify_endpoint(file: Optional[UploadFile] = File(None), text: Optional[str] = Form(None)):
    
    content = ""
    if file:
        data = await file.read()
        filename = (file.filename or "").lower()
        if filename.endswith(".pdf"):
            content += extract_text_from_pdf_bytes(data)
        else:
            content += extract_text_from_txt_bytes(data)
    
    if text:
        content += ("\n" + text) if content else text
    
    if not content or not content.strip():
        return JSONResponse({"error": "Nenhum contéudo fornecido (arquivo ou texto)."}, status_code=400)
    
    processed = preprocess(content)
    classification = classify_by_keywords(processed)
    suggested_response = generate_response_template(content, classification["category"])
    
    return{
        "category": classification["category"],
        "confidence": classification["confidence"],
        "score": classification["score"],
        "matched_keywords": classification["keywords"],
        "suggested_response": suggested_response,
        "processed_text": processed[:800],
    }