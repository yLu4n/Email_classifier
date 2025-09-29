import google.generativeai as genai

from .config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def classify_email_with_gemini(texto: str) -> tuple[str, str]:
    
    prompt = f"""" 
    Analise o texto abaixo e classifique se o e-mail é PRODUTIVO ou IMPRODUTIVO.
    Depois, gere uma resposta educada ao e-mail.

    Texto: {texto}
    Responda no formato:
    Categoria: <Produtivo/Improdutivo>
    Resposta: <texto da resposta>
    """
    
    model = genai.GenerativeModel.from_cached_content("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    output = response.text.strip()
    
    categoria = "Improdutivo"
    resposta = "Obrigado pelo seu contato."
    if "Categoria:" in output:
        parts = output.split("Resposta:")
        categoria = parts[0].replace("Categoria:", "").strip()
        resposta = parts[1].strip() if len(parts) > 1 else resposta
    
    return categoria, resposta