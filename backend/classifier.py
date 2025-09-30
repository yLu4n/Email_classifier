import google.generativeai as genai
import os

from dotenv import load_dotenv

from .config import GEMINI_API_KEY

load_dotenv()
genai.configure(api_key=GEMINI_API_KEY)

def classify_email_with_gemini(email_text: str):
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    prompt = f"""
    Você é um sistema de classificação de emails.
    - Se o email requer ação ou resposta → classifique como PRODUTIVO.
    - Se for apenas felicitação, agradecimento ou sem relevância → classifique como IMPRODUTIVO.

    Retorne no formato:
    Categoria: <Produtivo/Improdutivo>
    Resposta: <Mensagem sugerida>

    Email:
    {email_text}
    """

    response = model.generate_content(prompt)

    resposta = getattr(response, "text", None)
    if not resposta and response.candidates:
        resposta = response.candidates[0].content.parts[0].text

    categoria, sugestao = "Desconhecido", ""
    if resposta:
        for line in resposta.splitlines():
            line = line.strip()
            if line.lower().startswith("categoria"):
                categoria = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("resposta"):
                sugestao = line.split(":", 1)[-1].strip()

    return categoria, sugestao